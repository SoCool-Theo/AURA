"""Manual read-only evaluation of Aura's forecasting baselines.

This command reads persisted PostgreSQL market data and never calls a market
provider or writes model artifacts. It must be invoked manually by the user;
it is not part of API startup, scheduling, or production inference.
"""

from __future__ import annotations

import argparse
from collections.abc import Sequence
from dataclasses import asdict, dataclass
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
    ForecastEvaluationResult,
    ForecastTargetType,
    evaluate_candidate,
)
from app.forecasting.splits import (
    EvaluationPlanConfig,
    build_chronological_plan,
)
from app.services.market_data_service import MarketDataService


@dataclass(frozen=True, slots=True)
class BaselineEvaluationReport:
    """Deterministic metadata and internal evaluation results."""

    evaluation_cutoff: date
    evaluation_end_exclusive: date
    requested_symbols: tuple[str, ...]
    evaluated_symbols: tuple[str, ...]
    missing_symbols: tuple[str, ...]
    results: tuple[ForecastEvaluationResult, ...]


def _parse_date(value: str) -> date:
    try:
        return date.fromisoformat(value)
    except ValueError as error:
        raise argparse.ArgumentTypeError(
            "date must use YYYY-MM-DD format"
        ) from error


def evaluate_histories(
    histories: Sequence[AssetPriceHistory],
    *,
    evaluation_cutoff: date,
) -> BaselineEvaluationReport:
    """Apply both baselines to already-loaded histories without I/O."""
    if type(evaluation_cutoff) is not date:
        raise TypeError("evaluation_cutoff must be a date")
    evaluation_end_exclusive = evaluation_cutoff + timedelta(days=1)
    plan = build_chronological_plan(
        EvaluationPlanConfig(
            evaluation_end_exclusive=evaluation_end_exclusive,
        )
    )
    ordered_histories = tuple(sorted(histories, key=lambda item: item.symbol))
    baselines = (HistoricalMeanBaseline(), MovingAverageBaseline())
    target_types = (
        ForecastTargetType.RETURN,
        ForecastTargetType.VOLATILITY,
    )
    results: list[ForecastEvaluationResult] = []
    for history in ordered_histories:
        dataset = build_forecast_dataset(history)
        for target_type in target_types:
            for baseline in baselines:
                results.extend(
                    evaluate_candidate(
                        dataset=dataset,
                        plan=plan,
                        target_type=target_type,
                        candidate=baseline,
                    )
                )

    evaluated_symbols = tuple(history.symbol for history in ordered_histories)
    evaluated_set = set(evaluated_symbols)
    return BaselineEvaluationReport(
        evaluation_cutoff=evaluation_cutoff,
        evaluation_end_exclusive=evaluation_end_exclusive,
        requested_symbols=USER_ASSET_SYMBOLS,
        evaluated_symbols=evaluated_symbols,
        missing_symbols=tuple(
            symbol for symbol in USER_ASSET_SYMBOLS if symbol not in evaluated_set
        ),
        results=tuple(results),
    )


def run_persisted_baseline_evaluation(
    *,
    evaluation_cutoff: date,
) -> BaselineEvaluationReport:
    """Read persisted market data and evaluate without writing to PostgreSQL."""
    if type(evaluation_cutoff) is not date:
        raise TypeError("evaluation_cutoff must be a date")
    engine = create_database_engine()
    try:
        session_factory = create_session_factory(engine)
        with session_scope(session_factory) as session:
            records = MarketDataService(session).get_range(
                USER_ASSET_SYMBOLS,
                date.min,
                evaluation_cutoff,
            )
            histories = build_price_histories(records)
        return evaluate_histories(
            histories,
            evaluation_cutoff=evaluation_cutoff,
        )
    finally:
        engine.dispose()


def _result_dict(result: ForecastEvaluationResult) -> dict[str, object]:
    payload = asdict(result)
    for key in (
        "training_cutoff",
        "evaluation_origin_start",
        "evaluation_origin_end",
    ):
        payload[key] = payload[key].isoformat()
    return payload


def report_json(report: BaselineEvaluationReport) -> str:
    """Return strict deterministic JSON without NaN or Infinity."""
    payload = {
        "evaluation_cutoff": report.evaluation_cutoff.isoformat(),
        "evaluation_end_exclusive": report.evaluation_end_exclusive.isoformat(),
        "requested_symbols": list(report.requested_symbols),
        "evaluated_symbols": list(report.evaluated_symbols),
        "missing_symbols": list(report.missing_symbols),
        "results": [_result_dict(result) for result in report.results],
    }
    return json.dumps(
        payload,
        indent=2,
        sort_keys=True,
        allow_nan=False,
    ) + "\n"


def _print_summary(report: BaselineEvaluationReport, output_path: Path) -> None:
    available = sum(result.prediction_available for result in report.results)
    unavailable = len(report.results) - available
    print("Aura forecasting baseline evaluation completed.")
    print("----------------------------------------------")
    print(f"Evaluation cutoff: {report.evaluation_cutoff.isoformat()}")
    print(f"Symbols evaluated: {len(report.evaluated_symbols)}")
    print(f"Available fold results: {available}")
    print(f"Unavailable fold results: {unavailable}")
    print(f"JSON report: {output_path}")
    if report.missing_symbols:
        print(f"Missing symbols: {', '.join(report.missing_symbols)}")


def _build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description=(
            "Read persisted Aura market data and evaluate deterministic "
            "forecasting baselines chronologically."
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
        help="Path for the strict JSON evaluation report.",
    )
    return parser


def main(argv: Sequence[str] | None = None) -> None:
    args = _build_parser().parse_args(argv)
    try:
        report = run_persisted_baseline_evaluation(
            evaluation_cutoff=args.evaluation_cutoff,
        )
        args.output.write_text(report_json(report), encoding="utf-8")
    except (
        OSError,
        SQLAlchemyError,
        TypeError,
        ValueError,
        RuntimeError,
    ) as error:
        raise SystemExit(
            f"Aura forecasting baseline evaluation failed: {error}"
        ) from error
    _print_summary(report, args.output)


if __name__ == "__main__":
    main()
