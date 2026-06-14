"""
tests/test_schema.py — Unit tests for ib_analyst.schema model validation and derived fields.

Run with:  cd ib_analyst && python -m pytest tests/ -v
"""
from __future__ import annotations

import pytest
from pydantic import ValidationError

from ib_analyst.schema import BalanceSheet, CashFlow, Company, FinancialData, IncomeStatement


# ---------------------------------------------------------------------------
# Company
# ---------------------------------------------------------------------------

class TestCompany:
    def test_minimal_company_name_only(self):
        c = Company(name="Acme Corp")
        assert c.name == "Acme Corp"
        assert c.ticker is None
        assert c.currency == "USD"

    def test_full_company_fields(self):
        c = Company(name="Acme Corp", ticker="ACM", sector="Technology", fiscal_year="2024", currency="USD", period="FY2024")
        assert c.ticker == "ACM"
        assert c.sector == "Technology"

    def test_company_name_required(self):
        with pytest.raises(ValidationError):
            Company()  # name is required


# ---------------------------------------------------------------------------
# BalanceSheet — net_debt derivation
# ---------------------------------------------------------------------------

class TestBalanceSheetDerivation:
    def test_net_debt_derived_when_absent(self):
        bs = BalanceSheet(total_debt=500.0, cash_and_equivalents=200.0)
        assert bs.net_debt == 300.0

    def test_net_debt_not_overwritten_when_present(self):
        bs = BalanceSheet(total_debt=500.0, cash_and_equivalents=200.0, net_debt=150.0)
        assert bs.net_debt == 150.0  # stated value preserved

    def test_net_debt_none_when_inputs_missing(self):
        bs = BalanceSheet(total_debt=500.0)
        assert bs.net_debt is None

    def test_negative_net_debt_implies_net_cash(self):
        bs = BalanceSheet(total_debt=100.0, cash_and_equivalents=400.0)
        assert bs.net_debt == -300.0  # net cash position


# ---------------------------------------------------------------------------
# CashFlow — free_cash_flow derivation
# ---------------------------------------------------------------------------

class TestCashFlowDerivation:
    def test_fcf_derived_when_absent(self):
        cf = CashFlow(operating_cash_flow=300.0, capex=80.0)
        assert cf.free_cash_flow == pytest.approx(220.0)

    def test_fcf_not_overwritten_when_present(self):
        cf = CashFlow(operating_cash_flow=300.0, capex=80.0, free_cash_flow=100.0)
        assert cf.free_cash_flow == 100.0

    def test_fcf_none_when_ocf_missing(self):
        cf = CashFlow(capex=80.0)
        assert cf.free_cash_flow is None

    def test_fcf_none_when_capex_missing(self):
        cf = CashFlow(operating_cash_flow=300.0)
        assert cf.free_cash_flow is None


# ---------------------------------------------------------------------------
# IncomeStatement
# ---------------------------------------------------------------------------

class TestIncomeStatement:
    def test_all_fields_optional(self):
        inc = IncomeStatement()
        assert inc.revenue is None
        assert inc.ebitda is None

    def test_margin_fields_accept_floats(self):
        inc = IncomeStatement(gross_margin=62.5, ebitda_margin=28.3, net_margin=14.1)
        assert inc.gross_margin == pytest.approx(62.5)


# ---------------------------------------------------------------------------
# FinancialData — full model round-trip
# ---------------------------------------------------------------------------

class TestFinancialDataRoundTrip:
    def _minimal_dict(self) -> dict:
        return {
            "company": {"name": "Test Co", "ticker": "TST", "fiscal_year": "2024"},
            "income_statement": {"revenue": 1000.0, "ebitda": 250.0, "net_income": 150.0},
            "balance_sheet": {"total_debt": 400.0, "cash_and_equivalents": 150.0},
            "cash_flow": {"operating_cash_flow": 200.0, "capex": 60.0},
        }

    def test_model_validates_minimal_input(self):
        data = FinancialData.model_validate(self._minimal_dict())
        assert data.company.name == "Test Co"
        assert data.income_statement.revenue == 1000.0

    def test_derived_fields_computed_on_validation(self):
        data = FinancialData.model_validate(self._minimal_dict())
        # net_debt = 400 - 150 = 250
        assert data.balance_sheet.net_debt == pytest.approx(250.0)
        # fcf = 200 - 60 = 140
        assert data.cash_flow.free_cash_flow == pytest.approx(140.0)

    def test_model_dump_exclude_none_omits_missing_fields(self):
        data = FinancialData.model_validate(self._minimal_dict())
        dumped = data.model_dump(exclude_none=True)
        # Guidance was not provided — should be absent from dump
        assert "guidance" not in dumped

    def test_missing_required_company_name_raises(self):
        d = self._minimal_dict()
        del d["company"]["name"]
        with pytest.raises(ValidationError):
            FinancialData.model_validate(d)

    def test_segments_default_none(self):
        data = FinancialData.model_validate(self._minimal_dict())
        assert data.segments is None

    def test_full_guidance_parsed(self):
        d = self._minimal_dict()
        d["guidance"] = {"revenue_low": 950.0, "revenue_high": 1050.0, "eps_low": 1.80, "eps_high": 2.00}
        data = FinancialData.model_validate(d)
        assert data.guidance is not None
        assert data.guidance.revenue_low == pytest.approx(950.0)
