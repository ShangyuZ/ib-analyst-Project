"""
tests/test_validators.py — Unit tests for ib_analyst.validators.validate_financial_data.

Run with:  cd ib_analyst && python -m pytest tests/ -v
"""
from __future__ import annotations

import pytest
from ib_analyst.validators import validate_financial_data


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _make_payload(
    revenue: float | None = 1000.0,
    gross_profit: float | None = 600.0,
    ebitda: float | None = 250.0,
    net_income: float | None = 150.0,
    gross_margin: float | None = 60.0,
    ebitda_margin: float | None = 25.0,
    net_margin: float | None = 15.0,
    total_debt: float | None = 400.0,
    cash: float | None = 200.0,
    ocf: float | None = 180.0,
    capex: float | None = 50.0,
    guidance: dict | None = None,
) -> dict:
    return {
        "income_statement": {
            "revenue": revenue,
            "gross_profit": gross_profit,
            "ebitda": ebitda,
            "net_income": net_income,
            "gross_margin": gross_margin,
            "ebitda_margin": ebitda_margin,
            "net_margin": net_margin,
        },
        "balance_sheet": {
            "total_debt": total_debt,
            "cash_and_equivalents": cash,
        },
        "cash_flow": {
            "operating_cash_flow": ocf,
            "capex": capex,
        },
        "guidance": guidance or {},
    }


# ---------------------------------------------------------------------------
# Happy path
# ---------------------------------------------------------------------------

class TestCleanPayload:
    def test_valid_data_no_issues(self):
        warnings, errors = validate_financial_data(_make_payload())
        assert warnings == []
        assert errors == []


# ---------------------------------------------------------------------------
# All-null detection
# ---------------------------------------------------------------------------

class TestAllNull:
    def test_all_null_returns_single_error(self):
        payload = _make_payload(
            revenue=None, gross_profit=None, ebitda=None, net_income=None,
            total_debt=None, cash=None, ocf=None, capex=None,
        )
        warnings, errors = validate_financial_data(payload)
        assert len(errors) == 1
        assert "null" in errors[0]

    def test_all_null_no_warnings(self):
        payload = _make_payload(
            revenue=None, gross_profit=None, ebitda=None, net_income=None,
            total_debt=None, cash=None, ocf=None, capex=None,
        )
        warnings, _ = validate_financial_data(payload)
        assert warnings == []


# ---------------------------------------------------------------------------
# Presence warnings
# ---------------------------------------------------------------------------

class TestPresenceWarnings:
    def test_missing_revenue_warns(self):
        payload = _make_payload(revenue=None, gross_profit=None, gross_margin=None, ebitda_margin=None, net_margin=None)
        warnings, errors = validate_financial_data(payload)
        assert any("Revenue" in w for w in warnings)
        assert errors == []

    def test_missing_net_income_warns(self):
        payload = _make_payload(net_income=None, net_margin=None)
        warnings, _ = validate_financial_data(payload)
        assert any("income" in w.lower() for w in warnings)

    def test_missing_debt_or_cash_warns(self):
        payload = _make_payload(total_debt=None)
        warnings, _ = validate_financial_data(payload)
        assert any("debt" in w.lower() or "cash" in w.lower() for w in warnings)

    def test_missing_ocf_warns(self):
        payload = _make_payload(ocf=None)
        warnings, _ = validate_financial_data(payload)
        assert any("cash flow" in w.lower() for w in warnings)


# ---------------------------------------------------------------------------
# Revenue ≥ Gross Profit
# ---------------------------------------------------------------------------

class TestRevenueHierarchy:
    def test_gross_profit_exceeds_revenue_is_error(self):
        payload = _make_payload(revenue=500.0, gross_profit=600.0)
        _, errors = validate_financial_data(payload)
        assert any("Gross profit" in e for e in errors)

    def test_equal_values_is_ok(self):
        payload = _make_payload(revenue=600.0, gross_profit=600.0)
        _, errors = validate_financial_data(payload)
        assert errors == []


# ---------------------------------------------------------------------------
# EBITDA > Gross Profit
# ---------------------------------------------------------------------------

class TestEbitdaOverGrossProfit:
    def test_ebitda_exceeds_gross_profit_warns(self):
        payload = _make_payload(ebitda=700.0, gross_profit=600.0)
        warnings, _ = validate_financial_data(payload)
        assert any("EBITDA" in w for w in warnings)


# ---------------------------------------------------------------------------
# Net Income > EBITDA
# ---------------------------------------------------------------------------

class TestNetIncomeOverEbitda:
    def test_net_income_exceeds_ebitda_warns(self):
        payload = _make_payload(net_income=300.0, ebitda=250.0)
        warnings, _ = validate_financial_data(payload)
        assert any("Net income" in w for w in warnings)


# ---------------------------------------------------------------------------
# Margin range checks
# ---------------------------------------------------------------------------

class TestMarginRange:
    @pytest.mark.parametrize("field,value", [
        ("gross_margin", -1.0),
        ("ebitda_margin", 120.0),
        ("net_margin", -0.5),
    ])
    def test_out_of_range_margin_warns(self, field, value):
        payload = _make_payload(**{field: value})
        warnings, _ = validate_financial_data(payload)
        assert any("outside expected range" in w for w in warnings)

    def test_zero_gross_margin_is_valid(self):
        payload = _make_payload(gross_margin=0.0)
        warnings, _ = validate_financial_data(payload)
        assert not any("outside expected range" in w for w in warnings)


# ---------------------------------------------------------------------------
# Guidance range checks
# ---------------------------------------------------------------------------

class TestGuidanceRanges:
    def test_inverted_revenue_guidance_is_error(self):
        payload = _make_payload(guidance={"revenue_low": 1100.0, "revenue_high": 900.0})
        _, errors = validate_financial_data(payload)
        assert any("revenue" in e for e in errors)

    def test_inverted_eps_guidance_is_error(self):
        payload = _make_payload(guidance={"eps_low": 5.0, "eps_high": 3.0})
        _, errors = validate_financial_data(payload)
        assert any("eps" in e for e in errors)

    def test_valid_guidance_range_no_error(self):
        payload = _make_payload(guidance={"revenue_low": 900.0, "revenue_high": 1100.0})
        _, errors = validate_financial_data(payload)
        assert not any("revenue" in e for e in errors)

    def test_partial_guidance_no_error(self):
        payload = _make_payload(guidance={"eps_low": 2.0})
        _, errors = validate_financial_data(payload)
        assert errors == []


# ---------------------------------------------------------------------------
# Edge cases
# ---------------------------------------------------------------------------

class TestEdgeCases:
    def test_empty_payload_no_exception(self):
        warnings, errors = validate_financial_data({})
        assert len(errors) == 1  # all-null error

    def test_partial_payload_only_revenue_no_blocking_error(self):
        payload = {"income_statement": {"revenue": 500.0}}
        _, errors = validate_financial_data(payload)
        assert errors == []

    def test_negative_net_income_no_blocking_error(self):
        payload = _make_payload(net_income=-50.0)
        _, errors = validate_financial_data(payload)
        assert errors == []
