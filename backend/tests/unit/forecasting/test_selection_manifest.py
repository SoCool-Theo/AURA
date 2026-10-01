from copy import deepcopy
from dataclasses import asdict
from datetime import date

import pytest

from backend.app.core.instruments import USER_ASSET_SYMBOLS
from backend.app.forecasting.evaluation import (
    ForecastEvaluationResult,
    ForecastTargetType,
)
from backend.app.forecasting.selection import (
    CANDIDATE_SIMPLICITY_ORDER,
    VOLATILITY_CANDIDATE_SIMPLICITY_ORDER,
    summarize_symbol_selection,
    summarize_volatility_selection,
)
from backend.app.forecasting.selection_manifest import (
    EXPECTED_SELECTION_FOLD_IDS,
    SelectionManifestError,
    freeze_selection_manifest,
    selection_manifest_from_dict,
    selection_manifest_json,
)
from backend.app.forecasting.splits import FoldPurpose


REPORT_HASH_A = "a" * 64
REPORT_HASH_B = "b" * 64


def _result(
    *,
    symbol: str,
    target_type: ForecastTargetType,
    candidate_id: str,
    fold_id: str,
    mae: float,
) -> ForecastEvaluationResult:
    return ForecastEvaluationResult(
        symbol=symbol,
        target_type=target_type,
        candidate_id=candidate_id,
        fold_id=fold_id,
        fold_purpose=FoldPurpose.SELECTION,
        training_cutoff=date(2023, 1, 1),
        evaluation_origin_start=date(2023, 1, 1),
        evaluation_origin_end=date(2023, 7, 1),
        training_observation_count=756,
        candidate_training_value_count=756,
        evaluated_observation_count=100,
        prediction_available=True,
        mae=mae,
        rmse=mae,
        directional_accuracy=(
            0.5 if target_type is ForecastTargetType.RETURN else None
        ),
        directional_evaluated_count=(
            100 if target_type is ForecastTargetType.RETURN else None
        ),
        return_mape=None,
        warning=None,
        negative_prediction_clipped_count=(
            0 if target_type is ForecastTargetType.VOLATILITY else None
        ),
    )


def _result_payload(result: ForecastEvaluationResult) -> dict[str, object]:
    payload = asdict(result)
    payload["target_type"] = result.target_type.value
    payload["fold_purpose"] = result.fold_purpose.value
    for key in (
        "training_cutoff",
        "evaluation_origin_start",
        "evaluation_origin_end",
    ):
        payload[key] = payload[key].isoformat()
    if result.target_type is ForecastTargetType.RETURN:
        payload.pop("negative_prediction_clipped_count")
    return payload


def _report(
    target_type: ForecastTargetType,
    overrides: dict[tuple[str, str], float] | None = None,
) -> dict[str, object]:
    candidate_order = (
        CANDIDATE_SIMPLICITY_ORDER
        if target_type is ForecastTargetType.RETURN
        else VOLATILITY_CANDIDATE_SIMPLICITY_ORDER
    )
    default_maes = {
        candidate_id: 0.1 + index * 0.02
        for index, candidate_id in enumerate(candidate_order)
    }
    results: list[ForecastEvaluationResult] = []
    summaries = []
    for symbol in USER_ASSET_SYMBOLS:
        candidate_maes = {
            candidate_id: (
                overrides.get((symbol, candidate_id), default_maes[candidate_id])
                if overrides
                else default_maes[candidate_id]
            )
            for candidate_id in candidate_order
        }
        symbol_results = tuple(
            _result(
                symbol=symbol,
                target_type=target_type,
                candidate_id=candidate_id,
                fold_id=fold_id,
                mae=candidate_maes[candidate_id],
            )
            for candidate_id in candidate_order
            for fold_id in EXPECTED_SELECTION_FOLD_IDS
        )
        results.extend(symbol_results)
        summary = (
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
        summaries.append(asdict(summary))
    return {
        "evaluation_cutoff": "2026-09-17",
        "evaluation_end_exclusive": "2026-09-18",
        "requested_symbols": list(USER_ASSET_SYMBOLS),
        "evaluated_symbols": list(USER_ASSET_SYMBOLS),
        "missing_symbols": [],
        "selection_fold_ids": list(EXPECTED_SELECTION_FOLD_IDS),
        "candidate_ids": list(candidate_order),
        "results": [_result_payload(result) for result in results],
        "selection_summaries": summaries,
    }


def _freeze(return_report=None, volatility_report=None):
    return freeze_selection_manifest(
        return_report=(
            _report(ForecastTargetType.RETURN)
            if return_report is None
            else return_report
        ),
        volatility_report=(
            _report(ForecastTargetType.VOLATILITY)
            if volatility_report is None
            else volatility_report
        ),
        return_report_sha256=REPORT_HASH_A,
        volatility_report_sha256=REPORT_HASH_B,
    )


def test_freeze_creates_exactly_34_deterministic_ordered_records() -> None:
    first = _freeze()
    second = _freeze()

    assert first == second
    assert first.selection_count == 34
    assert len(first.records) == 34
    assert tuple(
        (record.symbol, record.target_type.value) for record in first.records
    ) == tuple(
        sorted(
            (symbol, target.value)
            for symbol in USER_ASSET_SYMBOLS
            for target in ForecastTargetType
        )
    )
    assert len(first.manifest_sha256) == 64
    assert selection_manifest_from_dict(
        __import__("json").loads(selection_manifest_json(first))
    ) == first


def test_additive_data_provenance_does_not_change_selection_validation():
    return_report = _report(ForecastTargetType.RETURN)
    volatility_report = _report(ForecastTargetType.VOLATILITY)
    before = _freeze(return_report, volatility_report)
    for report in (return_report, volatility_report):
        report["data_provenance"] = {"provenance_verified": True,
            "evaluation_cutoff": "2026-09-17", "symbol_count": 17,
            "row_count": 69928, "market_data_fingerprint_sha256": "a" * 64}
    assert _freeze(return_report, volatility_report) == before


def test_wrong_cutoff_and_missing_symbol_are_rejected() -> None:
    wrong_cutoff = _report(ForecastTargetType.RETURN)
    wrong_cutoff["evaluation_cutoff"] = "2026-09-16"
    with pytest.raises(SelectionManifestError, match="cutoff"):
        _freeze(return_report=wrong_cutoff)

    missing = _report(ForecastTargetType.RETURN)
    missing["evaluated_symbols"] = missing["evaluated_symbols"][:-1]
    with pytest.raises(SelectionManifestError, match="17 Aura symbols"):
        _freeze(return_report=missing)


def test_duplicate_summary_and_unexpected_candidate_are_rejected() -> None:
    duplicate = _report(ForecastTargetType.RETURN)
    duplicate["selection_summaries"].append(
        deepcopy(duplicate["selection_summaries"][0])
    )
    with pytest.raises(SelectionManifestError, match="duplicate summary"):
        _freeze(return_report=duplicate)

    unexpected = _report(ForecastTargetType.RETURN)
    unexpected["candidate_ids"][-1] = "unexpected_model"
    with pytest.raises(SelectionManifestError, match="candidate IDs"):
        _freeze(return_report=unexpected)


def test_non_finite_selection_metric_is_rejected() -> None:
    report = _report(ForecastTargetType.RETURN)
    report["results"][0]["mae"] = float("nan")

    with pytest.raises(SelectionManifestError, match="finite"):
        _freeze(return_report=report)


def test_calibration_and_final_test_fields_cannot_change_selection() -> None:
    clean_return = _report(ForecastTargetType.RETURN)
    clean_volatility = _report(ForecastTargetType.VOLATILITY)
    changed_return = deepcopy(clean_return)
    changed_volatility = deepcopy(clean_volatility)
    changed_return["calibration_results"] = {"DIA": {"mae": 999.0}}
    changed_return["final_test_results"] = {"DIA": {"mae": 999.0}}
    changed_volatility["calibration_results"] = {"AAPL": {"mae": 999.0}}

    clean = _freeze(clean_return, clean_volatility)
    changed = _freeze(changed_return, changed_volatility)

    assert changed == clean


def test_freeze_preserves_report_selected_complex_candidates() -> None:
    return_report = _report(
        ForecastTargetType.RETURN,
        {("DIA", "random_forest_v1"): 0.08},
    )
    volatility_report = _report(
        ForecastTargetType.VOLATILITY,
        {("AAPL", "volatility_linear_regression_v1"): 0.08},
    )

    manifest = _freeze(return_report, volatility_report)
    by_key = {
        (record.symbol, record.target_type): record
        for record in manifest.records
    }

    dia = by_key[("DIA", ForecastTargetType.RETURN)]
    aapl = by_key[("AAPL", ForecastTargetType.VOLATILITY)]
    assert dia.selected_candidate_id == "random_forest_v1"
    assert dia.selected_candidate_kind == "complex"
    assert dia.improvement_vs_best_baseline_percent == pytest.approx(20.0)
    assert aapl.selected_candidate_id == "volatility_linear_regression_v1"
    assert aapl.selected_candidate_kind == "complex"
