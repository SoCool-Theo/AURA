"""Read-only, checksum-validated registry for trusted local forecast artifacts."""

from dataclasses import dataclass
from datetime import date
import hashlib
from io import BytesIO
import json
import math
from pathlib import Path
import re
from threading import RLock

import joblib

from ..core.instruments import USER_ASSET_SYMBOLS
from .artifacts import ARTIFACT_SCHEMA_VERSION, ROOT_MANIFEST_SCHEMA_VERSION
from .evaluation import ForecastTargetType
from .features import FEATURE_SET_VERSION
from .finalization import ForecastArtifactModel
from .inference_errors import (
    ForecastArtifactInvalidError, ForecastArtifactMissingError,
    ForecastArtifactVersionError, ForecastSymbolUnsupportedError,
)
from .selection import CANDIDATE_SIMPLICITY_ORDER, VOLATILITY_CANDIDATE_SIMPLICITY_ORDER
from .targets import TARGET_SET_VERSION


@dataclass(frozen=True, slots=True)
class LoadedForecastArtifact:
    model: ForecastArtifactModel
    evaluation_cutoff: date
    residual_q10: float
    residual_q90: float


def _read_bytes(path: Path) -> bytes:
    try:
        return path.read_bytes()
    except FileNotFoundError:
        raise ForecastArtifactMissingError("required forecast artifact is missing") from None
    except OSError:
        raise ForecastArtifactInvalidError("forecast artifact cannot be read") from None


def _json(payload: bytes) -> dict:
    try:
        parsed = json.loads(payload)
        if not isinstance(parsed, dict):
            raise ValueError()
        return parsed
    except (ValueError, UnicodeError):
        raise ForecastArtifactInvalidError("invalid forecast artifact JSON") from None


def _finite(value: object) -> bool:
    try:
        return type(value) in (int, float) and math.isfinite(value)
    except OverflowError:
        return False


class ForecastArtifactRegistry:
    """Validate all 34 pairs before deserializing; cache models, never forecasts.

    Artifact storage is trusted deployment input. SHA-256 detects drift but is
    not an authenticity signature for joblib's pickle-based serialization.
    A deployed version must remain immutable for this registry's lifetime.
    """

    def __init__(self, *, artifact_version: str, artifact_root: Path | None = None):
        if not re.fullmatch(r"forecast-v[0-9]+-[0-9]{8}", artifact_version):
            raise ForecastArtifactVersionError("invalid configured artifact version")
        self.artifact_version = artifact_version
        self._root = (artifact_root if artifact_root is not None else
                      Path(__file__).resolve().parents[2] / "artifacts" / "forecasting" / artifact_version)
        self._records = None
        self._metadata = {}
        self._models = {}
        self._lock = RLock()

    def _validate(self):
        manifest = _json(_read_bytes(self._root / "manifest.json"))
        if manifest.get("artifact_version") != self.artifact_version:
            raise ForecastArtifactVersionError("configured forecast artifact version mismatch")
        required = {
            "artifact_schema_version": ROOT_MANIFEST_SCHEMA_VERSION,
            "expected_symbol_count": 17, "expected_target_count": 2,
            "expected_artifact_count": 34, "generated_artifact_count": 34,
            "feature_version": FEATURE_SET_VERSION, "target_version": TARGET_SET_VERSION,
            "final_test_completed": True, "nominal_interval_coverage": 0.80,
        }
        if any(type(manifest.get(key)) is not type(value) or manifest[key] != value
               for key, value in required.items()):
            raise ForecastArtifactInvalidError("forecast root manifest contract mismatch")
        try:
            cutoff = date.fromisoformat(manifest["evaluation_cutoff"])
            entries = manifest["generated_artifacts"]
            if not isinstance(entries, list) or len(entries) != 34:
                raise ValueError()
        except (KeyError, ValueError, TypeError):
            raise ForecastArtifactInvalidError("invalid forecast root manifest records") from None
        records = {}
        metadata = {}
        for entry in entries:
            try:
                symbol = entry["symbol"]
                target = ForecastTargetType(entry["target_type"])
                key = (symbol, target)
                candidates = (CANDIDATE_SIMPLICITY_ORDER if target is ForecastTargetType.RETURN
                              else VOLATILITY_CANDIDATE_SIMPLICITY_ORDER)
                if symbol not in USER_ASSET_SYMBOLS or key in records or entry["selected_candidate_id"] not in candidates:
                    raise ValueError()
                for kind, filename in (("model", "model.joblib"), ("metadata", "metadata.json")):
                    expected_path = f"{symbol}/{target.value}/{filename}"
                    if entry[f"{kind}_path"] != expected_path:
                        raise ValueError()
                    path = self._root / expected_path
                    if not path.resolve().is_relative_to(self._root.resolve()):
                        raise ValueError()
                    content = _read_bytes(path)
                    if hashlib.sha256(content).hexdigest() != entry[f"{kind}_sha256"]:
                        raise ForecastArtifactInvalidError("forecast artifact checksum mismatch")
                    if kind == "metadata":
                        meta = _json(content)
                self._validate_metadata(meta, entry, cutoff, manifest)
                records[key] = entry
                metadata[key] = meta
            except (KeyError, ValueError, TypeError) as error:
                if isinstance(error, (ForecastArtifactInvalidError, ForecastArtifactMissingError)):
                    raise
                raise ForecastArtifactInvalidError("invalid forecast artifact record") from None
        expected = {(symbol, target) for symbol in USER_ASSET_SYMBOLS for target in ForecastTargetType}
        if set(records) != expected:
            raise ForecastArtifactInvalidError("forecast artifact symbol-target pairs are incomplete")
        self._records = records
        self._metadata = metadata

    @staticmethod
    def _validate_metadata(meta, entry, cutoff, manifest):
        required = {
            "artifact_schema_version": ARTIFACT_SCHEMA_VERSION,
            "artifact_version": manifest["artifact_version"],
            "symbol": entry["symbol"], "target_type": entry["target_type"],
            "selected_candidate_id": entry["selected_candidate_id"],
            "feature_version": FEATURE_SET_VERSION, "target_version": TARGET_SET_VERSION,
            "evaluation_cutoff": cutoff.isoformat(), "nominal_interval_coverage": 0.80,
            "interval_type": "empirical prediction interval",
            "artifact_file_sha256": entry["model_sha256"],
            "selection_manifest_sha256": manifest["selection_manifest_sha256"],
            "dataset_fingerprint_sha256": manifest["training_data_fingerprint_sha256"],
        }
        if any(meta.get(key) != value for key, value in required.items()):
            raise ForecastArtifactInvalidError("forecast artifact metadata mismatch")
        if (not _finite(meta.get("calibration_residual_q10"))
                or not _finite(meta.get("calibration_residual_q90"))
                or meta["calibration_residual_q10"] > meta["calibration_residual_q90"]
                or type(meta.get("calibration_observation_count")) is not int
                or meta["calibration_observation_count"] < 60):
            raise ForecastArtifactInvalidError("invalid frozen forecast calibration")

    def get(self, symbol: str, target: ForecastTargetType) -> LoadedForecastArtifact:
        if symbol not in USER_ASSET_SYMBOLS:
            raise ForecastSymbolUnsupportedError("unsupported forecast symbol")
        if not isinstance(target, ForecastTargetType):
            raise ForecastArtifactInvalidError("unsupported forecast target")
        key = (symbol, target)
        with self._lock:
            if self._records is None:
                self._validate()
            if key not in self._models:
                record = self._records[key]
                meta = self._metadata[key]
                path = self._root / record["model_path"]
                # Check the bytes again immediately before deserializing, including
                # targets first loaded later in the registry's lifetime.
                content = _read_bytes(path)
                if hashlib.sha256(content).hexdigest() != record["model_sha256"]:
                    raise ForecastArtifactInvalidError("forecast model checksum mismatch")
                metadata_bytes = _read_bytes(self._root / record["metadata_path"])
                if hashlib.sha256(metadata_bytes).hexdigest() != record["metadata_sha256"]:
                    raise ForecastArtifactInvalidError("forecast metadata checksum mismatch")
                try:
                    model = joblib.load(BytesIO(content))
                except Exception:
                    raise ForecastArtifactInvalidError("forecast model cannot be deserialized") from None
                families = {
                    "historical_average": "historical_average",
                    "moving_average_90_calendar_days": "moving_average",
                    "linear_regression_v1": "linear_regression",
                    "volatility_linear_regression_v1": "linear_regression",
                    "arima_1_0_1_v1": "arima",
                    "volatility_arima_1_0_1_v1": "arima",
                    "random_forest_v1": "random_forest",
                    "volatility_random_forest_v1": "random_forest",
                }
                if (not isinstance(model, ForecastArtifactModel)
                        or model.candidate_id != record["selected_candidate_id"]
                        or model.target_type is not target
                        or model.model_family != families[model.candidate_id]
                        or meta.get("model_family") != model.model_family):
                    raise ForecastArtifactInvalidError("serialized forecast model identity mismatch")
                if model.model_family in {"historical_average", "moving_average"}:
                    if not _finite(model.constant_prediction):
                        raise ForecastArtifactInvalidError("invalid frozen baseline prediction")
                elif model.fitted_model is None:
                    raise ForecastArtifactInvalidError("forecast model lacks fitted state")
                self._models[key] = LoadedForecastArtifact(
                    model, date.fromisoformat(meta["evaluation_cutoff"]),
                    float(meta["calibration_residual_q10"]), float(meta["calibration_residual_q90"]),
                )
            return self._models[key]
