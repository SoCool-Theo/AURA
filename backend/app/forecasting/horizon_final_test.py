"""Offline weekly final scoring using frozen candidates and residual ranges."""

from __future__ import annotations

from collections.abc import Callable, Sequence
from dataclasses import asdict
from datetime import date
import json
import math
from numbers import Real

from ..core.instruments import USER_ASSET_SYMBOLS
from .data import AssetPriceHistory
from .evaluation import ForecastTargetType
from .features import FEATURE_SET_VERSION, build_feature_rows
from .finalization import (
    CALIBRATION_MINIMUM_OBSERVATIONS, LOWER_RESIDUAL_QUANTILE, NOMINAL_INTERVAL_COVERAGE,
    UPPER_RESIDUAL_QUANTILE, ForecastFinalizationError, evaluate_frozen_selection_fold, prediction_interval,
)
from .fingerprints import canonical_json_bytes, sha256_bytes
from .horizon_calibration import CALIBRATION_FOLD, PLAN, REPORT_SCHEMA as CALIBRATION_SCHEMA, STAGE as CALIBRATION_STAGE
from .horizon_selection_manifest import (
    RELEASE_VERSION, SELECTION_COUNT, FrozenHorizonManifest, FrozenHorizonSelection,
    horizon_manifest_from_dict, horizon_manifest_json, validate_digest,
)
from .models import ARIMA_CANDIDATE_ID, VOLATILITY_ARIMA_CANDIDATE_ID, ARIMA_FIT_CONVERGENCE_WARNING
from .multi_horizon import NEW_HORIZONS, HorizonDataset, _candidate_dataset, build_horizon_dataset, target_name, target_version
from .selection_manifest import OFFICIAL_EVALUATION_CUTOFF
from .splits import FoldPurpose, slice_dataset_for_fold
from .targets import MAX_ENDPOINT_SLIPPAGE_DAYS


REPORT_SCHEMA = "forecast-horizon-final-test-v1"
STAGE = "final_test_only_not_deployable"
FINAL_FOLD = next(fold for fold in PLAN.folds if fold.purpose is FoldPurpose.FINAL_TEST)


def _metric(value: object) -> float:
    if isinstance(value, bool) or not isinstance(value, Real) or not math.isfinite(value):
        raise ForecastFinalizationError("evidence metrics must be finite numbers")
    return float(value)


def _count(value: object, minimum: int = 0) -> int:
    if type(value) is not int or value < minimum:
        raise ForecastFinalizationError("calibration observation count is invalid")
    return value


def _date(value: object) -> date:
    parsed = date.fromisoformat(value)
    if parsed.isoformat() != value:
        raise ForecastFinalizationError("calibration date is not canonical")
    return parsed


def validate_calibration_report(
    payload: object, *, manifest: FrozenHorizonManifest, expected_calibration_sha256: str,
) -> tuple[dict[str, object], ...]:
    """Validate pinned calibration evidence without refitting or recalibrating."""
    try:
        expected = validate_digest(expected_calibration_sha256)
        if not isinstance(payload, dict):
            raise ForecastFinalizationError("calibration report must be an object")
        base = {key: value for key, value in payload.items() if key != "calibration_sha256"}
        if payload.get("calibration_sha256") != expected or sha256_bytes(canonical_json_bytes(base)) != expected:
            raise ForecastFinalizationError("calibration checksum differs from the reviewed evidence")
        fixed = {
            "report_schema": CALIBRATION_SCHEMA, "release_version": RELEASE_VERSION, "stage": CALIBRATION_STAGE,
            "evaluation_cutoff": OFFICIAL_EVALUATION_CUTOFF.isoformat(), "horizons": list(NEW_HORIZONS),
            "horizon_unit": "calendar_days", "record_count": SELECTION_COUNT,
            "selection_manifest_sha256": manifest.manifest_sha256,
            "source_selection_report_sha256": manifest.source_selection_report_sha256,
            "approved_market_data_fingerprint_sha256": manifest.market_data_fingerprint_sha256,
            "approved_market_data_row_count": manifest.market_data_row_count,
            "data_provenance": {"provenance_verified": True, "evaluation_cutoff": OFFICIAL_EVALUATION_CUTOFF.isoformat(),
                                "symbol_count": len(USER_ASSET_SYMBOLS), "row_count": manifest.market_data_row_count,
                                "market_data_fingerprint_sha256": manifest.market_data_fingerprint_sha256},
            "evaluation_plan": {**asdict(PLAN.config), "evaluation_end_exclusive": PLAN.config.evaluation_end_exclusive.isoformat()},
            "calibration_fold": {"fold_id": CALIBRATION_FOLD.fold_id, "purpose": "calibration",
                                 "origin_start": CALIBRATION_FOLD.origin_start.isoformat(), "origin_end": CALIBRATION_FOLD.origin_end.isoformat()},
            "interval_method": {"method": "empirical_actual_minus_prediction_residual_quantiles", "quantile_interpolation": "linear",
                                "nominal_coverage": NOMINAL_INTERVAL_COVERAGE, "lower_quantile": LOWER_RESIDUAL_QUANTILE,
                                "upper_quantile": UPPER_RESIDUAL_QUANTILE, "minimum_observations": CALIBRATION_MINIMUM_OBSERVATIONS},
            "final_test_completed": False, "deployment_artifacts_created": False,
        }
        if canonical_json_bytes({key: payload.get(key) for key in fixed}) != canonical_json_bytes(fixed):
            raise ForecastFinalizationError("calibration contract or provenance differs from frozen inputs")
        records = payload.get("records")
        if not isinstance(records, list) or len(records) != SELECTION_COUNT:
            raise ForecastFinalizationError("calibration requires 102 ordered records")
        for record, frozen in zip(records, manifest.records, strict=True):
            if not isinstance(record, dict):
                raise ForecastFinalizationError("calibration record is malformed")
            selection, horizon = frozen.selection, frozen.horizon_days
            identity = {
                "symbol": selection.symbol, "horizon_days": horizon, "target_type": target_name(selection.target_type, horizon),
                "selected_candidate_id": selection.selected_candidate_id, "selection_warning": selection.selection_warning,
                "feature_set_version": FEATURE_SET_VERSION, "target_set_version": target_version(horizon),
                "fold_id": CALIBRATION_FOLD.fold_id, "training_cutoff_exclusive": CALIBRATION_FOLD.origin_start.isoformat(),
                "evaluation_origin_start": CALIBRATION_FOLD.origin_start.isoformat(),
                "evaluation_origin_end_exclusive": CALIBRATION_FOLD.origin_end.isoformat(),
            }
            if canonical_json_bytes({key: record.get(key) for key in identity}) != canonical_json_bytes(identity):
                raise ForecastFinalizationError("calibration record order, identity or warning differs from selection")
            observations = _count(record.get("observation_count"), CALIBRATION_MINIMUM_OBSERVATIONS)
            _count(record.get("training_observation_count"), PLAN.config.minimum_training_origins)
            if (_metric(record.get("mae")) < 0 or _metric(record.get("rmse")) < 0
                or _metric(record.get("residual_q10")) > _metric(record.get("residual_q90"))):
                raise ForecastFinalizationError("calibration error metrics or quantiles are invalid")
            warning = record.get("warning")
            if warning is not None and (warning != ARIMA_FIT_CONVERGENCE_WARNING
                or selection.selected_candidate_id not in {ARIMA_CANDIDATE_ID, VOLATILITY_ARIMA_CANDIDATE_ID}):
                raise ForecastFinalizationError("calibration fit warning is unsupported")
            clipping = record.get("negative_prediction_clipped_count")
            if selection.target_type is ForecastTargetType.VOLATILITY:
                if _count(clipping) > observations:
                    raise ForecastFinalizationError("calibration clipping count exceeds observations")
            elif clipping is not None:
                raise ForecastFinalizationError("return calibration cannot contain volatility clipping")
            train_min, train_max, train_endpoint = (_date(record[key]) for key in
                ("training_origin_min", "training_origin_max", "training_endpoint_max"))
            origin_min, origin_max, endpoint_max = (_date(record[key]) for key in
                ("evaluated_origin_min", "evaluated_origin_max", "evaluated_endpoint_max"))
            if not (train_min <= train_max < train_endpoint < CALIBRATION_FOLD.origin_start
                    <= origin_min <= origin_max < endpoint_max < CALIBRATION_FOLD.origin_end
                    and horizon <= (train_endpoint - train_max).days <= horizon + MAX_ENDPOINT_SLIPPAGE_DAYS
                    and horizon <= (endpoint_max - origin_max).days <= horizon + MAX_ENDPOINT_SLIPPAGE_DAYS):
                raise ForecastFinalizationError("calibration endpoint/origin boundaries are invalid")
        return tuple(records)
    except ForecastFinalizationError:
        raise
    except (KeyError, TypeError, ValueError, OverflowError) as error:
        raise ForecastFinalizationError("calibration evidence is malformed") from error


def interval_coverage(
    *, actual_values: Sequence[float], prediction_values: Sequence[float], residual_q10: float,
    residual_q90: float, target_type: ForecastTargetType,
) -> dict[str, object]:
    """Inclusive coverage; empty volatility intervals count as misses, not repairs."""
    if not actual_values or len(actual_values) != len(prediction_values):
        raise ForecastFinalizationError("coverage requires aligned nonempty predictions and actuals")
    if target_type not in (ForecastTargetType.RETURN, ForecastTargetType.VOLATILITY) or not isinstance(target_type, ForecastTargetType):
        raise ForecastFinalizationError("coverage target type is invalid")
    _metric(residual_q10)
    _metric(residual_q90)
    covered = below = above = empty = 0
    widths = []
    for actual, prediction in zip(actual_values, prediction_values, strict=True):
        actual, prediction = _metric(actual), _metric(prediction)
        if target_type is ForecastTargetType.VOLATILITY and (actual < 0 or prediction < 0):
            raise ForecastFinalizationError("volatility coverage requires clipped nonnegative values")
        lower, upper = prediction_interval(point_prediction=prediction, residual_q10=residual_q10,
                                            residual_q90=residual_q90, target_type=target_type)
        if lower > upper:
            empty += 1
            continue
        width = upper - lower
        if not math.isfinite(width):
            raise ForecastFinalizationError("interval width is not finite")
        widths.append(width)
        if actual < lower:
            below += 1
        elif actual > upper:
            above += 1
        else:
            covered += 1
    count = len(actual_values)
    # Scale before fsum to avoid overflow when many valid finite widths are large.
    mean_width = math.fsum(width / len(widths) for width in widths) if widths else None
    if mean_width is not None and not math.isfinite(mean_width):
        raise ForecastFinalizationError("mean interval width is not finite")
    return {"observation_count": count, "nominal_coverage": NOMINAL_INTERVAL_COVERAGE,
            "empirical_coverage": covered / count, "covered_count": covered, "missed_count": count - covered,
            "below_interval_count": below, "above_interval_count": above, "empty_interval_count": empty,
            "valid_interval_count": len(widths), "mean_valid_interval_width": mean_width,
            "warning": "empty_volatility_intervals_counted_as_misses" if empty else None}


def evaluate_horizon_final_test(
    *, dataset: HorizonDataset, frozen: FrozenHorizonSelection, calibration: dict[str, object],
) -> dict[str, object]:
    selection, horizon = frozen.selection, frozen.horizon_days
    if (type(horizon) is not int or horizon not in NEW_HORIZONS or dataset.horizon_days != horizon
        or dataset.symbol != selection.symbol or selection.evaluation_cutoff != OFFICIAL_EVALUATION_CUTOFF
        or calibration.get("symbol") != selection.symbol or calibration.get("horizon_days") != horizon
        or calibration.get("target_type") != target_name(selection.target_type, horizon)
        or calibration.get("selected_candidate_id") != selection.selected_candidate_id):
        raise ForecastFinalizationError("final-test dataset, selection and calibration differ")
    q10, q90 = _metric(calibration.get("residual_q10")), _metric(calibration.get("residual_q90"))
    if q10 > q90:
        raise ForecastFinalizationError("frozen residual quantiles are reversed")
    bridged = _candidate_dataset(dataset, endpoint_before=FINAL_FOLD.origin_end)
    sliced = slice_dataset_for_fold(bridged, FINAL_FOLD, minimum_training_origins=PLAN.config.minimum_training_origins)
    if not sliced.training_eligible or not sliced.evaluation_rows:
        raise ForecastFinalizationError("final test requires eligible training history and usable test rows")
    evaluated = evaluate_frozen_selection_fold(dataset=bridged, plan=PLAN, selection=selection, purpose=FoldPurpose.FINAL_TEST)
    if (evaluated.symbol != selection.symbol or evaluated.target_type is not selection.target_type
        or evaluated.candidate_id != selection.selected_candidate_id or evaluated.fold_id != FINAL_FOLD.fold_id
        or evaluated.fold_purpose is not FoldPurpose.FINAL_TEST
        or evaluated.training_observation_count != len(sliced.training_rows)
        or evaluated.evaluated_observation_count != len(sliced.evaluation_rows)
        or len(evaluated.actual_values) != len(sliced.evaluation_rows)
        or _metric(evaluated.mae) < 0 or _metric(evaluated.rmse) < 0):
        raise ForecastFinalizationError("final-test result differs from frozen inputs")
    coverage = interval_coverage(actual_values=evaluated.actual_values, prediction_values=evaluated.prediction_values,
                                 residual_q10=q10, residual_q90=q90, target_type=selection.target_type)
    return {
        "symbol": selection.symbol, "horizon_days": horizon, "target_type": target_name(selection.target_type, horizon),
        "selected_candidate_id": selection.selected_candidate_id, "feature_set_version": FEATURE_SET_VERSION,
        "target_set_version": target_version(horizon), "fold_id": FINAL_FOLD.fold_id,
        "observation_count": evaluated.evaluated_observation_count,
        "training_observation_count": evaluated.training_observation_count,
        "candidate_training_value_count": evaluated.candidate_training_value_count,
        "mae": evaluated.mae, "rmse": evaluated.rmse, "directional_accuracy": evaluated.directional_accuracy,
        "negative_prediction_clipped_count": evaluated.negative_prediction_clipped_count,
        "selection_warning": selection.selection_warning, "calibration_warning": calibration.get("warning"), "warning": evaluated.warning,
        "frozen_residual_q10": q10, "frozen_residual_q90": q90, "interval_coverage": coverage,
        "training_cutoff_exclusive": FINAL_FOLD.origin_start.isoformat(),
        "training_origin_min": min(row.features.origin_date for row in sliced.training_rows).isoformat(),
        "training_origin_max": max(row.features.origin_date for row in sliced.training_rows).isoformat(),
        "training_endpoint_max": max(row.target.endpoint_date for row in sliced.training_rows).isoformat(),
        "evaluation_origin_start": FINAL_FOLD.origin_start.isoformat(), "evaluation_origin_end_exclusive": FINAL_FOLD.origin_end.isoformat(),
        "evaluated_origin_min": min(row.features.origin_date for row in sliced.evaluation_rows).isoformat(),
        "evaluated_origin_max": max(row.features.origin_date for row in sliced.evaluation_rows).isoformat(),
        "evaluated_endpoint_max": max(row.target.endpoint_date for row in sliced.evaluation_rows).isoformat(),
    }


def evaluate_final_histories(
    histories: Sequence[AssetPriceHistory], *, manifest: FrozenHorizonManifest,
    calibration_report: dict[str, object], expected_calibration_sha256: str,
    progress: Callable[[str], None] | None = None,
) -> dict[str, object]:
    manifest = horizon_manifest_from_dict(json.loads(horizon_manifest_json(manifest)))
    calibration_records = validate_calibration_report(calibration_report, manifest=manifest,
                                                       expected_calibration_sha256=expected_calibration_sha256)
    ordered = tuple(sorted(histories, key=lambda history: history.symbol))
    if len(ordered) != len(USER_ASSET_SYMBOLS) or {history.symbol for history in ordered} != set(USER_ASSET_SYMBOLS):
        raise ForecastFinalizationError("final test requires all 17 unique assets")
    if any(row.date > OFFICIAL_EVALUATION_CUTOFF for history in ordered for row in history.observations):
        raise ForecastFinalizationError("history exceeds frozen cutoff")
    by_symbol = {history.symbol: history for history in ordered}
    features = {symbol: build_feature_rows(history) for symbol, history in by_symbol.items()}
    datasets, records = {}, []
    for frozen, calibration in zip(manifest.records, calibration_records, strict=True):
        key = (frozen.horizon_days, frozen.selection.symbol)
        if key not in datasets:
            datasets[key] = build_horizon_dataset(by_symbol[key[1]], horizon_days=key[0], features=features[key[1]])
        if progress:
            progress(f"Final testing {key[1]} {target_name(frozen.selection.target_type, key[0])}, frozen candidate and ranges...")
        records.append(evaluate_horizon_final_test(dataset=datasets[key], frozen=frozen, calibration=calibration))
    return {
        "report_schema": REPORT_SCHEMA, "release_version": RELEASE_VERSION, "stage": STAGE,
        "evaluation_cutoff": OFFICIAL_EVALUATION_CUTOFF.isoformat(), "horizons": list(NEW_HORIZONS), "horizon_unit": "calendar_days",
        "record_count": len(records), "selection_manifest_sha256": manifest.manifest_sha256,
        "source_selection_report_sha256": manifest.source_selection_report_sha256,
        "calibration_sha256": expected_calibration_sha256,
        "data_provenance": {"provenance_verified": False, "evaluation_cutoff": OFFICIAL_EVALUATION_CUTOFF.isoformat(),
                            "symbol_count": None, "row_count": None, "market_data_fingerprint_sha256": None},
        "final_test_fold": {"fold_id": FINAL_FOLD.fold_id, "purpose": "final_test",
                            "origin_start": FINAL_FOLD.origin_start.isoformat(), "origin_end": FINAL_FOLD.origin_end.isoformat()},
        "nominal_interval_coverage": NOMINAL_INTERVAL_COVERAGE,
        "final_test_completed": True, "deployment_artifacts_created": False, "records": records,
        "limitations": [
            "Final scoring preserves all frozen candidates and calibration ranges; poor results are not retuned or hidden.",
            "Candidates fit only labels completed before the final-test fold starts; scoring endpoints precede its end.",
            "Intervals use frozen empirical residual quantiles; nominal 80% coverage is not guaranteed.",
            "Empty clipped volatility intervals count as misses and are excluded only from valid-width averages.",
            "Overlapping labels are not independent observations; no calibrated portfolio interval exists.",
            "The reused V1 snapshot is not a new untouched project-level holdout.",
            "Completion is not predictive-quality acceptance, deployment fitting, runtime support or client activation.",
        ],
    }


def final_test_report_json(report: dict[str, object]) -> str:
    if "final_test_sha256" in report:
        raise ForecastFinalizationError("final-test checksum must be computed from unhashed evidence")
    digest = sha256_bytes(canonical_json_bytes(report))
    return json.dumps({**report, "final_test_sha256": digest}, allow_nan=False, indent=2, sort_keys=True) + "\n"
