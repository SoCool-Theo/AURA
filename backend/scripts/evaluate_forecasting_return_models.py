"""Manual read-only selection-fold evaluation for Aura return candidates.

This command is the only Phase 4 entry point that performs estimator fitting.
It must be run manually by the user. It reads persisted local PostgreSQL market
data, never fetches provider data, and never writes database or model artifacts.
"""

from __future__ import annotations

import argparse
from collections.abc import Sequence
from dataclasses import asdict, dataclass, replace
from datetime import date, timedelta
import json
from pathlib import Path
import sys

from sqlalchemy.exc import SQLAlchemyError


BACKEND_DIR = Path(__file__).resolve().parents[1]
if str(BACKEND_DIR) not in sys.path:
    sys.path.insert(0, str(BACKEND_DIR))

from app.core.instruments import USER_ASSET_SYMBOLS
from app.database.connection import (
    create_database_engine,
    create_session_factory,
    session_scope,
)
from app.forecasting.baselines import (
    HistoricalMeanBaseline,
    MovingAverageBaseline,
)
from app.forecasting.data import (
    AssetPriceHistory,
    build_forecast_dataset,
    build_price_histories,
)
from app.forecasting.evaluation import (
    ForecastCandidate,
    ForecastEvaluationResult,
    ForecastTargetType,
    evaluate_candidate,
)
from app.forecasting.models import (
    ArimaCandidate,
    LinearRegressionCandidate,
    RandomForestCandidate,
)
from app.forecasting.selection import (
    SymbolSelectionSummary,
    summarize_symbol_selection,
)
from app.forecasting.splits import (
    EvaluationPlanConfig,
    FoldPurpose,
    build_chronological_plan,
)
from app.services.market_data_service import MarketDataService
from backend.scripts.forecasting_selection_provenance import (
    DatabaseEnvironmentError, SelectionDataProvenance, SelectionProvenanceError,
    add_provenance_arguments, database_url_from_env_file, provenance_payload,
    validate_expectations, validate_explicit_database_url, verify_selection_records,
)


@dataclass(frozen=True, slots=True)
class ReturnModelEvaluationReport:
    """Deterministic selection-only candidate results and policy summaries."""

    evaluation_cutoff: date
    evaluation_end_exclusive: date
    requested_symbols: tuple[str, ...]
    evaluated_symbols: tuple[str, ...]
    missing_symbols: tuple[str, ...]
    selection_fold_ids: tuple[str, ...]
    candidate_ids: tuple[str, ...]
    results: tuple[ForecastEvaluationResult, ...]
    selection_summaries: tuple[SymbolSelectionSummary, ...]
    data_provenance: SelectionDataProvenance | None = None


def _parse_date(value: str) -> date:
    try:
        return date.fromisoformat(value)
    except ValueError as error:
        raise argparse.ArgumentTypeError(
            "date must use YYYY-MM-DD format"
        ) from error


def _return_candidates() -> tuple[ForecastCandidate, ...]:
    return (
        HistoricalMeanBaseline(),
        MovingAverageBaseline(),
        LinearRegressionCandidate(),
        ArimaCandidate(),
        RandomForestCandidate(),
    )


def evaluate_histories(
    histories: Sequence[AssetPriceHistory],
    *,
    evaluation_cutoff: date,
    candidates: Sequence[ForecastCandidate] | None = None,
) -> ReturnModelEvaluationReport:
    """Evaluate return candidates on selection folds only.

    Passing candidates is an internal test seam. The command-line path always
    uses the fixed five approved Phase 4 candidates.
    """
    if type(evaluation_cutoff) is not date:
        raise TypeError("evaluation_cutoff must be a date")
    evaluation_end_exclusive = evaluation_cutoff + timedelta(days=1)
    plan = build_chronological_plan(
        EvaluationPlanConfig(
            evaluation_end_exclusive=evaluation_end_exclusive,
        )
    )
    selection_fold_ids = tuple(
        fold.fold_id
        for fold in plan.folds
        if fold.purpose is FoldPurpose.SELECTION
    )
    approved_candidates = tuple(
        _return_candidates() if candidates is None else candidates
    )
    candidate_ids = tuple(
        candidate.candidate_id for candidate in approved_candidates
    )
    if len(set(candidate_ids)) != len(candidate_ids):
        raise ValueError("candidate identifiers must be unique")

    ordered_histories = tuple(sorted(histories, key=lambda item: item.symbol))
    results: list[ForecastEvaluationResult] = []
    summaries: list[SymbolSelectionSummary] = []
    for history in ordered_histories:
        dataset = build_forecast_dataset(history)
        symbol_results: list[ForecastEvaluationResult] = []
        for candidate in approved_candidates:
            symbol_results.extend(
                evaluate_candidate(
                    dataset=dataset,
                    plan=plan,
                    target_type=ForecastTargetType.RETURN,
                    candidate=candidate,
                    fold_purposes=(FoldPurpose.SELECTION,),
                )
            )
        ordered_symbol_results = tuple(symbol_results)
        results.extend(ordered_symbol_results)
        summaries.append(
            summarize_symbol_selection(
                symbol=history.symbol,
                results=ordered_symbol_results,
                expected_selection_fold_ids=selection_fold_ids,
            )
        )

    evaluated_symbols = tuple(history.symbol for history in ordered_histories)
    evaluated_set = set(evaluated_symbols)
    return ReturnModelEvaluationReport(
        evaluation_cutoff=evaluation_cutoff,
        evaluation_end_exclusive=evaluation_end_exclusive,
        requested_symbols=USER_ASSET_SYMBOLS,
        evaluated_symbols=evaluated_symbols,
        missing_symbols=tuple(
            symbol for symbol in USER_ASSET_SYMBOLS if symbol not in evaluated_set
        ),
        selection_fold_ids=selection_fold_ids,
        candidate_ids=candidate_ids,
        results=tuple(results),
        selection_summaries=tuple(summaries),
    )


def run_persisted_return_model_evaluation(
    *,
    evaluation_cutoff: date,
    database_url: str,
    expected_market_data_fingerprint: str | None = None,
    expected_row_count: int | None = None,
) -> ReturnModelEvaluationReport:
    """Read persisted market data and run the user-triggered comparison."""
    if type(evaluation_cutoff) is not date:
        raise TypeError("evaluation_cutoff must be a date")
    validate_expectations(expected_market_data_fingerprint, expected_row_count)
    validate_explicit_database_url(database_url)
    try:
        engine = create_database_engine(database_url)
    except SQLAlchemyError:
        raise RuntimeError("selected evaluation database is unavailable") from None
    try:
        session_factory = create_session_factory(engine)
        with session_scope(session_factory) as session:
            records = tuple(
                MarketDataService(session).get_range(
                    USER_ASSET_SYMBOLS, date.min, evaluation_cutoff,
                )
            )
            provenance = verify_selection_records(
                records, evaluation_cutoff=evaluation_cutoff,
                expected_fingerprint=expected_market_data_fingerprint,
                expected_row_count=expected_row_count,
            )
            histories = build_price_histories(records)
        report = evaluate_histories(
            histories,
            evaluation_cutoff=evaluation_cutoff,
        )
        return replace(report, data_provenance=provenance)
    except SQLAlchemyError:
        raise RuntimeError("selected evaluation database is unavailable") from None
    finally:
        engine.dispose()


def _result_dict(result: ForecastEvaluationResult) -> dict[str, object]:
    payload = asdict(result)
    payload.pop("negative_prediction_clipped_count", None)
    for key in (
        "training_cutoff",
        "evaluation_origin_start",
        "evaluation_origin_end",
    ):
        payload[key] = payload[key].isoformat()
    return payload


def report_json(report: ReturnModelEvaluationReport) -> str:
    """Return strict deterministic JSON without NaN or Infinity."""
    payload = {
        "data_provenance": provenance_payload(
            report.data_provenance, evaluation_cutoff=report.evaluation_cutoff,
        ),
        "evaluation_cutoff": report.evaluation_cutoff.isoformat(),
        "evaluation_end_exclusive": report.evaluation_end_exclusive.isoformat(),
        "requested_symbols": list(report.requested_symbols),
        "evaluated_symbols": list(report.evaluated_symbols),
        "missing_symbols": list(report.missing_symbols),
        "selection_fold_ids": list(report.selection_fold_ids),
        "candidate_ids": list(report.candidate_ids),
        "results": [_result_dict(result) for result in report.results],
        "selection_summaries": [
            asdict(summary) for summary in report.selection_summaries
        ],
    }
    return json.dumps(
        payload,
        indent=2,
        sort_keys=True,
        allow_nan=False,
    ) + "\n"


def _print_summary(
    report: ReturnModelEvaluationReport,
    output_path: Path,
) -> None:
    available = sum(result.prediction_available for result in report.results)
    unavailable = len(report.results) - available
    baseline_leaders = sum(
        summary.baseline_remains_leading
        for summary in report.selection_summaries
    )
    print("Aura return-model selection evaluation completed.")
    print("-------------------------------------------------")
    print(f"Evaluation cutoff: {report.evaluation_cutoff.isoformat()}")
    verified = bool(report.data_provenance and report.data_provenance.provenance_verified)
    print(f"Provenance verified: {verified}")
    print(f"Symbols evaluated: {len(report.evaluated_symbols)}")
    print(f"Selection folds: {len(report.selection_fold_ids)}")
    print(f"Available candidate-fold results: {available}")
    print(f"Unavailable candidate-fold results: {unavailable}")
    print(f"Symbols retaining a baseline lead: {baseline_leaders}")
    print(f"JSON report: {output_path}")
    if report.missing_symbols:
        print(f"Missing symbols: {', '.join(report.missing_symbols)}")


def _build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description=(
            "Read persisted Aura market data and compare approved return "
            "candidates on selection folds only."
        )
    )
    parser.add_argument(
        "--evaluation-cutoff",
        type=_parse_date,
        required=True,
        help="Inclusive persisted-data cutoff in YYYY-MM-DD format.",
    )
    parser.add_argument(
        "--output",
        type=Path,
        required=True,
        help="Path for the strict JSON selection report.",
    )
    add_provenance_arguments(parser)
    return parser


def main(argv: Sequence[str] | None = None) -> None:
    args = _build_parser().parse_args(argv)
    try:
        validate_expectations(
            args.expected_market_data_fingerprint, args.expected_row_count,
        )
        report = run_persisted_return_model_evaluation(
            evaluation_cutoff=args.evaluation_cutoff,
            database_url=database_url_from_env_file(
                args.env_file, database_url_key=args.database_url_key,
            ),
            expected_market_data_fingerprint=args.expected_market_data_fingerprint,
            expected_row_count=args.expected_row_count,
        )
        args.output.write_text(report_json(report), encoding="utf-8")
    except (DatabaseEnvironmentError, SelectionProvenanceError) as error:
        raise SystemExit(f"Aura return-model evaluation failed: {error}") from None
    except (
        OSError,
        SQLAlchemyError,
        TypeError,
        ValueError,
        RuntimeError,
    ):
        raise SystemExit(
            "Aura return-model evaluation failed: unable to read, evaluate, or write the selected dataset."
        ) from None
    _print_summary(report, args.output)


if __name__ == "__main__":
    main()
