"""Synthetic money calculations; no database, model or provider access."""

from copy import deepcopy
from dataclasses import asdict, replace
from datetime import date, timedelta
from decimal import Decimal, localcontext
from types import SimpleNamespace

import pytest
from pydantic import ValidationError

from backend.app.forecasting.inference_errors import ForecastPredictionError
from backend.app.forecasting.monetary_projection import build_monetary_projection, projection_amounts
from backend.app.schemas.forecasting_monetary import PortfolioMonetaryProjectionResponse
from backend.app.services.portfolio_baseline_resolver import PortfolioBaselineKind, PortfolioBaselineResolution


DAY = date(2026, 10, 9)


def baseline(kind="current", amount=Decimal("10000"), currency="USD"):
    valuation = SimpleNamespace(total_current_value_usd=amount, requested_date=DAY,
        oldest_price_as_of=DAY-timedelta(days=2), newest_price_as_of=DAY-timedelta(days=1))
    allocation = SimpleNamespace(total_proposed_amount=amount, plan_currency=currency)
    return PortfolioBaselineResolution(PortfolioBaselineKind(kind), (),
        valuation if kind == "current" else None, DAY if kind == "current" else None,
        allocation if kind == "planned" else None)


@pytest.mark.parametrize("kind,currency", [("current","USD"), ("planned","USD"), ("planned","THB")])
@pytest.mark.parametrize("rate,change,ending", [(.03,"300","10300"), (-.1,"-1000","9000"),
    (0.,"0","10000"), (-1.,"-10000","0"), (-1.2,"-12000","-2000")])
def test_money_uses_baseline_without_compounding_rounding_or_clipping(kind, currency, rate, change, ending):
    source = baseline(kind, currency=currency)
    before = deepcopy(source)
    result = build_monetary_projection(source, rate)
    assert result.baseline_amount == Decimal("10000")
    assert result.expected_change_amount == Decimal(change)
    assert result.estimated_ending_value == Decimal(ending)
    assert result.currency == currency and result.hypothetical == (kind == "planned")
    assert result.assumes_unchanged_fx == (currency == "THB")
    assert result.valuation_requested_date == (DAY if kind == "current" else None)
    assert result.oldest_price_as_of == (DAY-timedelta(days=2) if kind == "current" else None)
    assert result.newest_price_as_of == (DAY-timedelta(days=1) if kind == "current" else None)
    assert source == before
    public = PortfolioMonetaryProjectionResponse.model_validate(asdict(result))
    assert PortfolioMonetaryProjectionResponse.model_validate_json(public.model_dump_json()) == public
    assert isinstance(public.model_dump(mode="json")["baseline_amount"], str)


def test_legacy_has_no_fabricated_money_baseline():
    assert build_monetary_projection(baseline("legacy"), .03) is None


def test_money_precision_does_not_depend_on_callers_decimal_context():
    amount = Decimal("1234567890123456.123456789012")
    with localcontext() as context:
        context.prec = 160
        expected_change = amount * Decimal("0.01234567890123456")
        expected_ending = amount + expected_change
    with localcontext() as context:
        context.prec = 2
        assert projection_amounts(amount, .01234567890123456) == (expected_change, expected_ending)
        assert context.prec == 2


@pytest.mark.parametrize("rate", [1e308, 1e-308])
def test_extreme_finite_ratios_preserve_exact_arithmetic(rate):
    amount = Decimal("10000.000000000001")
    with localcontext() as context:
        context.prec = 1000
        change = amount * Decimal(str(rate))
        ending = amount + change
    assert projection_amounts(amount, rate) == (change, ending)


@pytest.mark.parametrize("amount", [Decimal("0"), Decimal("-1"), Decimal("NaN"),
    Decimal("Infinity"), True, 10000., "10000"])
def test_bad_baseline_amounts_are_controlled(amount):
    with pytest.raises(ForecastPredictionError):
        build_monetary_projection(baseline(amount=amount), .03)


@pytest.mark.parametrize("rate", [float("nan"), float("inf"), float("-inf"), True, ".03", None])
def test_invalid_ratios_are_controlled(rate):
    with pytest.raises(ForecastPredictionError):
        build_monetary_projection(baseline(), rate)


def test_missing_or_mixed_baseline_context_is_not_fabricated():
    for source in (
        replace(baseline(), valuation=None),
        replace(baseline(), planned_allocation=baseline("planned").planned_allocation),
        replace(baseline(), valuation_as_of=DAY-timedelta(days=1)),
        replace(baseline("planned"), planned_allocation=None),
        replace(baseline("planned"), valuation=baseline().valuation),
        replace(baseline("planned"), valuation_as_of=DAY),
        baseline("planned", currency="EUR"),
    ):
        with pytest.raises(ForecastPredictionError):
            build_monetary_projection(source, .03)


@pytest.mark.parametrize("field,value", [("oldest_price_as_of",DAY+timedelta(days=1)),
    ("newest_price_as_of",DAY+timedelta(days=1)), ("requested_date",None)])
def test_invalid_valuation_dates_are_controlled(field, value):
    source = baseline()
    setattr(source.valuation, field, value)
    with pytest.raises(ForecastPredictionError):
        build_monetary_projection(source, .03)


@pytest.mark.parametrize("field,value", [("currency","EUR"), ("currency","THB"),
    ("baseline_source","planned_investment"), ("baseline_amount","0"),
    ("expected_change_amount","NaN"), ("estimated_ending_value","Infinity"),
    ("hypothetical",True), ("hypothetical","false"), ("assumes_unchanged_fx",True),
    ("oldest_price_as_of",None), ("newest_price_as_of","2026-10-10"), ("limitations",[])])
def test_strict_projection_context_and_finite_amounts(field, value):
    payload = asdict(build_monetary_projection(baseline(), .03))
    payload[field] = value
    with pytest.raises(ValidationError):
        PortfolioMonetaryProjectionResponse.model_validate(payload)


@pytest.mark.parametrize("field,value", [("hypothetical",False), ("assumes_unchanged_fx",False),
    ("valuation_requested_date",DAY), ("oldest_price_as_of",DAY), ("newest_price_as_of",DAY)])
def test_planned_thb_disclosure_without_fabricated_market_dates(field, value):
    payload = asdict(build_monetary_projection(baseline("planned", currency="THB"), .03))
    payload[field] = value
    with pytest.raises(ValidationError):
        PortfolioMonetaryProjectionResponse.model_validate(payload)
