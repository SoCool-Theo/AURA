"""Offline validation/freezing of weekly selections; never a V1 deployment.

The legacy freezer is reused privately per horizon for its established policy.
Public records always carry actual horizon names. Nothing here fits estimators,
queries a database, or changes the original frozen 30-day package.
"""

from __future__ import annotations

from dataclasses import asdict, dataclass, replace
from datetime import date, timedelta
import json
import re

from ..core.instruments import USER_ASSET_SYMBOLS
from .evaluation import ForecastTargetType
from .features import FEATURE_SET_VERSION
from .fingerprints import canonical_json_bytes, sha256_bytes
from .models import ARIMA_CANDIDATE_ID, ARIMA_FIT_CONVERGENCE_WARNING, VOLATILITY_ARIMA_CANDIDATE_ID
from .multi_horizon import NEW_HORIZONS, target_name, target_version
from .selection import (
    CANDIDATE_SIMPLICITY_ORDER, VOLATILITY_CANDIDATE_SIMPLICITY_ORDER,
    MINIMUM_COMPLEX_MODEL_IMPROVEMENT_PERCENT, PRACTICAL_TIE_PERCENT,
    summarize_symbol_selection, summarize_volatility_selection,
)
from .selection_manifest import (
    OFFICIAL_EVALUATION_CUTOFF, SELECTION_MANIFEST_SCHEMA_VERSION,
    FrozenSelectionRecord, _parse_result,
    freeze_selection_manifest, selection_manifest_from_dict,
)
from .splits import EvaluationPlanConfig, FoldPurpose, build_chronological_plan
from .targets import MAX_ENDPOINT_SLIPPAGE_DAYS


SCHEMA_VERSION = "forecast-horizon-selection-manifest-v1"
RELEASE_VERSION = "forecast-weekly-v1-20260917"
STAGE = "frozen_selection_not_deployable"
SELECTION_COUNT = len(USER_ASSET_SYMBOLS) * len(NEW_HORIZONS) * 2
_PLAN = EvaluationPlanConfig(OFFICIAL_EVALUATION_CUTOFF + timedelta(days=1))
_FOLDS = tuple(fold for fold in build_chronological_plan(_PLAN).folds if fold.purpose is FoldPurpose.SELECTION)


class HorizonSelectionError(ValueError):
    """Safe malformed/tampered selection evidence diagnostic."""


def validate_digest(value: object) -> str:
    if not isinstance(value, str) or re.fullmatch(r"[0-9a-fA-F]{64}", value) is None:
        raise HorizonSelectionError("expected a SHA-256 hex digest")
    return value.lower()


def _integer(value: object, *, minimum: int = 1) -> int:
    if type(value) is not int or value < minimum:
        raise HorizonSelectionError("evidence count must be a valid integer")
    return value


def _plan_payload() -> dict[str, object]:
    return {**asdict(_PLAN), "evaluation_end_exclusive": _PLAN.evaluation_end_exclusive.isoformat()}


def _fold_payloads() -> list[dict[str, object]]:
    return [{"fold_id": fold.fold_id, "purpose": fold.purpose.value,
             "origin_start": fold.origin_start.isoformat(), "origin_end": fold.origin_end.isoformat()}
            for fold in _FOLDS]


def _provenance(payload: object, expected_fingerprint: str, expected_row_count: int) -> None:
    if (not isinstance(payload, dict) or payload.get("provenance_verified") is not True
        or payload.get("evaluation_cutoff") != OFFICIAL_EVALUATION_CUTOFF.isoformat()
        or _integer(payload.get("symbol_count")) != len(USER_ASSET_SYMBOLS)
        or _integer(payload.get("row_count")) != expected_row_count
        or validate_digest(payload.get("market_data_fingerprint_sha256")) != expected_fingerprint):
        raise HorizonSelectionError("selection evidence does not match approved dataset provenance")


@dataclass(frozen=True, slots=True)
class FrozenHorizonSelection:
    horizon_days: int
    selection: FrozenSelectionRecord


@dataclass(frozen=True, slots=True)
class FrozenHorizonManifest:
    source_selection_report_sha256: str
    market_data_fingerprint_sha256: str
    market_data_row_count: int
    records: tuple[FrozenHorizonSelection, ...]
    manifest_sha256: str


def _record_payload(record: FrozenHorizonSelection) -> dict[str, object]:
    return {**asdict(record.selection),
            "target_type": target_name(record.selection.target_type, record.horizon_days),
            "horizon_days": record.horizon_days, "feature_set_version": FEATURE_SET_VERSION,
            "target_set_version": target_version(record.horizon_days),
            "evaluation_cutoff": record.selection.evaluation_cutoff.isoformat()}


def _manifest_base(source_hash: str, fingerprint: str, row_count: int,
                   records: tuple[FrozenHorizonSelection, ...]) -> dict[str, object]:
    return {
        "schema_version": SCHEMA_VERSION, "release_version": RELEASE_VERSION, "stage": STAGE,
        "evaluation_cutoff": OFFICIAL_EVALUATION_CUTOFF.isoformat(), "horizons": list(NEW_HORIZONS),
        "expected_symbol_count": len(USER_ASSET_SYMBOLS), "expected_target_count": 2,
        "selection_count": SELECTION_COUNT, "source_selection_report_sha256": source_hash,
        "data_provenance": {"provenance_verified": True,
                            "evaluation_cutoff": OFFICIAL_EVALUATION_CUTOFF.isoformat(),
                            "symbol_count": len(USER_ASSET_SYMBOLS), "row_count": row_count,
                            "market_data_fingerprint_sha256": fingerprint},
        "evaluation_plan": _plan_payload(), "selection_folds": _fold_payloads(),
        "selection_policy": {"minimum_complex_model_improvement_percent": MINIMUM_COMPLEX_MODEL_IMPROVEMENT_PERCENT,
                             "practical_tie_percent": PRACTICAL_TIE_PERCENT},
        "records": [_record_payload(record) for record in records],
    }


def _validate_group(group: dict[str, object], horizon: int, target: ForecastTargetType) -> None:
    """Validate real horizon identity/metadata before bridging legacy slots."""
    order = CANDIDATE_SIMPLICITY_ORDER if target is ForecastTargetType.RETURN else VOLATILITY_CANDIDATE_SIMPLICITY_ORDER
    if (group.get("feature_set_version") != FEATURE_SET_VERSION
        or group.get("target_set_version") != target_version(horizon)
        or group.get("candidate_ids") != list(order)):
        raise HorizonSelectionError("horizon group versions or candidates are invalid")
    price_count = _integer(group.get("price_observation_count"))
    feature_count = _integer(group.get("feature_origin_count"))
    target_count = _integer(group.get("target_origin_count"))
    complete_count = _integer(group.get("label_complete_origin_count"))
    if not (complete_count <= min(feature_count, target_count) and max(feature_count, target_count) <= price_count):
        raise HorizonSelectionError("horizon group dataset counts are inconsistent")
    items = group.get("results")
    if not isinstance(items, list) or len(items) != len(order) * len(_FOLDS):
        raise HorizonSelectionError("horizon group must contain 25 selection results")
    keys = set()
    parsed = []
    fold_counts = {}
    folds = {fold.fold_id: fold for fold in _FOLDS}
    for item in items:
        if not isinstance(item, dict):
            raise HorizonSelectionError("selection result must be an object")
        fold = folds.get(item.get("fold_id"))
        if (fold is None or item.get("candidate_id") not in order
            or item.get("symbol") != group["symbol"] or item.get("horizon_days") != horizon
            or type(item.get("horizon_days")) is not int
            or item.get("target_type") != target_name(target, horizon)
            or item.get("fold_purpose") != "selection" or item.get("prediction_available") is not True
            or item.get("training_cutoff") != fold.origin_start.isoformat()
            or item.get("evaluation_origin_start") != fold.origin_start.isoformat()
            or item.get("evaluation_origin_end") != fold.origin_end.isoformat()):
            raise HorizonSelectionError("selection result identity or fold boundary is invalid")
        key = (item["candidate_id"], item["fold_id"])
        if key in keys:
            raise HorizonSelectionError("duplicate selection candidate/fold result")
        keys.add(key)
        training = _integer(item.get("training_observation_count"), minimum=_PLAN.minimum_training_origins)
        candidate_training = _integer(item.get("candidate_training_value_count"))
        evaluated = _integer(item.get("evaluated_observation_count"))
        if candidate_training > training or training > complete_count or evaluated > complete_count:
            raise HorizonSelectionError("selection result observation counts are inconsistent")
        counts = (training, evaluated)
        if item["fold_id"] in fold_counts and fold_counts[item["fold_id"]] != counts:
            raise HorizonSelectionError("candidates did not use identical fold data")
        fold_counts[item["fold_id"]] = counts
        warning = item.get("warning")
        if warning is not None and (warning != ARIMA_FIT_CONVERGENCE_WARNING
            or item["candidate_id"] not in {ARIMA_CANDIDATE_ID, VOLATILITY_ARIMA_CANDIDATE_ID}):
            raise HorizonSelectionError("selection result warning is unsupported")
        result = _parse_result({**item, "target_type": target.value}, target_type=target)
        if result.mae < 0 or result.rmse < 0:
            raise HorizonSelectionError("selection error metrics cannot be negative")
        if target is ForecastTargetType.RETURN:
            if (result.directional_accuracy is None or not 0 <= result.directional_accuracy <= 1
                or _integer(item.get("directional_evaluated_count")) != evaluated
                or item.get("negative_prediction_clipped_count") is not None):
                raise HorizonSelectionError("return direction or clipping metadata is invalid")
        elif item.get("return_mape") is not None:
            raise HorizonSelectionError("volatility cannot contain return-only metrics")
        parsed.append(result)
    summarize = summarize_symbol_selection if target is ForecastTargetType.RETURN else summarize_volatility_selection
    generated = summarize(symbol=group["symbol"], results=tuple(parsed),
                          expected_selection_fold_ids=tuple(fold.fold_id for fold in _FOLDS))
    # Includes warnings and coverage flags, not just the reported winning ID.
    if canonical_json_bytes(asdict(generated)) != canonical_json_bytes(group.get("selection_summary")):
        raise HorizonSelectionError("reported selection summary or warnings differ from recomputed policy")


def freeze_horizon_manifest(
    *, report: object, source_report_sha256: str,
    expected_market_data_fingerprint: str, expected_row_count: int,
) -> FrozenHorizonManifest:
    """Freeze 102 choices from approved selection evidence, without fitting."""
    try:
        source_hash = validate_digest(source_report_sha256)
        fingerprint = validate_digest(expected_market_data_fingerprint)
        row_count = _integer(expected_row_count)
        canonical_json_bytes(report)  # Reject NaN/Infinity anywhere, including unused evidence.
        if (not isinstance(report, dict) or report.get("report_schema") != "forecast-horizon-selection-v1"
            or report.get("stage") != "selection_only_not_deployable"
            or report.get("evaluation_cutoff") != OFFICIAL_EVALUATION_CUTOFF.isoformat()
            or report.get("evaluation_end_exclusive") != _PLAN.evaluation_end_exclusive.isoformat()
            or canonical_json_bytes(report.get("horizons")) != canonical_json_bytes(list(NEW_HORIZONS))
            or report.get("horizon_unit") != "calendar_days"
            or canonical_json_bytes(report.get("evaluation_plan")) != canonical_json_bytes(_plan_payload())
            or report.get("selection_folds") != _fold_payloads()
            or canonical_json_bytes(report.get("selection_policy")) != canonical_json_bytes({
                "minimum_complex_model_improvement_percent": MINIMUM_COMPLEX_MODEL_IMPROVEMENT_PERCENT,
                "practical_tie_percent": PRACTICAL_TIE_PERCENT})
            or report.get("missing_symbols") != []):
            raise HorizonSelectionError("selection report stage, horizon or evaluation contract is invalid")
        _provenance(report.get("data_provenance"), fingerprint, row_count)
        for field in ("requested_symbols", "evaluated_symbols"):
            symbols = report.get(field)
            if not isinstance(symbols, list) or len(symbols) != len(USER_ASSET_SYMBOLS) or set(symbols) != set(USER_ASSET_SYMBOLS):
                raise HorizonSelectionError("selection report must contain all 17 assets exactly once")
        if canonical_json_bytes(report.get("target_definition")) != canonical_json_bytes({
            "return": "endpoint_price / origin_price - 1",
            "realized_volatility": "sqrt(sum(consecutive future log returns squared))",
            "annualized": False, "endpoint": "first stored observation on or after origin plus horizon",
            "maximum_endpoint_slippage_days": MAX_ENDPOINT_SLIPPAGE_DAYS,
        }):
            raise HorizonSelectionError("selection target definition differs from the approved workflow")
        groups = report.get("groups")
        if not isinstance(groups, list) or len(groups) != SELECTION_COUNT:
            raise HorizonSelectionError("selection report must contain 102 horizon/asset/target groups")
        by_key = {}
        for group in groups:
            if not isinstance(group, dict) or type(group.get("horizon_days")) is not int or group["horizon_days"] not in NEW_HORIZONS:
                raise HorizonSelectionError("horizon group is malformed")
            horizon = group["horizon_days"]
            key = (horizon, group.get("symbol"), group.get("target_type"))
            if key in by_key:
                raise HorizonSelectionError("duplicate horizon/asset/target group")
            by_key[key] = group
        expected_keys = {(horizon, symbol, target_name(target, horizon))
                         for horizon in NEW_HORIZONS for symbol in USER_ASSET_SYMBOLS for target in ForecastTargetType}
        if set(by_key) != expected_keys:
            raise HorizonSelectionError("selection report horizon/asset/target coverage is invalid")
        records = []
        for horizon in NEW_HORIZONS:
            reports = {}
            for target in ForecastTargetType:
                subset = [by_key[(horizon, symbol, target_name(target, horizon))] for symbol in sorted(USER_ASSET_SYMBOLS)]
                for group in subset:
                    _validate_group(group, horizon, target)
                reports[target] = {
                    "evaluation_cutoff": OFFICIAL_EVALUATION_CUTOFF.isoformat(),
                    "requested_symbols": list(USER_ASSET_SYMBOLS), "evaluated_symbols": sorted(USER_ASSET_SYMBOLS),
                    "missing_symbols": [], "selection_fold_ids": [fold.fold_id for fold in _FOLDS],
                    "candidate_ids": subset[0]["candidate_ids"],
                    "results": [{**item, "target_type": target.value} for group in subset for item in group["results"]],
                    "selection_summaries": [group["selection_summary"] for group in subset],
                }
            legacy = freeze_selection_manifest(
                return_report=reports[ForecastTargetType.RETURN], volatility_report=reports[ForecastTargetType.VOLATILITY],
                return_report_sha256=source_hash, volatility_report_sha256=source_hash,
            )
            for selection in legacy.records:
                group = by_key[(horizon, selection.symbol, target_name(selection.target_type, horizon))]
                # Return selection statistics do not aggregate available-fit warnings
                # in V1. Preserve selected raw warnings here for either target.
                warned = any(item.get("warning") for item in group["results"]
                             if item["candidate_id"] == selection.selected_candidate_id)
                if warned:
                    selection = replace(selection, selection_warning=ARIMA_FIT_CONVERGENCE_WARNING)
                records.append(FrozenHorizonSelection(horizon, selection))
        ordered = tuple(records)
        base = _manifest_base(source_hash, fingerprint, row_count, ordered)
        return FrozenHorizonManifest(source_hash, fingerprint, row_count, ordered, sha256_bytes(canonical_json_bytes(base)))
    except HorizonSelectionError:
        raise
    except (KeyError, TypeError, ValueError, OverflowError) as error:
        raise HorizonSelectionError("selection evidence is malformed or violates the established policy") from error


def horizon_manifest_json(manifest: FrozenHorizonManifest) -> str:
    base = _manifest_base(manifest.source_selection_report_sha256, manifest.market_data_fingerprint_sha256,
                          manifest.market_data_row_count, manifest.records)
    return json.dumps({**base, "manifest_sha256": manifest.manifest_sha256}, allow_nan=False, indent=2, sort_keys=True) + "\n"


def horizon_manifest_from_dict(payload: object) -> FrozenHorizonManifest:
    """Check full coverage, metadata, warning preservation, order and digest."""
    try:
        if not isinstance(payload, dict):
            raise HorizonSelectionError("horizon manifest must be an object")
        source_hash = validate_digest(payload.get("source_selection_report_sha256"))
        provenance = payload["data_provenance"]
        fingerprint = validate_digest(provenance["market_data_fingerprint_sha256"])
        row_count = _integer(provenance["row_count"])
        _provenance(provenance, fingerprint, row_count)
        raw_records = payload["records"]
        if not isinstance(raw_records, list) or len(raw_records) != SELECTION_COUNT:
            raise HorizonSelectionError("horizon manifest requires 102 records")
        records = []
        for horizon in NEW_HORIZONS:
            converted = []
            for item in raw_records:
                if not isinstance(item, dict) or type(item.get("horizon_days")) is not int or item["horizon_days"] not in NEW_HORIZONS:
                    raise HorizonSelectionError("manifest record horizon is invalid")
                if item["horizon_days"] != horizon:
                    continue
                target = next((target for target in ForecastTargetType if target_name(target, horizon) == item.get("target_type")), None)
                if (target is None or item.get("feature_set_version") != FEATURE_SET_VERSION
                    or item.get("target_set_version") != target_version(horizon)
                    or item.get("source_selection_report_sha256") != source_hash
                    or item.get("selection_warning") not in (None, ARIMA_FIT_CONVERGENCE_WARNING)
                    or (item.get("selection_warning") is not None
                        and item.get("selected_candidate_id") not in {ARIMA_CANDIDATE_ID, VOLATILITY_ARIMA_CANDIDATE_ID})):
                    raise HorizonSelectionError("manifest record identity or provenance is invalid")
                legacy_item = {key: value for key, value in item.items()
                               if key not in {"horizon_days", "feature_set_version", "target_set_version"}}
                legacy_item["target_type"] = target.value
                converted.append(legacy_item)
            base = {"schema_version": SELECTION_MANIFEST_SCHEMA_VERSION,
                    "evaluation_cutoff": OFFICIAL_EVALUATION_CUTOFF.isoformat(),
                    "expected_symbol_count": len(USER_ASSET_SYMBOLS), "expected_target_count": 2,
                    "selection_count": len(USER_ASSET_SYMBOLS) * 2, "records": converted}
            legacy = selection_manifest_from_dict({**base, "manifest_sha256": sha256_bytes(canonical_json_bytes(base))})
            if any(record.best_baseline_mean_selection_mae < 0 or record.selected_candidate_mean_selection_mae < 0
                   for record in legacy.records):
                raise HorizonSelectionError("manifest error metrics cannot be negative")
            records.extend(FrozenHorizonSelection(horizon, selection) for selection in legacy.records)
        ordered = tuple(records)
        expected = _manifest_base(source_hash, fingerprint, row_count, ordered)
        digest = validate_digest(payload.get("manifest_sha256"))
        if set(payload) != set(expected) | {"manifest_sha256"} or canonical_json_bytes({key: value for key, value in payload.items() if key != "manifest_sha256"}) != canonical_json_bytes(expected):
            raise HorizonSelectionError("horizon manifest metadata, records or order is invalid")
        if sha256_bytes(canonical_json_bytes(expected)) != digest:
            raise HorizonSelectionError("horizon manifest checksum mismatch")
        return FrozenHorizonManifest(source_hash, fingerprint, row_count, ordered, digest)
    except HorizonSelectionError:
        raise
    except (KeyError, TypeError, ValueError, StopIteration) as error:
        raise HorizonSelectionError("horizon manifest is malformed") from error
