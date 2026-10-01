from datetime import date
import json
from pathlib import Path
from types import SimpleNamespace

import joblib
import pytest

from backend.app.core.instruments import USER_ASSET_SYMBOLS
from backend.app.forecasting.artifacts import (
    ARTIFACT_SCHEMA_VERSION,
    ForecastArtifactError,
    GitRevisionState,
    checksum_bytes,
    mark_artifact_run_completed,
    mark_final_test_started,
    prepare_artifact_run,
    write_artifact_bundle,
)
from backend.app.forecasting.evaluation import ForecastTargetType
from backend.app.forecasting.finalization import (
    CalibrationResult,
    DeploymentTrainingResult,
    FinalTestResult,
    ForecastArtifactModel,
)
from backend.app.forecasting.fingerprints import (
    build_market_data_fingerprint,
    compare_market_data_fingerprints,
)
from backend.app.forecasting.models import ARIMA_FIT_CONVERGENCE_WARNING
from backend.app.forecasting.selection_manifest import (
    FrozenSelectionManifest,
    FrozenSelectionRecord,
)


class _FakeFeatureModel:
    def predict(self, features):
        return tuple(float(row[0]) for row in features)


class _FakeArimaModel:
    def forecast(self, *, steps):
        return tuple(0.2 for _ in range(steps))


def _fingerprint():
    records = tuple(
        SimpleNamespace(
            symbol=symbol,
            date=date(2026, 9, 17),
            adjusted_close="100.000000000000",
            volume=100,
            source="synthetic",
        )
        for symbol in USER_ASSET_SYMBOLS
    )
    return build_market_data_fingerprint(
        records,
        evaluation_cutoff=date(2026, 9, 17),
        symbols=USER_ASSET_SYMBOLS,
    )


def _selection_records():
    return tuple(
        FrozenSelectionRecord(
            symbol=symbol,
            target_type=target_type,
            selected_candidate_id="historical_average",
            selected_candidate_kind="baseline",
            best_baseline_id="historical_average",
            best_baseline_mean_selection_mae=0.1,
            selected_candidate_mean_selection_mae=0.1,
            improvement_vs_best_baseline_percent=None,
            practical_tie_with_best_baseline=True,
            selection_warning=None,
            source_selection_report_sha256="a" * 64,
            evaluation_cutoff=date(2026, 9, 17),
        )
        for symbol in sorted(USER_ASSET_SYMBOLS)
        for target_type in sorted(ForecastTargetType, key=lambda item: item.value)
    )


def _manifest(records=None):
    selected = _selection_records() if records is None else records
    return FrozenSelectionManifest(
        schema_version="forecast-selection-manifest-v1",
        evaluation_cutoff=date(2026, 9, 17),
        expected_symbol_count=17,
        expected_target_count=2,
        selection_count=len(selected),
        records=selected,
        manifest_sha256="b" * 64,
    )


def _bundle_inputs():
    records = _selection_records()
    calibrations = tuple(
        CalibrationResult(
            symbol=record.symbol,
            target_type=record.target_type,
            selected_candidate_id=record.selected_candidate_id,
            fold_id="calibration-01",
            observation_count=60,
            residual_q10=-0.1,
            residual_q90=0.1,
            mae=0.1,
            rmse=0.2,
            negative_prediction_clipped_count=(
                0
                if record.target_type is ForecastTargetType.VOLATILITY
                else None
            ),
            warning=(
                ARIMA_FIT_CONVERGENCE_WARNING
                if record == records[0]
                else None
            ),
        )
        for record in records
    )
    final_tests = tuple(
        FinalTestResult(
            symbol=record.symbol,
            target_type=record.target_type,
            selected_candidate_id=record.selected_candidate_id,
            fold_id="final-test-01",
            observation_count=100,
            mae=0.2,
            rmse=0.3,
            directional_accuracy=(
                0.5 if record.target_type is ForecastTargetType.RETURN else None
            ),
            negative_prediction_clipped_count=(
                0
                if record.target_type is ForecastTargetType.VOLATILITY
                else None
            ),
            warning=None,
        )
        for record in records
    )
    training = tuple(
        DeploymentTrainingResult(
            symbol=record.symbol,
            target_type=record.target_type,
            selected_candidate_id=record.selected_candidate_id,
            model_family="historical_average",
            model_parameters={"aggregation": "all_completed_labels"},
            artifact_model=ForecastArtifactModel(
                candidate_id=record.selected_candidate_id,
                target_type=record.target_type,
                model_family="historical_average",
                constant_prediction=0.1,
            ),
            training_row_count=1000,
            training_origin_min=date(2020, 1, 1),
            training_origin_max=date(2026, 8, 1),
            warning=None,
        )
        for record in records
    )
    return records, calibrations, final_tests, training


def test_baseline_and_complex_wrappers_serialize_and_reload(tmp_path: Path) -> None:
    models = (
        ForecastArtifactModel(
            "historical_average",
            ForecastTargetType.RETURN,
            "historical_average",
            constant_prediction=-0.1,
        ),
        ForecastArtifactModel(
            "linear_regression_v1",
            ForecastTargetType.RETURN,
            "linear_regression",
            fitted_model=_FakeFeatureModel(),
        ),
        ForecastArtifactModel(
            "arima_1_0_1_v1",
            ForecastTargetType.RETURN,
            "arima",
            fitted_model=_FakeArimaModel(),
        ),
        ForecastArtifactModel(
            "random_forest_v1",
            ForecastTargetType.RETURN,
            "random_forest",
            fitted_model=_FakeFeatureModel(),
        ),
    )

    for index, model in enumerate(models):
        path = tmp_path / f"model-{index}.joblib"
        joblib.dump(model, path)
        loaded = joblib.load(path)
        if loaded.model_family == "arima":
            assert loaded.predict(steps=2) == (0.2, 0.2)
        elif loaded.model_family == "historical_average":
            assert loaded.predict(steps=2) == (-0.1, -0.1)
        else:
            assert loaded.predict(
                steps=2,
                feature_matrix=((0.1,), (0.2,)),
            ) == (0.1, 0.2)


def test_exactly_once_guard_allows_pre_final_restart_but_not_final_rerun(
    tmp_path: Path,
) -> None:
    root = tmp_path / "fake-version"
    state = prepare_artifact_run(
        artifact_root=root,
        artifact_version="fake-version",
    )
    assert prepare_artifact_run(
        artifact_root=root,
        artifact_version="fake-version",
    ) == state

    started = mark_final_test_started(artifact_root=root, state=state)
    with pytest.raises(ForecastArtifactError, match="already started"):
        prepare_artifact_run(
            artifact_root=root,
            artifact_version="fake-version",
        )
    completed = mark_artifact_run_completed(
        artifact_root=root,
        state=started,
    )
    assert completed.completed


def test_existing_artifact_version_cannot_be_overwritten(tmp_path: Path) -> None:
    root = tmp_path / "existing"
    root.mkdir()

    with pytest.raises(ForecastArtifactError, match="already exists"):
        prepare_artifact_run(artifact_root=root, artifact_version="existing")


def test_bundle_requires_and_writes_exactly_34_artifacts(tmp_path: Path) -> None:
    records, calibrations, final_tests, training = _bundle_inputs()
    fingerprint = _fingerprint()
    verification = compare_market_data_fingerprints(fingerprint, fingerprint)
    root = tmp_path / "fake-artifacts"

    generated = write_artifact_bundle(
        artifact_root=root,
        artifact_version="fake-version",
        selection_manifest=_manifest(records),
        verification=verification,
        fingerprint=fingerprint,
        calibrations=calibrations,
        final_tests=final_tests,
        training_results=training,
        git_state=GitRevisionState("c" * 40, True),
        creation_timestamp="2026-09-17T00:00:00Z",
    )

    assert len(generated) == 34
    manifest = json.loads((root / "manifest.json").read_text(encoding="utf-8"))
    assert manifest["expected_artifact_count"] == 34
    assert manifest["generated_artifact_count"] == 34
    assert manifest["final_test_completed"] is True
    metadata = json.loads(
        (
            root
            / records[0].symbol
            / records[0].target_type.value
            / "metadata.json"
        ).read_text(encoding="utf-8")
    )
    required = {
        "artifact_schema_version",
        "artifact_version",
        "symbol",
        "target_type",
        "selected_candidate_id",
        "model_family",
        "model_parameters",
        "feature_version",
        "target_version",
        "horizon_definition",
        "evaluation_cutoff",
        "deployment_training_row_count",
        "deployment_training_origin_min",
        "deployment_training_origin_max",
        "training_label_completion_rule",
        "dataset_fingerprint_sha256",
        "selection_manifest_sha256",
        "calibration_observation_count",
        "calibration_residual_q10",
        "calibration_residual_q90",
        "nominal_interval_coverage",
        "interval_type",
        "final_test_mae",
        "final_test_rmse",
        "warning_codes",
        "runtime_versions",
        "git_commit",
        "creation_timestamp_utc",
        "artifact_file_sha256",
    }
    assert required <= set(metadata)
    assert metadata["artifact_schema_version"] == ARTIFACT_SCHEMA_VERSION
    assert ARIMA_FIT_CONVERGENCE_WARNING in metadata["warning_codes"]
    serialized = json.dumps(metadata).casefold()
    assert "database_url" not in serialized
    assert "password" not in serialized
    assert "api_key" not in serialized


def test_missing_artifact_record_blocks_bundle_before_writing(tmp_path: Path) -> None:
    records, calibrations, final_tests, training = _bundle_inputs()
    fingerprint = _fingerprint()
    root = tmp_path / "incomplete"

    with pytest.raises(ForecastArtifactError, match="exactly 34"):
        write_artifact_bundle(
            artifact_root=root,
            artifact_version="fake-version",
            selection_manifest=_manifest(records[:-1]),
            verification=compare_market_data_fingerprints(
                fingerprint, fingerprint
            ),
            fingerprint=fingerprint,
            calibrations=calibrations[:-1],
            final_tests=final_tests[:-1],
            training_results=training[:-1],
            git_state=GitRevisionState("c" * 40, True),
        )
    assert not root.exists()


def test_warning_checksum_and_gitignore_contract(tmp_path: Path) -> None:
    assert checksum_bytes(b"stable") == checksum_bytes(b"stable")
    assert checksum_bytes(b"changed") != checksum_bytes(b"stable")
    ignored = Path(".gitignore").read_text(encoding="utf-8")
    assert "backend/artifacts/forecasting/" in ignored
    assert "backend/app/forecasting" not in ignored
    assert ARIMA_FIT_CONVERGENCE_WARNING == "arima_fit_convergence_warning"
