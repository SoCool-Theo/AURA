"""Validation and deterministic freezing of Phase 4/5 selection evidence."""

from __future__ import annotations

from dataclasses import asdict, dataclass
from datetime import date
import json
import math
from numbers import Real

from ..core.instruments import USER_ASSET_SYMBOLS
from .evaluation import ForecastEvaluationResult, ForecastTargetType
from .fingerprints import canonical_json_bytes, sha256_bytes
from .selection import (
    BASELINE_CANDIDATE_IDS,
    CANDIDATE_SIMPLICITY_ORDER,
    VOLATILITY_CANDIDATE_SIMPLICITY_ORDER,
    SymbolSelectionSummary,
    summarize_symbol_selection,
    summarize_volatility_selection,
)
from .splits import FoldPurpose


SELECTION_MANIFEST_SCHEMA_VERSION = "forecast-selection-manifest-v1"
OFFICIAL_EVALUATION_CUTOFF = date(2026, 9, 17)
EXPECTED_SELECTION_FOLD_IDS = tuple(
    f"selection-{index:02d}" for index in range(1, 6)
)
EXPECTED_SELECTION_RECORD_COUNT = len(USER_ASSET_SYMBOLS) * 2


class SelectionManifestError(ValueError):
    """Raised when experiment evidence cannot be frozen safely."""


@dataclass(frozen=True, slots=True)
class FrozenSelectionRecord:
    symbol: str
    target_type: ForecastTargetType
    selected_candidate_id: str
    selected_candidate_kind: str
    best_baseline_id: str
    best_baseline_mean_selection_mae: float
    selected_candidate_mean_selection_mae: float
    improvement_vs_best_baseline_percent: float | None
    practical_tie_with_best_baseline: bool
    selection_warning: str | None
    source_selection_report_sha256: str
    evaluation_cutoff: date


@dataclass(frozen=True, slots=True)
class FrozenSelectionManifest:
    schema_version: str
    evaluation_cutoff: date
    expected_symbol_count: int
    expected_target_count: int
    selection_count: int
    records: tuple[FrozenSelectionRecord, ...]
    manifest_sha256: str


def _finite_metric(value: object, *, name: str) -> float:
    if (
        isinstance(value, bool)
        or not isinstance(value, Real)
        or not math.isfinite(float(value))
    ):
        raise SelectionManifestError(f"{name} must be finite")
    return float(value)


def _optional_finite_metric(value: object, *, name: str) -> float | None:
    if value is None:
        return None
    return _finite_metric(value, name=name)


def _parse_result(
    payload: object,
    *,
    target_type: ForecastTargetType,
) -> ForecastEvaluationResult:
    if not isinstance(payload, dict):
        raise SelectionManifestError("selection result must be an object")
    try:
        parsed_target = ForecastTargetType(payload["target_type"])
        result = ForecastEvaluationResult(
            symbol=payload["symbol"],
            target_type=parsed_target,
            candidate_id=payload["candidate_id"],
            fold_id=payload["fold_id"],
            fold_purpose=FoldPurpose(payload["fold_purpose"]),
            training_cutoff=date.fromisoformat(payload["training_cutoff"]),
            evaluation_origin_start=date.fromisoformat(
                payload["evaluation_origin_start"]
            ),
            evaluation_origin_end=date.fromisoformat(
                payload["evaluation_origin_end"]
            ),
            training_observation_count=payload["training_observation_count"],
            candidate_training_value_count=payload[
                "candidate_training_value_count"
            ],
            evaluated_observation_count=payload[
                "evaluated_observation_count"
            ],
            prediction_available=payload["prediction_available"],
            mae=(
                None
                if payload["mae"] is None
                else _finite_metric(payload["mae"], name="result MAE")
            ),
            rmse=(
                None
                if payload["rmse"] is None
                else _finite_metric(payload["rmse"], name="result RMSE")
            ),
            directional_accuracy=(
                None
                if payload.get("directional_accuracy") is None
                else _finite_metric(
                    payload["directional_accuracy"],
                    name="directional accuracy",
                )
            ),
            directional_evaluated_count=payload.get(
                "directional_evaluated_count"
            ),
            return_mape=None,
            warning=payload.get("warning"),
            negative_prediction_clipped_count=(
                payload.get("negative_prediction_clipped_count", 0)
                if parsed_target is ForecastTargetType.VOLATILITY
                else None
            ),
        )
    except SelectionManifestError:
        raise
    except (KeyError, TypeError, ValueError) as error:
        raise SelectionManifestError("selection result is malformed") from error
    if result.target_type is not target_type:
        raise SelectionManifestError("selection report target type mismatch")
    if not result.prediction_available or result.mae is None or result.rmse is None:
        raise SelectionManifestError(
            "all selection-fold candidate results must be available"
        )
    return result


def _validate_report(
    payload: object,
    *,
    target_type: ForecastTargetType,
) -> tuple[tuple[ForecastEvaluationResult, ...], dict[str, dict[str, object]]]:
    if not isinstance(payload, dict):
        raise SelectionManifestError("selection report must be an object")
    candidate_order = (
        CANDIDATE_SIMPLICITY_ORDER
        if target_type is ForecastTargetType.RETURN
        else VOLATILITY_CANDIDATE_SIMPLICITY_ORDER
    )
    try:
        cutoff = date.fromisoformat(payload["evaluation_cutoff"])
        requested_symbols = tuple(payload["requested_symbols"])
        evaluated_symbols = tuple(payload["evaluated_symbols"])
        missing_symbols = tuple(payload["missing_symbols"])
        fold_ids = tuple(payload["selection_fold_ids"])
        candidate_ids = tuple(payload["candidate_ids"])
        result_payloads = tuple(payload["results"])
        summary_payloads = tuple(payload["selection_summaries"])
    except (KeyError, TypeError, ValueError) as error:
        raise SelectionManifestError("selection report is malformed") from error
    expected_symbols = tuple(USER_ASSET_SYMBOLS)
    if cutoff != OFFICIAL_EVALUATION_CUTOFF:
        raise SelectionManifestError("selection report cutoff is not official")
    if (
        len(requested_symbols) != len(expected_symbols)
        or set(requested_symbols) != set(expected_symbols)
        or len(evaluated_symbols) != len(expected_symbols)
        or set(evaluated_symbols) != set(expected_symbols)
        or missing_symbols
    ):
        raise SelectionManifestError(
            "selection report must contain all 17 Aura symbols"
        )
    if fold_ids != EXPECTED_SELECTION_FOLD_IDS:
        raise SelectionManifestError(
            "selection report must contain exactly five selection folds"
        )
    if candidate_ids != candidate_order:
        raise SelectionManifestError("selection report candidate IDs are invalid")
    expected_result_count = (
        len(expected_symbols) * len(fold_ids) * len(candidate_order)
    )
    if len(result_payloads) != expected_result_count:
        raise SelectionManifestError("selection report result count is invalid")

    results = tuple(
        _parse_result(item, target_type=target_type) for item in result_payloads
    )
    result_keys = tuple(
        (result.symbol, result.candidate_id, result.fold_id)
        for result in results
    )
    if len(set(result_keys)) != len(result_keys):
        raise SelectionManifestError("selection report contains duplicate results")
    if any(
        result.fold_purpose is not FoldPurpose.SELECTION
        or result.fold_id not in EXPECTED_SELECTION_FOLD_IDS
        or result.symbol not in expected_symbols
        or result.candidate_id not in candidate_order
        for result in results
    ):
        raise SelectionManifestError(
            "selection report contains unexpected result provenance"
        )

    summaries: dict[str, dict[str, object]] = {}
    for summary in summary_payloads:
        if not isinstance(summary, dict) or not isinstance(
            summary.get("symbol"), str
        ):
            raise SelectionManifestError("selection summary is malformed")
        symbol = summary["symbol"]
        if symbol in summaries:
            raise SelectionManifestError("selection report has duplicate summary")
        summaries[symbol] = summary
    if set(summaries) != set(expected_symbols):
        raise SelectionManifestError(
            "selection report must have one summary per symbol"
        )

    for symbol in expected_symbols:
        symbol_results = tuple(
            result for result in results if result.symbol == symbol
        )
        generated: SymbolSelectionSummary = (
            summarize_symbol_selection(
                symbol=symbol,
                results=symbol_results,
                expected_selection_fold_ids=EXPECTED_SELECTION_FOLD_IDS,
            )
            if target_type is ForecastTargetType.RETURN
            else summarize_volatility_selection(
                symbol=symbol,
                results=symbol_results,
                expected_selection_fold_ids=EXPECTED_SELECTION_FOLD_IDS,
            )
        )
        reported = summaries[symbol]
        if (
            reported.get("leading_selection_candidate_id")
            != generated.leading_selection_candidate_id
            or reported.get("best_baseline_id") != generated.best_baseline_id
            or reported.get("baseline_remains_leading")
            != generated.baseline_remains_leading
        ):
            raise SelectionManifestError(
                "selection report summary violates the frozen policy"
            )
        reported_baseline_mae = _finite_metric(
            reported.get("best_baseline_mean_selection_mae"),
            name="best baseline mean selection MAE",
        )
        generated_baseline_mae = generated.best_baseline_mean_selection_mae
        if generated_baseline_mae is None or not math.isclose(
            reported_baseline_mae,
            generated_baseline_mae,
            rel_tol=1e-12,
            abs_tol=1e-15,
        ):
            raise SelectionManifestError(
                "selection report baseline MAE is inconsistent"
            )
        reported_stats = reported.get("candidate_statistics")
        if not isinstance(reported_stats, (list, tuple)) or tuple(
            item.get("candidate_id") for item in reported_stats
        ) != candidate_order:
            raise SelectionManifestError(
                "selection report candidate statistics are invalid"
            )
        generated_stats = {
            item.candidate_id: item for item in generated.candidate_statistics
        }
        for item in reported_stats:
            candidate_id = item["candidate_id"]
            generated_item = generated_stats[candidate_id]
            reported_mean = _finite_metric(
                item.get("mean_selection_mae"),
                name="candidate mean selection MAE",
            )
            generated_mean = generated_item.mean_selection_mae
            if generated_mean is None or not math.isclose(
                reported_mean,
                generated_mean,
                rel_tol=1e-12,
                abs_tol=1e-15,
            ):
                raise SelectionManifestError(
                    "selection report candidate MAE is inconsistent"
                )
            reported_improvement = _optional_finite_metric(
                item.get("improvement_vs_best_baseline_percent"),
                name="candidate improvement",
            )
            generated_improvement = (
                generated_item.improvement_vs_best_baseline_percent
            )
            if (
                reported_improvement is None
                and generated_improvement is not None
            ) or (
                reported_improvement is not None
                and (
                    generated_improvement is None
                    or not math.isclose(
                        reported_improvement,
                        generated_improvement,
                        rel_tol=1e-12,
                        abs_tol=1e-12,
                    )
                )
            ):
                raise SelectionManifestError(
                    "selection report improvement is inconsistent"
                )
            if (
                item.get("clears_minimum_improvement")
                != generated_item.clears_minimum_improvement
                or item.get("practical_tie_with_best_baseline")
                != generated_item.practical_tie_with_best_baseline
                or item.get("available_fold_count") != 5
                or item.get("required_fold_count") != 5
            ):
                raise SelectionManifestError(
                    "selection report policy flags are inconsistent"
                )
    return results, summaries


def _record_payload(record: FrozenSelectionRecord) -> dict[str, object]:
    payload = asdict(record)
    payload["target_type"] = record.target_type.value
    payload["evaluation_cutoff"] = record.evaluation_cutoff.isoformat()
    return payload


def freeze_selection_manifest(
    *,
    return_report: object,
    volatility_report: object,
    return_report_sha256: str,
    volatility_report_sha256: str,
) -> FrozenSelectionManifest:
    """Freeze 34 report-selected candidates without calibration/test input."""
    if len(return_report_sha256) != 64 or len(volatility_report_sha256) != 64:
        raise SelectionManifestError("selection report SHA-256 is invalid")
    _, return_summaries = _validate_report(
        return_report,
        target_type=ForecastTargetType.RETURN,
    )
    _, volatility_summaries = _validate_report(
        volatility_report,
        target_type=ForecastTargetType.VOLATILITY,
    )
    records: list[FrozenSelectionRecord] = []
    for symbol in sorted(USER_ASSET_SYMBOLS):
        for target_type, summaries, report_hash in (
            (
                ForecastTargetType.RETURN,
                return_summaries,
                return_report_sha256,
            ),
            (
                ForecastTargetType.VOLATILITY,
                volatility_summaries,
                volatility_report_sha256,
            ),
        ):
            summary = summaries[symbol]
            selected_id = summary.get("leading_selection_candidate_id")
            best_baseline_id = summary.get("best_baseline_id")
            if not isinstance(selected_id, str) or not isinstance(
                best_baseline_id, str
            ):
                raise SelectionManifestError(
                    "selection summary must identify one leading candidate"
                )
            selected_stats = tuple(
                item
                for item in summary["candidate_statistics"]
                if item["candidate_id"] == selected_id
            )
            if len(selected_stats) != 1:
                raise SelectionManifestError(
                    "selection summary must identify selected statistics"
                )
            selected = selected_stats[0]
            warning_parts = tuple(
                dict.fromkeys(
                    part
                    for part in (summary.get("warning"), selected.get("warning"))
                    if part
                )
            )
            records.append(
                FrozenSelectionRecord(
                    symbol=symbol,
                    target_type=target_type,
                    selected_candidate_id=selected_id,
                    selected_candidate_kind=(
                        "baseline"
                        if selected_id in BASELINE_CANDIDATE_IDS
                        else "complex"
                    ),
                    best_baseline_id=best_baseline_id,
                    best_baseline_mean_selection_mae=_finite_metric(
                        summary["best_baseline_mean_selection_mae"],
                        name="best baseline mean selection MAE",
                    ),
                    selected_candidate_mean_selection_mae=_finite_metric(
                        selected["mean_selection_mae"],
                        name="selected candidate mean selection MAE",
                    ),
                    improvement_vs_best_baseline_percent=(
                        _optional_finite_metric(
                            selected.get(
                                "improvement_vs_best_baseline_percent"
                            ),
                            name="selected improvement",
                        )
                    ),
                    practical_tie_with_best_baseline=bool(
                        selected["practical_tie_with_best_baseline"]
                    ),
                    selection_warning=(
                        None if not warning_parts else "; ".join(warning_parts)
                    ),
                    source_selection_report_sha256=report_hash,
                    evaluation_cutoff=OFFICIAL_EVALUATION_CUTOFF,
                )
            )
    ordered = tuple(
        sorted(records, key=lambda item: (item.symbol, item.target_type.value))
    )
    if len(ordered) != EXPECTED_SELECTION_RECORD_COUNT or len(
        {(item.symbol, item.target_type) for item in ordered}
    ) != EXPECTED_SELECTION_RECORD_COUNT:
        raise SelectionManifestError(
            "selection manifest must contain exactly 34 unique records"
        )
    base = {
        "schema_version": SELECTION_MANIFEST_SCHEMA_VERSION,
        "evaluation_cutoff": OFFICIAL_EVALUATION_CUTOFF.isoformat(),
        "expected_symbol_count": len(USER_ASSET_SYMBOLS),
        "expected_target_count": 2,
        "selection_count": len(ordered),
        "records": [_record_payload(record) for record in ordered],
    }
    return FrozenSelectionManifest(
        schema_version=SELECTION_MANIFEST_SCHEMA_VERSION,
        evaluation_cutoff=OFFICIAL_EVALUATION_CUTOFF,
        expected_symbol_count=len(USER_ASSET_SYMBOLS),
        expected_target_count=2,
        selection_count=len(ordered),
        records=ordered,
        manifest_sha256=sha256_bytes(canonical_json_bytes(base)),
    )


def selection_manifest_json(manifest: FrozenSelectionManifest) -> str:
    payload = {
        "schema_version": manifest.schema_version,
        "evaluation_cutoff": manifest.evaluation_cutoff.isoformat(),
        "expected_symbol_count": manifest.expected_symbol_count,
        "expected_target_count": manifest.expected_target_count,
        "selection_count": manifest.selection_count,
        "records": [_record_payload(record) for record in manifest.records],
        "manifest_sha256": manifest.manifest_sha256,
    }
    return json.dumps(payload, allow_nan=False, indent=2, sort_keys=True) + "\n"


def selection_manifest_from_dict(payload: object) -> FrozenSelectionManifest:
    if not isinstance(payload, dict):
        raise SelectionManifestError("selection manifest must be an object")
    try:
        records = tuple(
            FrozenSelectionRecord(
                symbol=item["symbol"],
                target_type=ForecastTargetType(item["target_type"]),
                selected_candidate_id=item["selected_candidate_id"],
                selected_candidate_kind=item["selected_candidate_kind"],
                best_baseline_id=item["best_baseline_id"],
                best_baseline_mean_selection_mae=_finite_metric(
                    item["best_baseline_mean_selection_mae"],
                    name="best baseline mean selection MAE",
                ),
                selected_candidate_mean_selection_mae=_finite_metric(
                    item["selected_candidate_mean_selection_mae"],
                    name="selected candidate mean selection MAE",
                ),
                improvement_vs_best_baseline_percent=_optional_finite_metric(
                    item["improvement_vs_best_baseline_percent"],
                    name="selected improvement",
                ),
                practical_tie_with_best_baseline=item[
                    "practical_tie_with_best_baseline"
                ],
                selection_warning=item["selection_warning"],
                source_selection_report_sha256=item[
                    "source_selection_report_sha256"
                ],
                evaluation_cutoff=date.fromisoformat(item["evaluation_cutoff"]),
            )
            for item in payload["records"]
        )
        manifest = FrozenSelectionManifest(
            schema_version=payload["schema_version"],
            evaluation_cutoff=date.fromisoformat(payload["evaluation_cutoff"]),
            expected_symbol_count=payload["expected_symbol_count"],
            expected_target_count=payload["expected_target_count"],
            selection_count=payload["selection_count"],
            records=records,
            manifest_sha256=payload["manifest_sha256"],
        )
    except (KeyError, TypeError, ValueError) as error:
        raise SelectionManifestError("selection manifest is malformed") from error
    if (
        manifest.schema_version != SELECTION_MANIFEST_SCHEMA_VERSION
        or manifest.evaluation_cutoff != OFFICIAL_EVALUATION_CUTOFF
        or manifest.expected_symbol_count != len(USER_ASSET_SYMBOLS)
        or manifest.expected_target_count != 2
        or manifest.selection_count != EXPECTED_SELECTION_RECORD_COUNT
        or len(records) != EXPECTED_SELECTION_RECORD_COUNT
        or len({(item.symbol, item.target_type) for item in records})
        != EXPECTED_SELECTION_RECORD_COUNT
    ):
        raise SelectionManifestError("selection manifest contract is invalid")
    expected_keys = {
        (symbol, target_type)
        for symbol in USER_ASSET_SYMBOLS
        for target_type in ForecastTargetType
    }
    if {(item.symbol, item.target_type) for item in records} != expected_keys:
        raise SelectionManifestError("selection manifest symbol targets are invalid")
    for record in records:
        candidate_order = (
            CANDIDATE_SIMPLICITY_ORDER
            if record.target_type is ForecastTargetType.RETURN
            else VOLATILITY_CANDIDATE_SIMPLICITY_ORDER
        )
        expected_kind = (
            "baseline"
            if record.selected_candidate_id in BASELINE_CANDIDATE_IDS
            else "complex"
        )
        if (
            record.evaluation_cutoff != OFFICIAL_EVALUATION_CUTOFF
            or record.selected_candidate_id not in candidate_order
            or record.selected_candidate_kind != expected_kind
            or record.best_baseline_id not in BASELINE_CANDIDATE_IDS
            or type(record.practical_tie_with_best_baseline) is not bool
            or len(record.source_selection_report_sha256) != 64
        ):
            raise SelectionManifestError("selection manifest record is invalid")
    ordered = tuple(
        sorted(records, key=lambda item: (item.symbol, item.target_type.value))
    )
    if records != ordered:
        raise SelectionManifestError("selection manifest order is invalid")
    base = {
        "schema_version": manifest.schema_version,
        "evaluation_cutoff": manifest.evaluation_cutoff.isoformat(),
        "expected_symbol_count": manifest.expected_symbol_count,
        "expected_target_count": manifest.expected_target_count,
        "selection_count": manifest.selection_count,
        "records": [_record_payload(record) for record in records],
    }
    if sha256_bytes(canonical_json_bytes(base)) != manifest.manifest_sha256:
        raise SelectionManifestError("selection manifest hash mismatch")
    return manifest
