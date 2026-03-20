"""
LOCAL / FALLBACK PATH ONLY

This module generates a rule-based analyst note without calling the AI.
It exists solely as a developer tool and offline fallback — it is NOT
the main product experience.

The main user-facing path is the AI path (prompt.py + Claude via run_ai.sh).
Analytical improvements — beat/miss framing, sector context, investment
signals, decision-oriented conclusions — are owned by the AI system prompt.

Do not build new product-quality analytical features here. If local logic
needs updating to remain a viable fallback, keep changes minimal and
clearly scoped to the fallback role.
"""
from __future__ import annotations

from .schema import FinancialData
from .sector_benchmarks import (
    get_benchmarks,
    sector_display_name,
    margin_label,
    leverage_label,
)


def _fmt(value: float, currency: str = "") -> str:
    """Format a number with optional currency prefix."""
    prefix = f"{currency} " if currency else ""
    if abs(value) >= 1_000:
        return f"{prefix}{value:,.1f}"
    return f"{prefix}{value:.1f}"


def _guidance_verdict(actual: float, low: float, high: float) -> tuple[str, float]:
    midpoint = (low + high) / 2
    if actual > midpoint:
        label = "BEAT"
    elif actual < midpoint:
        label = "MISS"
    else:
        label = "IN-LINE"
    return label, midpoint


def _compute_signal(
    data: FinancialData,
    bm: dict[str, float],
    sector_name: str,
) -> tuple[str, list[str], int, int]:
    """
    Score-based investment signal.

    Each of 6 metrics contributes +1 (positive), 0 (neutral/missing), or -1 (risk).
    Signal thresholds:  score >= +3 → Positive | score <= -3 → Cautious | else → Neutral.
    Missing data scores 0 — never penalised, never rewarded.

    Returns (rating, rationale_bullets, score, metrics_scored).
    """
    score = 0
    scored = 0
    bullets: list[str] = []

    inc      = data.income_statement
    bs       = data.balance_sheet
    cf       = data.cash_flow
    yoy      = data.yoy_changes or {}
    guidance = data.guidance

    # 1. Revenue YoY growth
    rev_growth = yoy.get("revenue")
    if rev_growth is not None:
        scored += 1
        if rev_growth >= 5:
            score += 1
            bullets.append(f"Revenue grew {rev_growth:.1f}% YoY, above the +5% threshold. (+1)")
        elif rev_growth < 0:
            score -= 1
            bullets.append(f"Revenue contracted {abs(rev_growth):.1f}% YoY. (-1)")
        else:
            bullets.append(f"Revenue grew {rev_growth:.1f}% YoY — below the +5% threshold. (0)")
    else:
        bullets.append("Revenue YoY growth: data not available. (0)")

    # 2. Gross margin vs sector benchmark
    if inc.gross_margin is not None:
        scored += 1
        lbl = margin_label(inc.gross_margin, bm["gross_strong"], bm["gross_moderate"])
        if lbl == "strong":
            score += 1
            bullets.append(
                f"Gross margin of {inc.gross_margin:.1f}% is strong for {sector_name} "
                f"(≥{bm['gross_strong']:.0f}% threshold). (+1)"
            )
        elif lbl == "weak":
            score -= 1
            bullets.append(
                f"Gross margin of {inc.gross_margin:.1f}% is weak for {sector_name} "
                f"(<{bm['gross_moderate']:.0f}% moderate floor). (-1)"
            )
        else:
            bullets.append(f"Gross margin of {inc.gross_margin:.1f}% is moderate for {sector_name}. (0)")
    else:
        bullets.append("Gross margin: data not available. (0)")

    # 3. EBITDA margin vs sector benchmark
    if inc.ebitda_margin is not None:
        scored += 1
        lbl = margin_label(inc.ebitda_margin, bm["ebitda_strong"], bm["ebitda_moderate"])
        if lbl == "strong":
            score += 1
            bullets.append(f"EBITDA margin of {inc.ebitda_margin:.1f}% is strong for {sector_name}. (+1)")
        elif lbl == "weak":
            score -= 1
            bullets.append(
                f"EBITDA margin of {inc.ebitda_margin:.1f}% is weak for {sector_name} "
                f"(<{bm['ebitda_moderate']:.0f}% moderate floor). (-1)"
            )
        else:
            bullets.append(f"EBITDA margin of {inc.ebitda_margin:.1f}% is moderate for {sector_name}. (0)")
    else:
        bullets.append("EBITDA margin: data not available. (0)")

    # 4. Leverage (net debt / EBITDA)
    if bs.net_debt is not None and inc.ebitda is not None and inc.ebitda > 0:
        scored += 1
        lev = bs.net_debt / inc.ebitda
        lbl = leverage_label(lev, bm["leverage_high"], bm["leverage_elevated"])
        if lbl == "high":
            score -= 1
            bullets.append(
                f"Net debt / EBITDA of {lev:.1f}x exceeds the {sector_name} high threshold "
                f"of {bm['leverage_high']:.1f}x. (-1)"
            )
        elif lbl == "elevated":
            score -= 1
            bullets.append(
                f"Net debt / EBITDA of {lev:.1f}x is elevated for {sector_name} "
                f"(threshold: {bm['leverage_elevated']:.1f}x). (-1)"
            )
        else:
            score += 1
            bullets.append(
                f"Net debt / EBITDA of {lev:.1f}x is within {sector_name} norms. (+1)"
            )
    else:
        bullets.append("Leverage: insufficient data to score. (0)")

    # 5. FCF conversion (FCF / net income)
    if cf.free_cash_flow is not None and inc.net_income is not None and inc.net_income != 0:
        scored += 1
        fcf_conv = cf.free_cash_flow / inc.net_income
        if fcf_conv >= 0.90:
            score += 1
            bullets.append(f"FCF conversion of {fcf_conv:.0%} reflects high earnings quality. (+1)")
        elif fcf_conv < 0.70:
            score -= 1
            bullets.append(f"FCF conversion of {fcf_conv:.0%} is below the 70% threshold. (-1)")
        else:
            bullets.append(f"FCF conversion of {fcf_conv:.0%} is adequate. (0)")
    else:
        bullets.append("FCF conversion: data not available. (0)")

    # 6. EPS vs guidance midpoint
    if (guidance is not None
            and guidance.eps_low is not None and guidance.eps_high is not None
            and inc.eps_diluted is not None):
        scored += 1
        verdict, midpoint = _guidance_verdict(inc.eps_diluted, guidance.eps_low, guidance.eps_high)
        if verdict == "BEAT":
            score += 1
            bullets.append(f"EPS of {inc.eps_diluted:.2f} beat guidance midpoint of {midpoint:.2f}. (+1)")
        elif verdict == "MISS":
            score -= 1
            bullets.append(f"EPS of {inc.eps_diluted:.2f} missed guidance midpoint of {midpoint:.2f}. (-1)")
        else:
            bullets.append(
                f"EPS of {inc.eps_diluted:.2f} came in-line with guidance midpoint of {midpoint:.2f}. (0)"
            )
    else:
        bullets.append("EPS vs guidance: no guidance data available. (0)")

    # Determine rating
    if score >= 3:
        rating = "Positive"
    elif score <= -3:
        rating = "Cautious"
    else:
        rating = "Neutral"

    return rating, bullets, score, scored


def generate_local_note(data: FinancialData) -> str:
    sections: list[str] = []
    currency = data.company.currency or ""
    inc = data.income_statement
    bs = data.balance_sheet
    cf = data.cash_flow
    yoy = data.yoy_changes or {}
    guidance = data.guidance
    bm = get_benchmarks(data.company.sector)
    sector_name = sector_display_name(data.company.sector)

    # ------------------------------------------------------------------ #
    # Section 1 — Profitability Analysis
    # ------------------------------------------------------------------ #
    lines: list[str] = ["## Profitability Analysis\n"]

    # Revenue and YoY growth
    if inc.revenue is not None:
        rev_str = _fmt(inc.revenue, currency)
        rev_growth = yoy.get("revenue")
        if rev_growth is not None:
            direction = "grew" if rev_growth >= 0 else "declined"
            lines.append(
                f"{data.company.name} reported revenue of {rev_str}, "
                f"which {direction} {abs(rev_growth):.1f}% year-over-year."
            )
        else:
            lines.append(f"{data.company.name} reported revenue of {rev_str} (YoY growth data not available).")
    else:
        lines.append("Revenue data not available.")

    # Revenue beat/miss vs guidance
    if (guidance is not None
            and guidance.revenue_low is not None and guidance.revenue_high is not None
            and inc.revenue is not None):
        verdict, midpoint = _guidance_verdict(inc.revenue, guidance.revenue_low, guidance.revenue_high)
        mp_str = _fmt(midpoint, currency)
        lines.append(
            f"Revenue {verdict} guidance midpoint of {mp_str} "
            f"(guided range: {_fmt(guidance.revenue_low, currency)}–{_fmt(guidance.revenue_high, currency)})."
        )

    # EBITDA beat/miss vs guidance
    if (guidance is not None
            and guidance.ebitda_low is not None and guidance.ebitda_high is not None
            and inc.ebitda is not None):
        verdict, midpoint = _guidance_verdict(inc.ebitda, guidance.ebitda_low, guidance.ebitda_high)
        mp_str = _fmt(midpoint, currency)
        lines.append(
            f"EBITDA {verdict} guidance midpoint of {mp_str} "
            f"(guided range: {_fmt(guidance.ebitda_low, currency)}–{_fmt(guidance.ebitda_high, currency)})."
        )

    # Gross margin (stored as percentage, e.g. 36.0 = 36%)
    if inc.gross_margin is not None:
        gm = inc.gross_margin
        label = margin_label(gm, bm["gross_strong"], bm["gross_moderate"])
        lines.append(
            f"Gross margin of {gm:.1f}% is considered {label} relative to {sector_name} benchmarks."
        )
    else:
        lines.append("Gross margin: data not available.")

    # EBITDA margin (stored as percentage)
    if inc.ebitda_margin is not None:
        em = inc.ebitda_margin
        label = margin_label(em, bm["ebitda_strong"], bm["ebitda_moderate"])
        lines.append(f"EBITDA margin of {em:.1f}% is {label} for {sector_name}.")
    else:
        lines.append("EBITDA margin: data not available.")

    # Net margin (stored as percentage)
    if inc.net_margin is not None:
        nm = inc.net_margin
        label = margin_label(nm, bm["net_strong"], bm["net_moderate"])
        lines.append(f"Net margin of {nm:.1f}% is {label} for {sector_name}.")
    else:
        lines.append("Net margin: data not available.")

    # FCF quality
    if cf.free_cash_flow is not None and inc.net_income is not None and inc.net_income != 0:
        fcf_conversion = cf.free_cash_flow / inc.net_income
        quality = "high" if fcf_conversion >= 0.90 else ("adequate" if fcf_conversion >= 0.70 else "low")
        lines.append(
            f"FCF-to-net-income conversion of {fcf_conversion:.1%} suggests {quality} earnings quality "
            f"(FCF: {_fmt(cf.free_cash_flow, currency)}, net income: {_fmt(inc.net_income, currency)})."
        )
    elif cf.free_cash_flow is None:
        lines.append("Free cash flow data not available; FCF quality cannot be assessed.")

    sections.append("\n".join(lines))

    # ------------------------------------------------------------------ #
    # Section 2 — Risk Observations
    # ------------------------------------------------------------------ #
    bullets: list[str] = []

    # Leverage: net debt / EBITDA
    if bs.net_debt is not None and inc.ebitda is not None and inc.ebitda > 0:
        leverage = bs.net_debt / inc.ebitda
        lev_lbl = leverage_label(leverage, bm["leverage_high"], bm["leverage_elevated"])
        if lev_lbl == "high":
            bullets.append(
                f"**High leverage**: Net debt / EBITDA of {leverage:.1f}x exceeds the "
                f"{sector_name} high threshold of {bm['leverage_high']:.1f}x — "
                f"balance sheet flexibility is materially constrained."
            )
        elif lev_lbl == "elevated":
            bullets.append(
                f"**Elevated leverage**: Net debt / EBITDA of {leverage:.1f}x exceeds the "
                f"{sector_name} elevated threshold of {bm['leverage_elevated']:.1f}x — "
                f"debt service warrants monitoring."
            )
        else:
            bullets.append(
                f"Net debt / EBITDA of {leverage:.1f}x is within a manageable range for {sector_name}."
            )
    elif bs.net_debt is not None or inc.ebitda is not None:
        bullets.append("Leverage ratio cannot be calculated — net debt or EBITDA data missing.")

    # Debt-to-equity
    if bs.total_debt is not None and bs.total_equity is not None and bs.total_equity != 0:
        dte = bs.total_debt / bs.total_equity
        bullets.append(f"Debt-to-equity ratio of {dte:.2f}x.")

    # FCF conversion risk
    if cf.free_cash_flow is not None and inc.net_income is not None and inc.net_income != 0:
        fcf_conv = cf.free_cash_flow / inc.net_income
        if fcf_conv < 0.70:
            bullets.append(
                f"**Weak FCF conversion**: FCF / net income of {fcf_conv:.1%} is below the 70% threshold, "
                f"suggesting potential accruals or working capital drag."
            )


    # Capex intensity
    if cf.capex is not None and inc.revenue is not None and inc.revenue != 0:
        capex_pct = abs(cf.capex) / inc.revenue
        bullets.append(f"Capex intensity of {capex_pct:.1%} of revenue ({_fmt(cf.capex, currency)}).")

    # Guidance range width
    if guidance is not None and guidance.eps_low is not None and guidance.eps_high is not None:
        midpoint = (guidance.eps_low + guidance.eps_high) / 2
        if midpoint != 0:
            spread = (guidance.eps_high - guidance.eps_low) / abs(midpoint)
            if spread > 0.10:
                bullets.append(
                    f"**Wide guidance range**: EPS guidance of {guidance.eps_low}–{guidance.eps_high} "
                    f"implies a {spread:.1%} spread around midpoint, signaling elevated management uncertainty."
                )

    risk_section = "## Risk Observations\n\n"
    if bullets:
        risk_section += "\n".join(f"- {b}" for b in bullets)
    else:
        risk_section += "Insufficient data to identify specific risk factors."
    sections.append(risk_section)

    # ------------------------------------------------------------------ #
    # Section 3 — Capital Position
    # ------------------------------------------------------------------ #
    cap_lines: list[str] = ["## Capital Position\n"]

    # Cash, debt, net debt
    if bs.cash_and_equivalents is not None:
        cap_lines.append(f"Cash and equivalents: {_fmt(bs.cash_and_equivalents, currency)}.")
    if bs.total_debt is not None:
        cap_lines.append(f"Total debt: {_fmt(bs.total_debt, currency)}.")
    if bs.net_debt is not None:
        if bs.net_debt < 0:
            cap_lines.append(
                f"Net debt is negative ({_fmt(bs.net_debt, currency)}), indicating a **net cash position**."
            )
        else:
            cap_lines.append(f"Net debt: {_fmt(bs.net_debt, currency)}.")

    # Equity and working capital
    if bs.total_equity is not None:
        cap_lines.append(f"Total equity: {_fmt(bs.total_equity, currency)}.")
    if bs.working_capital is not None:
        cap_lines.append(f"Working capital: {_fmt(bs.working_capital, currency)}.")

    # Liquidity: cash as % of debt
    if bs.cash_and_equivalents is not None and bs.total_debt is not None and bs.total_debt > 0:
        liquidity_ratio = bs.cash_and_equivalents / bs.total_debt
        cap_lines.append(
            f"Cash covers {liquidity_ratio:.1%} of total debt, "
            f"{'providing adequate near-term liquidity' if liquidity_ratio >= 0.20 else 'suggesting limited liquidity buffer'}."
        )

    if len(cap_lines) == 1:
        cap_lines.append("Insufficient balance sheet data to assess capital position.")

    sections.append("\n".join(cap_lines))

    # ------------------------------------------------------------------ #
    # Section 4 — Key Takeaways
    # ------------------------------------------------------------------ #
    positives: list[str] = []
    risks: list[str] = []

    # Positives
    rev_growth = yoy.get("revenue")
    if rev_growth is not None and rev_growth > 0:
        positives.append(f"Revenue growth of {rev_growth:.1f}% YoY suggests sustained top-line momentum.")

    if inc.gross_margin is not None and inc.gross_margin >= bm["gross_strong"]:
        positives.append(
            f"Gross margin of {inc.gross_margin:.1f}% is strong relative to {sector_name} benchmarks."
        )

    if inc.ebitda_margin is not None and inc.ebitda_margin >= bm["ebitda_strong"]:
        positives.append(f"EBITDA margin of {inc.ebitda_margin:.1f}% reflects solid operating leverage for {sector_name}.")

    if cf.free_cash_flow is not None and inc.net_income is not None and inc.net_income != 0:
        fcf_conv = cf.free_cash_flow / inc.net_income
        if fcf_conv >= 0.90:
            positives.append(
                f"FCF conversion of {fcf_conv:.1%} indicates high earnings quality based on available data."
            )

    if (guidance is not None
            and guidance.eps_low is not None and guidance.eps_high is not None
            and inc.eps_diluted is not None):
        verdict, midpoint = _guidance_verdict(inc.eps_diluted, guidance.eps_low, guidance.eps_high)
        if verdict == "BEAT":
            positives.append(
                f"EPS of {inc.eps_diluted:.2f} beat guidance midpoint of {midpoint:.2f} "
                f"(range: {guidance.eps_low:.2f}–{guidance.eps_high:.2f}), "
                f"suggesting management delivered above its own expectations."
            )
        elif verdict == "MISS":
            risks.append(
                f"EPS of {inc.eps_diluted:.2f} missed guidance midpoint of {midpoint:.2f} "
                f"(range: {guidance.eps_low:.2f}–{guidance.eps_high:.2f}), "
                f"warranting scrutiny of the drivers behind the shortfall."
            )
        else:
            positives.append(
                f"EPS of {inc.eps_diluted:.2f} came in-line with guidance midpoint of {midpoint:.2f}."
            )

    # Risks
    if bs.net_debt is not None and inc.ebitda is not None and inc.ebitda > 0:
        lev = bs.net_debt / inc.ebitda
        if lev > bm["leverage_elevated"]:
            risks.append(
                f"Leverage of {lev:.1f}x net debt / EBITDA is elevated for {sector_name} and may limit financial flexibility."
            )

    if inc.ebitda_margin is not None and inc.ebitda_margin < bm["ebitda_moderate"]:
        risks.append(
            f"EBITDA margin of {inc.ebitda_margin:.1f}% is below the {sector_name} moderate benchmark "
            f"of {bm['ebitda_moderate']:.0f}% and warrants monitoring."
        )

    if cf.capex is not None and inc.revenue is not None and inc.revenue != 0:
        capex_pct = abs(cf.capex) / inc.revenue
        if capex_pct > 0.10:
            risks.append(f"Capex intensity of {capex_pct:.1%} of revenue represents a meaningful cash burden.")

    if guidance is not None and guidance.eps_low is not None and guidance.eps_high is not None:
        midpoint = (guidance.eps_low + guidance.eps_high) / 2
        if midpoint != 0 and (guidance.eps_high - guidance.eps_low) / abs(midpoint) > 0.10:
            risks.append("Wide EPS guidance range signals uncertainty in management's near-term outlook.")

    takeaway_section = "## Key Takeaways\n\n"
    all_bullets: list[str] = []
    for p in positives[:3]:
        all_bullets.append(f"- {p}")
    for r in risks[:2]:
        all_bullets.append(f"- {r}")

    if all_bullets:
        takeaway_section += "\n".join(all_bullets)
        takeaway_section += "\n\n*Based on available data. All observations are preliminary and subject to revision.*"
    else:
        takeaway_section += "Insufficient data to generate key takeaways."

    sections.append(takeaway_section)

    # ------------------------------------------------------------------ #
    # Section 5 — Investment Signal
    # ------------------------------------------------------------------ #
    rating, sig_bullets, sig_score, sig_scored = _compute_signal(data, bm, sector_name)
    score_str = f"+{sig_score}" if sig_score >= 0 else str(sig_score)
    bullet_text = "\n".join(f"- {b}" for b in sig_bullets)
    signal_section = (
        f"## Investment Signal\n\n"
        f"**Signal: {rating}** — Score: {score_str} ({sig_scored}/6 metrics scored)\n\n"
        f"**Rationale:**\n{bullet_text}\n\n"
        f"*Signal is rule-based and reflects only the data provided. "
        f"Not a buy/sell recommendation.*"
    )
    sections.append(signal_section)

    company_header = f"# Analyst Note — {data.company.name}"
    if data.company.ticker:
        company_header += f" ({data.company.ticker})"
    if data.company.period or data.company.fiscal_year:
        period_str = data.company.period or data.company.fiscal_year
        company_header += f" | {period_str}"

    return company_header + "\n\n" + "\n\n".join(sections)
