"""User-run, provenance-gated offline selection for 7/14/21-day forecasts.

Reads the explicitly selected local PostgreSQL snapshot in a read-only
transaction. Fits selection-fold candidates only; produces new evidence, never
deployment artifacts, calibration, final-test results or provider downloads.
"""

from __future__ import annotations

import argparse
from collections.abc import Callable, Sequence
from dataclasses import asdict
from datetime import date, timedelta
import json
from pathlib import Path
import sys

from sqlalchemy import text
from sqlalchemy.engine import make_url
from sqlalchemy.exc import SQLAlchemyError


REPOSITORY_ROOT = Path(__file__).resolve().parents[2]
BACKEND_DIR = REPOSITORY_ROOT / "backend"
if str(BACKEND_DIR) not in sys.path:
    sys.path.insert(0, str(BACKEND_DIR))

from app.core.instruments import USER_ASSET_SYMBOLS
from app.database.connection import create_database_engine, create_session_factory, session_scope
from app.forecasting.data import AssetPriceHistory, build_price_histories
from app.forecasting.evaluation import ForecastTargetType
from app.forecasting.features import FEATURE_SET_VERSION, build_feature_rows
from app.forecasting.multi_horizon import (
    NEW_HORIZONS, SUPPORTED_HORIZONS, build_horizon_dataset,
    evaluate_horizon_selection, horizon_candidates, target_name, target_version,
    validate_horizon,
)
from app.forecasting.targets import MAX_ENDPOINT_SLIPPAGE_DAYS
from app.forecasting.selection import (
    MINIMUM_COMPLEX_MODEL_IMPROVEMENT_PERCENT, PRACTICAL_TIE_PERCENT,
)
from app.forecasting.splits import EvaluationPlanConfig, FoldPurpose, build_chronological_plan
from app.services.market_data_service import MarketDataService
from backend.scripts.forecasting_selection_provenance import (
    DatabaseEnvironmentError, SelectionProvenanceError,
    database_url_from_env_file, provenance_payload, validate_expectations,
    verify_selection_records,
)


REPORT_SCHEMA = "forecast-horizon-selection-v1"


def validate_local_database_url(database_url: str) -> None:
    """No fallback or remote training source; never include the URL in errors."""
    try:
        url = make_url(database_url)
        valid = (url.drivername == "postgresql+psycopg"
                 and url.host in {"127.0.0.1", "localhost", "::1"}
                 and url.port == 5433 and bool(url.database)
                 and not (set(url.query) - {"sslmode"})
                 and url.query.get("sslmode", "disable") == "disable")
    except (TypeError, ValueError, SQLAlchemyError):
        valid = False
    if not valid:
        raise SelectionProvenanceError("use the explicit local PostgreSQL snapshot on port 5433")


def validate_output_path(path: Path) -> Path:
    """New JSON evidence only; protect frozen V1 evidence and all artifacts."""
    resolved = path.resolve()
    evidence = (REPOSITORY_ROOT / "forecasting-evidence").resolve()
    frozen_evidence = evidence / "forecast-v1-20260917"
    if (not resolved.is_relative_to(evidence)
        or resolved.is_relative_to(frozen_evidence)
        or resolved.suffix.lower() != ".json"):
        raise ValueError("output must be a new JSON file under a separate forecasting-evidence folder")
    if resolved.exists():
        raise ValueError("output already exists; choose a new evidence filename")
    return resolved


def evaluate_histories(
    histories: Sequence[AssetPriceHistory], *, evaluation_cutoff: date,
    horizons: Sequence[int] = NEW_HORIZONS,
    progress: Callable[[str], None] | None = None,
) -> dict[str, object]:
    """Pure orchestration seam; estimator execution is explicitly user-triggered."""
    if type(evaluation_cutoff) is not date:
        raise TypeError("evaluation cutoff must be a date")
    requested = tuple(horizons)
    if not requested or len(set(requested)) != len(requested):
        raise ValueError("horizons must be non-empty and unique")
    for horizon in requested:
        validate_horizon(horizon)
    ordered = tuple(sorted(histories, key=lambda item: item.symbol))
    symbols = tuple(history.symbol for history in ordered)
    if len(set(symbols)) != len(symbols):
        raise ValueError("histories must contain unique symbols")
    if any(item.date > evaluation_cutoff for history in ordered for item in history.observations):
        raise ValueError("history exceeds the explicit evaluation cutoff")
    plan = build_chronological_plan(EvaluationPlanConfig(
        evaluation_end_exclusive=evaluation_cutoff + timedelta(days=1),
    ))
    feature_rows = {history.symbol: build_feature_rows(history) for history in ordered}
    groups = []
    for horizon in sorted(requested):
        for history in ordered:
            dataset = build_horizon_dataset(
                history, horizon_days=horizon, features=feature_rows[history.symbol],
            )
            for target_type in (ForecastTargetType.RETURN, ForecastTargetType.VOLATILITY):
                name = target_name(target_type, horizon)
                if progress:
                    progress(f"Evaluating {history.symbol} {name} on selection folds only...")
                candidates = horizon_candidates(target_type)
                results, summary = evaluate_horizon_selection(
                    dataset=dataset, plan=plan, target_type=target_type, candidates=candidates,
                )
                serialized = []
                for result in results:
                    payload = asdict(result)
                    # Legacy candidate enum names never leak into shorter-horizon evidence.
                    payload["target_type"] = name
                    payload["horizon_days"] = horizon
                    if target_type is ForecastTargetType.RETURN:
                        payload.pop("negative_prediction_clipped_count", None)
                    serialized.append(payload)
                groups.append({
                    "symbol": history.symbol, "horizon_days": horizon,
                    "target_type": name, "target_set_version": target_version(horizon),
                    "feature_set_version": FEATURE_SET_VERSION,
                    "candidate_ids": [candidate.candidate_id for candidate in candidates],
                    "price_observation_count": dataset.price_observation_count,
                    "feature_origin_count": dataset.feature_origin_count,
                    "target_origin_count": dataset.target_origin_count,
                    "label_complete_origin_count": len(dataset.rows),
                    "results": serialized, "selection_summary": asdict(summary),
                })
    return {
        "report_schema": REPORT_SCHEMA,
        "stage": "selection_only_not_deployable",
        "evaluation_cutoff": evaluation_cutoff,
        "evaluation_end_exclusive": plan.config.evaluation_end_exclusive,
        "horizons": sorted(requested), "horizon_unit": "calendar_days",
        "target_definition": {
            "return": "endpoint_price / origin_price - 1",
            "realized_volatility": "sqrt(sum(consecutive future log returns squared))",
            "annualized": False,
            "endpoint": "first stored observation on or after origin plus horizon",
            "maximum_endpoint_slippage_days": MAX_ENDPOINT_SLIPPAGE_DAYS,
        },
        "requested_symbols": list(USER_ASSET_SYMBOLS), "evaluated_symbols": list(symbols),
        "missing_symbols": [symbol for symbol in USER_ASSET_SYMBOLS if symbol not in symbols],
        "evaluation_plan": asdict(plan.config),
        "selection_folds": [asdict(fold) for fold in plan.folds if fold.purpose is FoldPurpose.SELECTION],
        "selection_policy": {
            "minimum_complex_model_improvement_percent": MINIMUM_COMPLEX_MODEL_IMPROVEMENT_PERCENT,
            "practical_tie_percent": PRACTICAL_TIE_PERCENT,
        },
        "data_provenance": provenance_payload(None, evaluation_cutoff=evaluation_cutoff),
        "groups": groups,
        "limitations": [
            "Selection evidence is not calibration, final-test performance or a deployment artifact.",
            "Volatility is non-annualized; missing observations are not filled.",
            "Training labels finish before each fold start; scored labels finish before that fold end.",
            "Reusing a V1 snapshot does not create a wholly new untouched project-level holdout.",
            "Each horizon needs its own frozen selection, interval calibration, final test and versioned artifacts before activation.",
        ],
    }


def run_persisted_evaluation(
    *, database_url: str, evaluation_cutoff: date, horizons: Sequence[int],
    expected_market_data_fingerprint: str, expected_row_count: int,
    progress: Callable[[str], None] | None = None,
) -> dict[str, object]:
    validate_expectations(expected_market_data_fingerprint, expected_row_count)
    if expected_market_data_fingerprint is None or expected_row_count is None:
        raise SelectionProvenanceError("verified fingerprint and row count are required")
    if type(evaluation_cutoff) is not date:
        raise TypeError("evaluation cutoff must be a date")
    if not horizons or len(set(horizons)) != len(horizons):
        raise ValueError("horizons must be non-empty and unique")
    for horizon in horizons:
        validate_horizon(horizon)
    validate_local_database_url(database_url)
    engine = create_database_engine(database_url, isolated=True)
    try:
        factory = create_session_factory(engine)
        with session_scope(factory) as session:
            session.execute(text("SET TRANSACTION READ ONLY"))
            records = tuple(MarketDataService(session).get_range(
                USER_ASSET_SYMBOLS, date.min, evaluation_cutoff,
            ))
            provenance = verify_selection_records(
                records, evaluation_cutoff=evaluation_cutoff,
                expected_fingerprint=expected_market_data_fingerprint,
                expected_row_count=expected_row_count,
            )
            histories = build_price_histories(records)
        if {history.symbol for history in histories} != set(USER_ASSET_SYMBOLS):
            raise SelectionProvenanceError("the verified snapshot must include all 17 user assets")
    finally:
        engine.dispose()
    # Database resources are closed before expensive estimator fitting begins.
    report = evaluate_histories(histories, evaluation_cutoff=evaluation_cutoff,
                                horizons=horizons, progress=progress)
    report["data_provenance"] = provenance_payload(provenance, evaluation_cutoff=evaluation_cutoff)
    return report


def report_json(report: dict[str, object]) -> str:
    def serialize(value: object) -> str:
        if type(value) is date:
            return value.isoformat()
        raise TypeError("report contains an unsupported value")
    return json.dumps(report, default=serialize, indent=2, sort_keys=True, allow_nan=False) + "\n"


def _parse_date(value: str) -> date:
    try:
        return date.fromisoformat(value)
    except ValueError:
        raise argparse.ArgumentTypeError("date must use YYYY-MM-DD") from None


def _build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Evaluate new forecast horizons offline; do not activate models.")
    parser.add_argument("--env-file", type=Path, required=True)
    parser.add_argument("--database-url-key", default="TEST_DATABASE_URL")
    parser.add_argument("--evaluation-cutoff", type=_parse_date, required=True)
    parser.add_argument("--horizons", type=int, choices=SUPPORTED_HORIZONS, nargs="+", default=NEW_HORIZONS)
    parser.add_argument("--expected-market-data-fingerprint", required=True)
    parser.add_argument("--expected-row-count", type=int, required=True)
    parser.add_argument("--output", type=Path, required=True)
    return parser


def main(argv: Sequence[str] | None = None) -> None:
    args = _build_parser().parse_args(argv)
    try:
        output = validate_output_path(args.output)
        report = run_persisted_evaluation(
            database_url=database_url_from_env_file(args.env_file, database_url_key=args.database_url_key),
            evaluation_cutoff=args.evaluation_cutoff, horizons=args.horizons,
            expected_market_data_fingerprint=args.expected_market_data_fingerprint,
            expected_row_count=args.expected_row_count,
            progress=lambda message: print(message, flush=True),
        )
        payload = report_json(report)
        output.parent.mkdir(parents=True, exist_ok=True)
        # Revalidate after fitting: refuse races, symlink changes and overwrites.
        if validate_output_path(args.output) != output:
            raise ValueError("output destination changed during evaluation")
        with output.open("x", encoding="utf-8") as stream:
            stream.write(payload)
    except (DatabaseEnvironmentError, SelectionProvenanceError) as error:
        raise SystemExit(f"Horizon selection stopped: {error}") from None
    except (OSError, SQLAlchemyError, TypeError, ValueError, RuntimeError, OverflowError):
        raise SystemExit("Horizon selection failed: input, database, model or new-output validation failed; no deployment was activated.") from None
    print("Horizon selection evidence written. No calibration, final test or artifact training was run.")
    print(f"Report: {output}")


if __name__ == "__main__":
    main()
