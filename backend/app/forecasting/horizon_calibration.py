"""Offline weekly calibration, isolated from V1 and final-test outcomes."""

from __future__ import annotations

from collections.abc import Callable, Sequence
from dataclasses import asdict
from datetime import timedelta
import json

from ..core.instruments import USER_ASSET_SYMBOLS
from .data import AssetPriceHistory
from .features import FEATURE_SET_VERSION, build_feature_rows
from .finalization import (
    CALIBRATION_MINIMUM_OBSERVATIONS, LOWER_RESIDUAL_QUANTILE,
    NOMINAL_INTERVAL_COVERAGE, UPPER_RESIDUAL_QUANTILE,
    ForecastFinalizationError, calibrate_frozen_selection,
)
from .fingerprints import canonical_json_bytes, sha256_bytes
from .horizon_selection_manifest import (
    RELEASE_VERSION, FrozenHorizonManifest, FrozenHorizonSelection,
    horizon_manifest_from_dict, horizon_manifest_json,
)
from .multi_horizon import (
    NEW_HORIZONS, HorizonDataset, _candidate_dataset, build_horizon_dataset,
    target_name, target_version,
)
from .selection_manifest import OFFICIAL_EVALUATION_CUTOFF
from .splits import (
    EvaluationPlanConfig, FoldPurpose, build_chronological_plan, slice_dataset_for_fold,
)


REPORT_SCHEMA = "forecast-horizon-calibration-v1"
STAGE = "calibration_only_not_deployable"
PLAN = build_chronological_plan(EvaluationPlanConfig(OFFICIAL_EVALUATION_CUTOFF + timedelta(days=1)))
CALIBRATION_FOLD = next(fold for fold in PLAN.folds if fold.purpose is FoldPurpose.CALIBRATION)


def calibrate_horizon_selection(*, dataset: HorizonDataset, frozen: FrozenHorizonSelection) -> dict[str, object]:
    """Fit one frozen winner; purge training and scored endpoint boundaries."""
    selection = frozen.selection
    if (dataset.symbol != selection.symbol or dataset.horizon_days != frozen.horizon_days
        or frozen.horizon_days not in NEW_HORIZONS or selection.evaluation_cutoff != OFFICIAL_EVALUATION_CUTOFF):
        raise ForecastFinalizationError("calibration dataset and frozen horizon selection differ")
    # The private V1 bridge carries this horizon's actual labels, not 30-day outputs.
    bridged = _candidate_dataset(dataset, endpoint_before=CALIBRATION_FOLD.origin_end)
    sliced = slice_dataset_for_fold(bridged, CALIBRATION_FOLD,
                                    minimum_training_origins=PLAN.config.minimum_training_origins)
    if not sliced.training_eligible:
        raise ForecastFinalizationError("minimum label-complete training history is not met")
    if len(sliced.evaluation_rows) < CALIBRATION_MINIMUM_OBSERVATIONS:
        raise ForecastFinalizationError("calibration requires at least 60 usable residuals")
    result = calibrate_frozen_selection(dataset=bridged, plan=PLAN, selection=selection)
    if (result.symbol != selection.symbol or result.target_type is not selection.target_type
        or result.selected_candidate_id != selection.selected_candidate_id
        or result.fold_id != CALIBRATION_FOLD.fold_id
        or result.observation_count != len(sliced.evaluation_rows)
        or result.residual_q10 > result.residual_q90):
        raise ForecastFinalizationError("calibration result differs from its frozen inputs")
    payload = {
        **asdict(result), "horizon_days": frozen.horizon_days,
        "target_type": target_name(selection.target_type, frozen.horizon_days),
        "feature_set_version": FEATURE_SET_VERSION, "target_set_version": target_version(frozen.horizon_days),
        "selection_warning": selection.selection_warning,
        "training_observation_count": len(sliced.training_rows),
        "training_cutoff_exclusive": CALIBRATION_FOLD.origin_start.isoformat(),
        "training_origin_min": min(row.features.origin_date for row in sliced.training_rows).isoformat(),
        "training_origin_max": max(row.features.origin_date for row in sliced.training_rows).isoformat(),
        "training_endpoint_max": max(row.target.endpoint_date for row in sliced.training_rows).isoformat(),
        "evaluation_origin_start": CALIBRATION_FOLD.origin_start.isoformat(),
        "evaluation_origin_end_exclusive": CALIBRATION_FOLD.origin_end.isoformat(),
        "evaluated_origin_min": min(row.features.origin_date for row in sliced.evaluation_rows).isoformat(),
        "evaluated_origin_max": max(row.features.origin_date for row in sliced.evaluation_rows).isoformat(),
        "evaluated_endpoint_max": max(row.target.endpoint_date for row in sliced.evaluation_rows).isoformat(),
    }
    canonical_json_bytes(payload)  # Never serialize non-finite metrics or ranges.
    return payload


def calibrate_histories(
    histories: Sequence[AssetPriceHistory], *, manifest: FrozenHorizonManifest,
    progress: Callable[[str], None] | None = None,
) -> dict[str, object]:
    """Pure calibration orchestration; persisted provenance is checked by caller.

    A pure history collection has no canonical volume/source information and
    therefore emits unverified provenance until the database caller supplies it.
    """
    # Validate even callers supplying a hand-constructed dataclass.
    manifest = horizon_manifest_from_dict(json.loads(horizon_manifest_json(manifest)))
    ordered = tuple(sorted(histories, key=lambda history: history.symbol))
    symbols = tuple(history.symbol for history in ordered)
    if len(symbols) != len(USER_ASSET_SYMBOLS) or set(symbols) != set(USER_ASSET_SYMBOLS):
        raise ForecastFinalizationError("calibration requires all 17 unique assets")
    if any(row.date > OFFICIAL_EVALUATION_CUTOFF for history in ordered for row in history.observations):
        raise ForecastFinalizationError("history exceeds the frozen cutoff")
    # Verify the full snapshot in the CLI, then exclude final-test prices BEFORE
    # feature/label construction. No final-test label is fitted or scored here.
    truncated = {history.symbol: AssetPriceHistory(history.symbol, tuple(
        row for row in history.observations if row.date < CALIBRATION_FOLD.origin_end
    )) for history in ordered}
    features = {symbol: build_feature_rows(history) for symbol, history in truncated.items()}
    datasets = {}
    records = []
    for frozen in manifest.records:
        key = (frozen.horizon_days, frozen.selection.symbol)
        if key not in datasets:
            datasets[key] = build_horizon_dataset(truncated[key[1]], horizon_days=key[0], features=features[key[1]])
        if progress:
            progress(f"Calibrating {key[1]} {target_name(frozen.selection.target_type, key[0])}, frozen candidate only...")
        records.append(calibrate_horizon_selection(dataset=datasets[key], frozen=frozen))
    plan_payload = {**asdict(PLAN.config), "evaluation_end_exclusive": PLAN.config.evaluation_end_exclusive.isoformat()}
    return {
        "report_schema": REPORT_SCHEMA, "release_version": RELEASE_VERSION, "stage": STAGE,
        "evaluation_cutoff": OFFICIAL_EVALUATION_CUTOFF.isoformat(),
        "horizons": list(NEW_HORIZONS), "horizon_unit": "calendar_days", "record_count": len(records),
        "selection_manifest_sha256": manifest.manifest_sha256,
        "source_selection_report_sha256": manifest.source_selection_report_sha256,
        "approved_market_data_fingerprint_sha256": manifest.market_data_fingerprint_sha256,
        "approved_market_data_row_count": manifest.market_data_row_count,
        "data_provenance": {"provenance_verified": False, "evaluation_cutoff": OFFICIAL_EVALUATION_CUTOFF.isoformat(),
                            "symbol_count": None, "row_count": None, "market_data_fingerprint_sha256": None},
        "evaluation_plan": plan_payload,
        "calibration_fold": {"fold_id": CALIBRATION_FOLD.fold_id, "purpose": "calibration",
                             "origin_start": CALIBRATION_FOLD.origin_start.isoformat(),
                             "origin_end": CALIBRATION_FOLD.origin_end.isoformat()},
        "interval_method": {"method": "empirical_actual_minus_prediction_residual_quantiles",
                            "quantile_interpolation": "linear", "nominal_coverage": NOMINAL_INTERVAL_COVERAGE,
                            "lower_quantile": LOWER_RESIDUAL_QUANTILE, "upper_quantile": UPPER_RESIDUAL_QUANTILE,
                            "minimum_observations": CALIBRATION_MINIMUM_OBSERVATIONS},
        "final_test_completed": False, "deployment_artifacts_created": False, "records": records,
        "limitations": [
            "Calibration fits only frozen candidates, with no selection changes or fallback.",
            "Training labels end before calibration starts; scored labels end before final testing starts.",
            "Intervals are nominal empirical asset ranges, not guaranteed coverage or portfolio intervals.",
            "Horizon labels overlap; residual observations are not independent guarantees.",
            "Volatility is non-annualized; negative point predictions are clipped before residual calculation.",
            "Reusing the V1 snapshot is not a wholly new untouched project-level holdout.",
            "Final testing, deployment fitting, runtime support and client activation remain pending.",
        ],
    }


def calibration_report_json(report: dict[str, object]) -> str:
    """Bind all evidence fields to a canonical hash; prohibit non-finite JSON."""
    if "calibration_sha256" in report:
        raise ForecastFinalizationError("calibration checksum must be computed from unhashed evidence")
    digest = sha256_bytes(canonical_json_bytes(report))
    return json.dumps({**report, "calibration_sha256": digest}, indent=2, sort_keys=True, allow_nan=False) + "\n"
