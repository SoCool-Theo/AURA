"""Synthetic offline provenance checks; every evaluation/fit path is mocked."""

from contextlib import contextmanager
from dataclasses import replace
from datetime import date
from decimal import Decimal
import json
from types import SimpleNamespace
from unittest.mock import MagicMock, patch

import pytest

import backend.scripts.evaluate_forecasting_return_models as returns
import backend.scripts.evaluate_forecasting_volatility_models as volatility
import backend.scripts.forecasting_selection_provenance as provenance


CUTOFF = date(2026, 9, 17)
SECRET_URL = "postgresql+psycopg://synthetic:private-password@invalid.example/db"
SCRIPTS = [(returns, "run_persisted_return_model_evaluation", "ReturnModelEvaluationReport"),
           (volatility, "run_persisted_volatility_model_evaluation", "VolatilityModelEvaluationReport")]


def records():
    return tuple(SimpleNamespace(symbol=symbol, date=date(2020, 1, 1),
        adjusted_close=Decimal("100.123456789012"), volume=None, source="synthetic")
        for symbol in returns.USER_ASSET_SYMBOLS)


def fingerprint(rows):
    return provenance.build_market_data_fingerprint(rows, evaluation_cutoff=CUTOFF,
                                                    symbols=returns.USER_ASSET_SYMBOLS)


def empty_report(script, name):
    return getattr(script, name)(CUTOFF,date(2026,9,18),script.USER_ASSET_SYMBOLS,
                                (),script.USER_ASSET_SYMBOLS,(),(),(),())


@pytest.fixture(params=SCRIPTS, ids=["return", "volatility"])
def selection(request):
    script, function, report_name = request.param
    rows = records()
    report = empty_report(script, report_name)
    engine = MagicMock(); session = MagicMock(); service = MagicMock()
    service.get_range.return_value = rows

    @contextmanager
    def scope(factory):
        yield session

    with (
        patch.object(script,"create_database_engine",return_value=engine) as create,
        patch.object(script,"create_session_factory"),
        patch.object(script,"session_scope",side_effect=scope),
        patch.object(script,"MarketDataService",return_value=service),
        patch.object(script,"evaluate_histories",return_value=report) as evaluate,
        patch.object(script,"build_price_histories",wraps=script.build_price_histories) as histories,
    ):
        yield script,getattr(script,function),rows,report,engine,session,create,evaluate,histories


def test_canonical_fingerprint_precedes_evaluation_and_records_are_identical(selection):
    script,run,rows,report,engine,session,create,evaluate,histories = selection
    actual = fingerprint(rows)
    order = []
    original = provenance.build_market_data_fingerprint
    def spy(*args,**kwargs):
        order.append("fingerprint")
        return original(*args,**kwargs)
    evaluate.side_effect = lambda *args,**kwargs: (order.append("evaluate") or report)
    with patch.object(provenance,"build_market_data_fingerprint",side_effect=spy) as canonical:
        result = run(evaluation_cutoff=CUTOFF,database_url=SECRET_URL,
                     expected_market_data_fingerprint=actual.sha256,expected_row_count=len(rows))
    assert order == ["fingerprint","evaluate"]
    canonical.assert_called_once_with(rows,evaluation_cutoff=CUTOFF,symbols=script.USER_ASSET_SYMBOLS)
    histories.assert_called_once_with(rows)
    create.assert_called_once_with(SECRET_URL)
    assert replace(result,data_provenance=None) == report
    payload = json.loads(script.report_json(result))
    assert payload["data_provenance"] == {"provenance_verified":True,"evaluation_cutoff":"2026-09-17",
        "symbol_count":17,"row_count":len(rows),"market_data_fingerprint_sha256":actual.sha256}
    assert script.report_json(result) == script.report_json(result)
    assert SECRET_URL not in script.report_json(result)
    assert "private-password" not in script.report_json(result)
    engine.dispose.assert_called_once_with()
    session.commit.assert_not_called()


@pytest.mark.parametrize("mismatch", ["fingerprint","count"])
def test_mismatch_blocks_before_histories_candidates_and_evaluation(selection,mismatch):
    script,run,rows,_,engine,_,_,evaluate,histories = selection
    actual = fingerprint(rows)
    candidate_method = "_return_candidates" if script is returns else "_volatility_candidates"
    with patch.object(script,candidate_method,side_effect=AssertionError("candidates created")) as candidates:
        with pytest.raises(provenance.SelectionProvenanceError,match="provenance mismatch"):
            run(evaluation_cutoff=CUTOFF,database_url=SECRET_URL,
                expected_market_data_fingerprint="0"*64 if mismatch=="fingerprint" else actual.sha256,
                expected_row_count=len(rows)+1 if mismatch=="count" else len(rows))
    evaluate.assert_not_called(); histories.assert_not_called(); candidates.assert_not_called()
    engine.dispose.assert_called_once_with()


def test_nonofficial_run_without_expectations_explicitly_unverified(selection):
    script,run,rows,_,_,_,_,_,_ = selection
    result = run(evaluation_cutoff=CUTOFF,database_url=SECRET_URL)
    data = json.loads(script.report_json(result))["data_provenance"]
    assert data["provenance_verified"] is False
    assert data["market_data_fingerprint_sha256"] == fingerprint(rows).sha256
    assert data["row_count"] == len(rows)


@pytest.mark.parametrize("database_url", [None,"","   "])
def test_no_implicit_application_database_fallback(selection,database_url):
    _,run,_,_,_,_,create,evaluate,_ = selection
    with pytest.raises(provenance.SelectionProvenanceError,match="explicit database URL"):
        run(evaluation_cutoff=CUTOFF,database_url=database_url)
    create.assert_not_called(); evaluate.assert_not_called()


@pytest.mark.parametrize("mismatch", ["fingerprint","count"])
def test_cli_mismatch_preserves_existing_report_before_evaluation(selection,tmp_path,mismatch):
    script,_,rows,_,_,_,_,evaluate,histories = selection
    env_file = tmp_path/"synthetic.env"; env_file.write_text(f"DATABASE_URL={SECRET_URL}\n")
    output = tmp_path/"selection.json"; output.write_text("previous-user-report")
    with pytest.raises(SystemExit,match="provenance mismatch"):
        script.main(["--env-file",str(env_file),"--evaluation-cutoff","2026-09-17",
            "--expected-market-data-fingerprint","0"*64 if mismatch=="fingerprint" else fingerprint(rows).sha256,
            "--expected-row-count",str(len(rows)+1 if mismatch=="count" else len(rows)),"--output",str(output)])
    assert output.read_text() == "previous-user-report"
    evaluate.assert_not_called(); histories.assert_not_called()


@pytest.mark.parametrize("expected,count", [("0"*64,None),(None,17),("private-password",17),
                                          ("0"*64,0),("0"*64,-1),("0"*64,True)])
def test_invalid_expectations_fail_before_engine(selection,expected,count):
    _,run,_,_,_,_,create,evaluate,_ = selection
    with pytest.raises(provenance.SelectionProvenanceError) as caught:
        run(evaluation_cutoff=CUTOFF,database_url=SECRET_URL,
            expected_market_data_fingerprint=expected,expected_row_count=count)
    assert "private-password" not in str(caught.value)
    create.assert_not_called(); evaluate.assert_not_called()


@pytest.mark.parametrize("script,function,name", SCRIPTS)
@pytest.mark.parametrize("key", ["DATABASE_URL","TEST_DATABASE_URL","FORECASTING_DATABASE_URL"])
def test_cli_reads_only_requested_key_and_serializes_no_secret(tmp_path,capsys,script,function,name,key):
    env_file = tmp_path/"synthetic.env"
    env_file.write_text(f"{key}={SECRET_URL}\nUNRELATED_KEY=must-not-be-used\n",encoding="utf-8")
    output = tmp_path/"selection.json"
    report = replace(empty_report(script,name),data_provenance=provenance.SelectionDataProvenance(True,CUTOFF,17,17,"a"*64))
    with patch.object(script,function,return_value=report) as run:
        script.main(["--env-file",str(env_file),"--database-url-key",key,"--evaluation-cutoff","2026-09-17",
                     "--expected-market-data-fingerprint","a"*64,"--expected-row-count","17","--output",str(output)])
    run.assert_called_once_with(evaluation_cutoff=CUTOFF,database_url=SECRET_URL,
                               expected_market_data_fingerprint="a"*64,expected_row_count=17)
    assert "private-password" not in capsys.readouterr().out
    assert SECRET_URL not in output.read_text()


@pytest.mark.parametrize("script,function,name", SCRIPTS)
@pytest.mark.parametrize("key", ["DATABASE_URL","TEST_DATABASE_URL","FORECASTING_DATABASE_URL"])
def test_missing_requested_key_never_falls_back(tmp_path,monkeypatch,script,function,name,key):
    env_file = tmp_path/"synthetic.env"
    env_file.write_text("\n".join(f"{other}={SECRET_URL}" for other in
                        ["DATABASE_URL","TEST_DATABASE_URL","FORECASTING_DATABASE_URL"] if other!=key),encoding="utf-8")
    monkeypatch.setenv(key,SECRET_URL)
    output = tmp_path/"selection.json"
    with patch.object(script,function) as run:
        with pytest.raises(SystemExit,match=key) as caught:
            script.main(["--env-file",str(env_file),"--database-url-key",key,"--evaluation-cutoff","2026-09-17",
                         "--output",str(output)])
    assert SECRET_URL not in str(caught.value)
    run.assert_not_called(); assert not output.exists()


@pytest.mark.parametrize("script,function,name", SCRIPTS)
def test_connection_error_sanitized_and_existing_output_preserved(tmp_path,script,function,name):
    from sqlalchemy.exc import SQLAlchemyError
    env_file = tmp_path/"synthetic.env"; env_file.write_text(f"DATABASE_URL={SECRET_URL}\n")
    output = tmp_path/"selection.json"; output.write_text("previous-user-report")
    with patch.object(script,"create_database_engine",side_effect=SQLAlchemyError(SECRET_URL)):
        with pytest.raises(SystemExit) as caught:
            script.main(["--env-file",str(env_file),"--evaluation-cutoff","2026-09-17","--output",str(output)])
    assert SECRET_URL not in str(caught.value) and "private-password" not in str(caught.value)
    assert caught.value.__suppress_context__ is True
    assert output.read_text() == "previous-user-report"


def test_canonical_fingerprint_sensitive_to_volume_source_and_prices():
    rows = records(); original = fingerprint(rows)
    for field,value in [("volume",123),("source","changed"),("adjusted_close",Decimal("99"))]:
        changed = SimpleNamespace(**vars(rows[0])); setattr(changed,field,value)
        with pytest.raises(provenance.SelectionProvenanceError):
            provenance.verify_selection_records((changed,*rows[1:]),evaluation_cutoff=CUTOFF,
                expected_fingerprint=original.sha256,expected_row_count=len(rows))


@pytest.mark.parametrize("script,function,name", SCRIPTS)
def test_gate_passes_without_altering_evaluator_numerics_or_selection(tmp_path,script,function,name):
    rows = records(); actual = fingerprint(rows); engine = MagicMock()
    @contextmanager
    def scope(factory):
        yield MagicMock()
    def fake_evaluate(*,dataset,plan,target_type,candidate,fold_purposes):
        return tuple(script.ForecastEvaluationResult(symbol=dataset.symbol,target_type=target_type,
            candidate_id=candidate.candidate_id,fold_id=fold.fold_id,fold_purpose=fold.purpose,
            training_cutoff=fold.training_cutoff,evaluation_origin_start=fold.origin_start,
            evaluation_origin_end=fold.origin_end,training_observation_count=756,candidate_training_value_count=756,
            evaluated_observation_count=20,prediction_available=True,mae=.1,rmse=.12,
            directional_accuracy=.5 if script is returns else None,
            directional_evaluated_count=20 if script is returns else None,return_mape=None,warning=None,
            negative_prediction_clipped_count=0 if script is volatility else None)
            for fold in plan.folds if fold.purpose in fold_purposes)
    with (
        patch.object(script,"evaluate_candidate",side_effect=fake_evaluate),
        patch.object(script,"create_database_engine",return_value=engine),
        patch.object(script,"create_session_factory"),patch.object(script,"session_scope",side_effect=scope),
        patch.object(script,"MarketDataService") as service,
    ):
        service.return_value.get_range.return_value = rows
        before = script.evaluate_histories(script.build_price_histories(rows),evaluation_cutoff=CUTOFF)
        after = getattr(script,function)(evaluation_cutoff=CUTOFF,database_url=SECRET_URL,
            expected_market_data_fingerprint=actual.sha256,expected_row_count=len(rows))
    assert replace(after,data_provenance=None) == before
    assert all(result.mae == .1 and result.rmse == .12 for result in after.results)
    assert after.selection_summaries == before.selection_summaries
