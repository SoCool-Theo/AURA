"""Read-only loading of the reviewed experimental weekly deployment bundle."""

from dataclasses import dataclass
from datetime import date
from io import BytesIO
import json
from pathlib import Path
from threading import RLock

import joblib

from ..core.instruments import USER_ASSET_SYMBOLS
from .evaluation import ForecastTargetType
from .features import FEATURE_NAMES, FEATURE_SET_VERSION
from .finalization import ForecastArtifactModel, _model_family_and_parameters
from .fingerprints import canonical_json_bytes, sha256_bytes
from .horizon_artifacts import MODEL_SCHEMA, ROOT_SCHEMA, QUALITY_STATUS, WeeklyArtifactModel
from .inference_errors import ForecastArtifactInvalidError, ForecastInferenceError, ForecastSymbolUnsupportedError
from .registry import _finite, _read_bytes
from .selection import CANDIDATE_SIMPLICITY_ORDER, VOLATILITY_CANDIDATE_SIMPLICITY_ORDER


WEEKLY_VERSION = "forecast-weekly-v1-20260917"
WEEKLY_HORIZONS = (7, 14, 21)
# External approval pin, not a digest trusted merely because it is in the bundle.
REVIEWED_MANIFEST_SHA256 = "5b604af0c7e965cfcebdc0ae38a9570b64464ffc2c8d8adee230a19b2aaf95fe"
WARNING_CODES = (
    "arima_fit_convergence_warning", "empty_volatility_intervals_counted_as_misses",
    "final_interval_coverage_below_nominal",
)


def validate_weekly_horizon(horizon_days: int) -> None:
    if type(horizon_days) is not int or horizon_days not in WEEKLY_HORIZONS:
        raise ForecastArtifactInvalidError("weekly horizon must be 7, 14 or 21 calendar days")


def weekly_target_name(target: ForecastTargetType, horizon: int) -> str:
    if target is ForecastTargetType.RETURN:
        return f"return_{horizon}d"
    if target is ForecastTargetType.VOLATILITY:
        return f"realized_volatility_{horizon}d"
    raise ForecastArtifactInvalidError("unsupported weekly forecast target")


def _strict_json(payload: bytes) -> dict:
    def pairs(items):
        result = {}
        for key, value in items:
            if key in result:
                raise ValueError("duplicate key")
            result[key] = value
        return result

    def invalid_constant(value):
        raise ValueError("non-finite JSON")

    try:
        result = json.loads(payload, object_pairs_hook=pairs, parse_constant=invalid_constant)
        if not isinstance(result, dict):
            raise ValueError()
        # Also rejects overflow such as a JSON number written as 1e999.
        canonical_json_bytes(result)
        return result
    except (ValueError, UnicodeError, OverflowError, RecursionError):
        raise ForecastArtifactInvalidError("invalid weekly artifact JSON") from None


@dataclass(frozen=True, slots=True)
class LoadedWeeklyArtifact:
    model: ForecastArtifactModel
    evaluation_cutoff: date
    residual_q10: float
    residual_q90: float
    warning_codes: tuple[str, ...]


class WeeklyArtifactRegistry:
    """Verify all 102 pairs and evidence before any pickle deserialization.

    Storage is trusted local deployment input, not an upload endpoint. The
    approval pin is code-owned; constructor overrides are for explicit trusted
    test/deployment wiring only and are never read from requests or bundle data.
    Packages must remain immutable for this registry's lifetime.
    """

    artifact_version = WEEKLY_VERSION

    def __init__(self, *, artifact_root: Path | None = None,
                 expected_manifest_sha256: str = REVIEWED_MANIFEST_SHA256):
        self._root = (artifact_root if artifact_root is not None else
                      Path(__file__).resolve().parents[2] / "artifacts" / "forecasting" / WEEKLY_VERSION)
        self._expected_digest = expected_manifest_sha256
        self._records = None
        self._metadata = {}
        self._models = {}
        self._lock = RLock()

    def _checked_bytes(self, relative: str, digest: str) -> bytes:
        path = self._root / relative
        if not path.resolve().is_relative_to(self._root.resolve()):
            raise ForecastArtifactInvalidError("weekly artifact path escapes deployment root")
        content = _read_bytes(path)
        if sha256_bytes(content) != digest:
            raise ForecastArtifactInvalidError("weekly artifact checksum mismatch")
        return content

    def _validate(self):
        manifest = _strict_json(_read_bytes(self._root / "manifest.json"))
        base = {key: value for key, value in manifest.items() if key != "manifest_sha256"}
        if (manifest.get("manifest_sha256") != self._expected_digest
                or sha256_bytes(canonical_json_bytes(base)) != self._expected_digest):
            raise ForecastArtifactInvalidError("weekly bundle differs from reviewed deployment")
        required = {
            "artifact_schema_version": ROOT_SCHEMA, "artifact_version": WEEKLY_VERSION,
            "expected_symbol_count": 17, "expected_target_count": 2,
            "expected_artifact_count": 102, "generated_artifact_count": 102,
            "horizons": list(WEEKLY_HORIZONS), "horizon_unit": "calendar_days",
            "feature_version": FEATURE_SET_VERSION, "training_completed": True,
            "final_test_completed": True, "experimental_quality_acknowledged": True,
            "quality_status": QUALITY_STATUS, "predictive_quality_approved": False,
            # Frozen build evidence is not rewritten to activate a runtime.
            "runtime_activated": False, "evaluation_cutoff": "2026-09-17",
        }
        if canonical_json_bytes({key: manifest.get(key) for key in required}) != canonical_json_bytes(required):
            raise ForecastArtifactInvalidError("weekly root manifest contract mismatch")
        try:
            evidence = manifest["evidence_file_sha256"]
            if set(evidence) != {"selection_manifest.json", "calibration_report.json",
                                 "final_test_report.json", "source_selection_report.json", "training_started.json"}:
                raise ValueError()
            for name, digest in evidence.items():
                _strict_json(self._checked_bytes(name, digest))
            entries = manifest["generated_artifacts"]
            if not isinstance(entries, list) or len(entries) != 102:
                raise ValueError()
            records, metadata = {}, {}
            for entry in entries:
                symbol, horizon = entry["symbol"], entry["horizon_days"]
                validate_weekly_horizon(horizon)
                target = next((kind for kind in ForecastTargetType
                               if weekly_target_name(kind, horizon) == entry["target_type"]), None)
                candidates = (CANDIDATE_SIMPLICITY_ORDER if target is ForecastTargetType.RETURN
                              else VOLATILITY_CANDIDATE_SIMPLICITY_ORDER)
                key = (symbol, horizon, target)
                if (symbol not in USER_ASSET_SYMBOLS or target is None or key in records
                        or entry["selected_candidate_id"] not in candidates):
                    raise ValueError()
                for kind, filename in (("model", "model.joblib"), ("metadata", "metadata.json")):
                    relative = f"{horizon}d/{symbol}/{entry['target_type']}/{filename}"
                    if entry[f"{kind}_path"] != relative:
                        raise ValueError()
                    content = self._checked_bytes(relative, entry[f"{kind}_sha256"])
                    if kind == "metadata":
                        meta = _strict_json(content)
                self._validate_metadata(meta, entry, target, manifest)
                records[key], metadata[key] = entry, meta
            expected = {(symbol, horizon, target) for symbol in USER_ASSET_SYMBOLS
                        for horizon in WEEKLY_HORIZONS for target in ForecastTargetType}
            if set(records) != expected:
                raise ValueError()
        except ForecastInferenceError:
            raise
        except (KeyError, TypeError, ValueError, StopIteration):
            raise ForecastArtifactInvalidError("invalid weekly artifact records") from None
        self._records, self._metadata = records, metadata

    @staticmethod
    def _validate_metadata(meta, entry, target, manifest):
        horizon = entry["horizon_days"]
        required = {
            "artifact_schema_version": MODEL_SCHEMA, "artifact_version": WEEKLY_VERSION,
            "symbol": entry["symbol"], "horizon_days": horizon, "horizon_unit": "calendar_days",
            "target_type": entry["target_type"], "selected_candidate_id": entry["selected_candidate_id"],
            "feature_version": FEATURE_SET_VERSION, "feature_names": list(FEATURE_NAMES),
            "target_version": f"forecast-targets-{horizon}d-v1",
            "horizon_definition": {"calendar_days": horizon, "maximum_endpoint_slippage_days": 4},
            "artifact_file_sha256": entry["model_sha256"], "nominal_interval_coverage": .8,
            "warning_codes": entry["warning_codes"], "deployment_fit_warning": entry["deployment_fit_warning"],
            "volatility_prediction_rule": "max(raw_prediction, 0.0)" if target is ForecastTargetType.VOLATILITY else None,
        }
        for field in ("evaluation_cutoff", "selection_manifest_sha256", "calibration_sha256",
                      "final_test_sha256", "final_test_run_state_sha256", "training_data_fingerprint_sha256",
                      "training_data_row_count", "quality_status", "experimental_quality_acknowledged",
                      "predictive_quality_approved", "runtime_activated"):
            required[field] = manifest[field]
        family, parameters = _model_family_and_parameters(entry["selected_candidate_id"])
        required.update(model_family=family, model_parameters=parameters)
        if canonical_json_bytes({key: meta.get(key) for key in required}) != canonical_json_bytes(required):
            raise ValueError()
        q10, q90 = meta["calibration_residual_q10"], meta["calibration_residual_q90"]
        calibration, final = meta["calibration_evidence"], meta["final_test_evidence"]
        if (not _finite(q10) or not _finite(q90) or q10 > q90
                or type(calibration["observation_count"]) is not int or calibration["observation_count"] < 60
                or calibration["residual_q10"] != q10 or calibration["residual_q90"] != q90
                or final["frozen_residual_q10"] != q10 or final["frozen_residual_q90"] != q90):
            raise ValueError()
        for record in (meta["selection_evidence"], calibration, final):
            if (record["symbol"] != entry["symbol"] or record["target_type"] != entry["target_type"]
                    or record["selected_candidate_id"] != entry["selected_candidate_id"]):
                raise ValueError()
        if any(type(record["horizon_days"]) is not int or record["horizon_days"] != horizon
               for record in (calibration, final)):
            raise ValueError()
        warnings = meta["warning_codes"]
        if (not isinstance(warnings, list) or len(warnings) != len(set(warnings))
                or any(code not in WARNING_CODES for code in warnings)):
            raise ValueError()
        coverage = final["interval_coverage"]["empirical_coverage"]
        if (not _finite(coverage) or not 0 <= coverage <= 1
                or (coverage < .8) != ("final_interval_coverage_below_nominal" in warnings)):
            raise ValueError()

    def get(self, symbol: str, target: ForecastTargetType, horizon_days: int) -> LoadedWeeklyArtifact:
        validate_weekly_horizon(horizon_days)
        if symbol not in USER_ASSET_SYMBOLS:
            raise ForecastSymbolUnsupportedError("unsupported forecast symbol")
        if not isinstance(target, ForecastTargetType):
            raise ForecastArtifactInvalidError("unsupported weekly forecast target")
        key = (symbol, horizon_days, target)
        with self._lock:
            if self._records is None:
                self._validate()
            if key not in self._models:
                record, meta = self._records[key], self._metadata[key]
                content = self._checked_bytes(record["model_path"], record["model_sha256"])
                self._checked_bytes(record["metadata_path"], record["metadata_sha256"])
                try:
                    wrapper = joblib.load(BytesIO(content))
                    if not isinstance(wrapper, WeeklyArtifactModel):
                        raise ValueError()
                    wrapper.__post_init__()
                    model = wrapper._model
                    if (wrapper.symbol != symbol or wrapper.horizon_days != horizon_days
                            or wrapper.target_type != record["target_type"]
                            or wrapper.candidate_id != record["selected_candidate_id"]
                            or model.target_type is not target or model.model_family != meta["model_family"]):
                        raise ValueError()
                    if model.model_family in {"historical_average", "moving_average"}:
                        if not _finite(model.constant_prediction):
                            raise ValueError()
                    elif model.fitted_model is None:
                        raise ValueError()
                except Exception:
                    raise ForecastArtifactInvalidError("serialized weekly model is invalid") from None
                self._models[key] = LoadedWeeklyArtifact(
                    model, date.fromisoformat(meta["evaluation_cutoff"]),
                    float(meta["calibration_residual_q10"]), float(meta["calibration_residual_q90"]),
                    tuple(meta["warning_codes"]),
                )
            return self._models[key]
