"""
validators.py — Financial data logical sanity checks.

Works on a plain dict (the JSON payload) so it can be reused
independently of any specific model class.
"""
from __future__ import annotations


def validate_financial_data(payload: dict) -> tuple[list[str], list[str]]:
    """Returns (warnings, errors). Errors are blocking; warnings are advisory."""
    warnings: list[str] = []
    errors: list[str] = []

    # Shorthand helpers
    def _get(*keys):
        """Safely traverse nested dicts. Returns None if any key is missing."""
        obj = payload
        for k in keys:
            if not isinstance(obj, dict):
                return None
            obj = obj.get(k)
        return obj

    income: dict = payload.get("income_statement") or {}
    guidance: dict = payload.get("guidance") or {}

    revenue: float | None = income.get("revenue")
    gross_profit: float | None = income.get("gross_profit")
    ebitda: float | None = income.get("ebitda")
    net_income: float | None = income.get("net_income")
    gross_margin: float | None = income.get("gross_margin")
    ebitda_margin: float | None = income.get("ebitda_margin")
    net_margin: float | None = income.get("net_margin")

    balance: dict = payload.get("balance_sheet") or {}
    total_debt: float | None = balance.get("total_debt")
    cash: float | None = balance.get("cash_and_equivalents")

    cash_flow: dict = payload.get("cash_flow") or {}
    ocf: float | None = cash_flow.get("operating_cash_flow")
    capex: float | None = cash_flow.get("capex")

    # ------------------------------------------------------------------
    # Check: all top-level sections are empty / all fields null
    # ------------------------------------------------------------------
    all_values: list[float | None] = [revenue, gross_profit, ebitda, net_income,
                                       total_debt, cash, ocf, capex]
    if all(v is None for v in all_values):
        errors.append("All financial fields are null — extraction appears to have completely failed")
        # Return early; remaining checks are meaningless
        return warnings, errors

    # ------------------------------------------------------------------
    # Presence checks (warnings)
    # ------------------------------------------------------------------
    if revenue is None:
        warnings.append("Revenue is missing — core profitability metrics will be incomplete")
    if net_income is None:
        warnings.append("Net income is missing — FCF quality cannot be assessed")
    if total_debt is None or cash is None:
        warnings.append("Total debt or cash is missing — net debt cannot be derived")
    if ocf is None or capex is None:
        warnings.append("Operating cash flow or capex is missing — free cash flow cannot be derived")

    # ------------------------------------------------------------------
    # Revenue ≥ Gross Profit (ERROR)
    # ------------------------------------------------------------------
    if revenue is not None and gross_profit is not None:
        if gross_profit > revenue:
            errors.append(
                f"Gross profit ({gross_profit:,.2f}) exceeds revenue ({revenue:,.2f}) — logically impossible"
            )

    # ------------------------------------------------------------------
    # Gross Profit ≥ EBITDA (WARNING — unusual but possible)
    # ------------------------------------------------------------------
    if gross_profit is not None and ebitda is not None:
        if ebitda > gross_profit:
            warnings.append(
                f"EBITDA ({ebitda:,.2f}) exceeds gross profit ({gross_profit:,.2f}) — unusual, verify D&A treatment"
            )

    # ------------------------------------------------------------------
    # EBITDA ≥ Net Income (WARNING — unusual but possible)
    # ------------------------------------------------------------------
    if ebitda is not None and net_income is not None:
        if net_income > ebitda:
            warnings.append(
                f"Net income ({net_income:,.2f}) exceeds EBITDA ({ebitda:,.2f}) — unusual, verify tax/interest items"
            )

    # ------------------------------------------------------------------
    # Margin range 0–100% (WARNING)
    # ------------------------------------------------------------------
    margin_fields: list[tuple[str, float | None]] = [
        ("Gross margin", gross_margin),
        ("EBITDA margin", ebitda_margin),
        ("Net margin", net_margin),
    ]
    for label, value in margin_fields:
        if value is not None and not (0.0 <= value <= 100.0):
            warnings.append(
                f"{label} of {value:.1f}% is outside expected range (0–100%) — likely extraction error"
            )

    # ------------------------------------------------------------------
    # Guidance low ≤ high (ERROR)
    # ------------------------------------------------------------------
    pairs: list[tuple[str, float | None, float | None]] = [
        ("revenue", guidance.get("revenue_low"), guidance.get("revenue_high")),
        ("ebitda",  guidance.get("ebitda_low"),  guidance.get("ebitda_high")),
        ("eps",     guidance.get("eps_low"),     guidance.get("eps_high")),
    ]
    for metric, low, high in pairs:
        if low is not None and high is not None and low > high:
            errors.append(
                f"Guidance {metric} low ({low}) > high ({high}) — range is inverted"
            )

    return warnings, errors
