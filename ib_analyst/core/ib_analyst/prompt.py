"""
prompt.py — System prompt construction and user message assembly for the AI analyst path.

This module is the analytical core of the IB Analyst Note Generator.  All
improvements to analytical depth, framing, and sector context belong here.
The local fallback path (local_analysis.py) is a developer tool only and
does not receive product-quality analytical enhancements.
"""
from __future__ import annotations

import json
from .schema import FinancialData

_TONE_INSTRUCTIONS: dict[str, str] = {
    "conservative": """\
━━━ TONE INSTRUCTION: CONSERVATIVE ━━━
Weight risk factors above positives. In the Investment Signal section, set the bar
for **Positive** higher: require at least two independently confirmed positives with
no material offsetting risk. Default to **Neutral** when data is mixed or incomplete.
Highlight what an investor should watch for or protect against. Avoid language that
implies upside without anchoring it to a specific, quantified data point.
""",
    "balanced": """\
━━━ TONE INSTRUCTION: BALANCED ━━━
Weigh positives and risks equally. Let the data determine the signal direction.
Present both the strongest bullish and the strongest bearish case — do not tilt
the narrative in either direction beyond what the numbers support.
""",
    "bullish": """\
━━━ TONE INSTRUCTION: BULLISH ━━━
Lead with what is working. In the Investment Signal section, lean toward **Positive**
where the data permits, but you must still cite a specific quantified counterpoint.
Highlight near-term and medium-term catalysts explicitly. Never manufacture positives
not supported by the data — anchor every constructive point to a number.
""",
}

# Sector-specific typical P/E and EV/EBITDA ranges for the Comparable Valuation section.
# Ranges are approximate public-market multiples as of 2024-25 for context only.
_SECTOR_MULTIPLES: dict[str, dict[str, str]] = {
    "technology":             {"pe": "25–40×", "ev_ebitda": "18–30×"},
    "software":               {"pe": "30–55×", "ev_ebitda": "20–40×"},
    "saas":                   {"pe": "35–60×", "ev_ebitda": "25–45×"},
    "financials":             {"pe": "10–15×", "ev_ebitda": "n/a (use P/B: 1–2×)"},
    "financial_services":     {"pe": "10–15×", "ev_ebitda": "n/a (use P/B: 1–2×)"},
    "healthcare":             {"pe": "18–28×", "ev_ebitda": "12–20×"},
    "pharma":                 {"pe": "15–25×", "ev_ebitda": "10–18×"},
    "industrials":            {"pe": "16–24×", "ev_ebitda": "10–16×"},
    "energy":                 {"pe": "10–18×", "ev_ebitda": "6–12×"},
    "consumer_staples":       {"pe": "18–28×", "ev_ebitda": "12–18×"},
    "consumer_discretionary": {"pe": "20–35×", "ev_ebitda": "12–20×"},
    "real_estate":            {"pe": "20–35×", "ev_ebitda": "15–25×"},
    "default":                {"pe": "18–25×", "ev_ebitda": "12–18×"},
}


def _resolve_sector_key(sector: str | None) -> str:
    if not sector:
        return "default"
    s = sector.lower()
    for key in _SECTOR_MULTIPLES:
        if key in s or s in key:
            return key
    # Broader keyword fallback
    if any(w in s for w in ("tech", "software", "cloud", "semi", "internet")):
        return "technology"
    if any(w in s for w in ("bank", "financ", "insur", "asset manag")):
        return "financials"
    if any(w in s for w in ("health", "pharma", "bio", "medic", "hospital")):
        return "healthcare"
    if any(w in s for w in ("oil", "gas", "mining", "util", "renew", "power")):
        return "energy"
    if any(w in s for w in ("retail", "apparel", "luxury", "auto", "consumer disc")):
        return "consumer_discretionary"
    if any(w in s for w in ("food", "bever", "grocer", "consumer staple")):
        return "consumer_staples"
    if any(w in s for w in ("manufactur", "aerospace", "defense", "logistic", "transport", "industrial")):
        return "industrials"
    if any(w in s for w in ("real estate", "reit", "property")):
        return "real_estate"
    return "default"


def _build_system_prompt(tone: str = "balanced") -> str:
    tone_block = _TONE_INSTRUCTIONS.get(tone, _TONE_INSTRUCTIONS["balanced"])

    return f"""\
You are a senior investment banking analyst. Write a concise first-pass analyst note.
Follow the exact 6-section structure below. No preamble, no closing remarks, no filler.

━━━ ANALYTICAL STANDARD ━━━
Lead with interpretation, not description.
The number is not the insight — what it means for an investor is.
Every sentence must answer: "so what?"

Fact vs inference:
- State data-derived facts directly: "Revenue grew 12% YoY."
- Signal inferences explicitly: use "suggests", "implies", "appears to reflect", or
  "points to" when causality is not directly evidenced by the data.
- Never present an inference as a fact.

Conciseness:
- Each sentence must add new analytical content. Do not restate what the previous
  sentence established.
- If a section requirement cannot be met due to missing data, omit that requirement
  rather than padding with qualifications.

━━━ WHAT NOT TO WRITE ━━━
Banned patterns — do not use these under any circumstances:
- Unanchored quality labels: "strong", "robust", "healthy", "solid" without a specific
  sector or data anchor (e.g. "68% gross margin, above the ~60% typical for SaaS" is
  acceptable; "strong gross margin" alone is not)
- Corporate filler: "hallmarks of", "demonstrates commitment to", "underscores
  management's focus on", "continued momentum"
- Descriptive openings: do not open any section by restating the top-line figure.
  Lead with what the figure implies.
- Empty hedges: "it remains to be seen", "time will tell", "subject to market conditions"

━━━ DATA USAGE RULES ━━━
Apply every applicable rule; skip rules where data is absent.

1. YoY: When present, lead with direction and magnitude of change — not the absolute
   level. A revenue level is a fact; whether it is accelerating or decelerating is
   the analytical point.
2. Segments: When present, decompose performance. Identify the primary driver. Flag
   divergence (e.g. a fast-growing segment masking a declining one).
3. Guidance: When present, compute midpoint = (low + high) / 2. The midpoint comparison
   (beat / in-line / miss) must appear in the Profitability Analysis section — not in
   Risk Observations. Include the midpoint value and the guidance range in the text.
4. Sector: When present, interpret margins and leverage relative to what is typical for
   that specific sector — not generic corporate norms.
5. Banking/financials: Use sector-appropriate framing (net interest income, cost-to-income,
   capital adequacy). Do not apply industrial-company margin logic.

{tone_block}

━━━ SECTIONS ━━━

## Profitability Analysis
3–5 sentences. Lead with the most important analytical point — not the revenue figure.
- Open with: what the revenue outcome implies (relative to prior period, guidance, or
  segment mix) — not with the revenue level itself.
- If guidance exists: state midpoint, guidance range, and whether actuals beat /
  came in-line / missed. This is required here, not elsewhere.
  Guidance credibility: if actuals beat guidance midpoint by more than 5% on revenue
  OR by more than 10% on EPS, add one sentence on management track record — e.g.
  "Management has now beaten its own guidance for [N] consecutive periods, which
  suggests guidance conservatism and may support a higher valuation multiple."
  If actuals missed guidance midpoint, flag this as a credibility concern to monitor.
- Use segment data to explain the driver — name the segment, its growth rate, and
  what it implies for the mix or trajectory.
- Interpret margin levels relative to sector norms if sector is known. Comment on
  direction and magnitude of margin change, not just the current level.
- FCF yield and earnings quality: if free_cash_flow and revenue are both present,
  compute FCF margin (FCF / revenue × 100) and state it explicitly.  If FCF
  margin exceeds net margin by more than 2pp, note that cash conversion is
  outpacing reported earnings — a quality signal.  If FCF margin is materially
  below net margin, flag the divergence and name a plausible cause (working
  capital build, elevated capex, or accruals).  Do not speculate if FCF data
  is absent.

## Risk Observations
3–5 bullets. Most material risk first.
- Each bullet: one specific risk anchored to a number, ratio, or data gap.
- For the most material bullet: state what an investor should watch for or act on.
- Flag missing critical data as an analytical limitation, not just a data gap.
- No generic macro risk language unless directly supported by a figure in the data.

## Capital Position
2–3 sentences.
- Lead with the net debt or net cash position and its strategic implication.
- If net debt / EBITDA is computable, state it with sector-appropriate interpretation.
- Close with one sentence on what the balance sheet enables or constrains
  (M&A capacity, return of capital, refinancing risk).
- If leverage or liquidity data is absent, state the limitation in one sentence only.

## Key Takeaways
Exactly 3 bullets.
- Bullet 1: the single most significant positive — what it means for an investor.
- Bullet 2: the single most significant concern — what an investor should act on.
- Bullet 3: forward-looking — guidance credibility, growth sustainability, or the
  key metric to monitor next period.
Do not repeat figures already stated above. Synthesise to a decision-relevant point.

## Comparable Valuation Context
2–3 sentences. Reference typical public-market multiples for the sector (P/E and
EV/EBITDA) that are supplied in the user message. Comment on what premium or discount
those ranges imply given this company's margin profile, growth rate, and leverage.
- If EPS, EBITDA, and sector multiples are all available, state the implied valuation
  range explicitly (e.g. "at the sector median EV/EBITDA of X×, EBITDA of $Ym implies
  enterprise value of ~$Zm").
- If data is insufficient for an implied EV range, note what additional information
  (market cap, share price, or enterprise value) would be required.
- Keep this section factual: stated multiples are sector norms, not price targets.

## Investment Signal
One bolded signal word on its own line, then 2–3 sentences, then the disclaimer.
- Signal: exactly **Positive**, **Neutral**, or **Cautious**
- Near-term catalyst (within next 2 quarters): cite the single most time-sensitive
  data point or event that could move the signal.
- Medium-term catalyst (next 1–2 years): cite the structural trend or strategic
  initiative most likely to drive re-rating.
- Acknowledge the single most important counterpoint in one clause.
- If data is too sparse for a directional call, use **Neutral** and state what data
  would change it.
- No new data or reasoning not already in the sections above.
- Final line (exact): *This signal reflects only the data provided and is not a buy/sell recommendation.*
"""


# Backwards-compatible constant (used by dry-run display when no tone is specified)
SYSTEM_PROMPT = _build_system_prompt(tone="balanced")


def _compute_guidance_beat(data: FinancialData) -> list[str]:
    """Return pre-computed guidance beat/miss annotations for the user message.

    These are passed as analyst context so the model does not have to
    re-derive them, reducing reasoning errors.

    Args:
        data: Validated :class:`FinancialData` instance.

    Returns:
        A list of annotation strings (empty if no guidance data present).
    """
    annotations: list[str] = []
    g = data.guidance
    inc = data.income_statement

    if g is None:
        return annotations

    # Revenue vs guidance
    if g.revenue_low is not None and g.revenue_high is not None and inc.revenue is not None:
        midpoint: float = (g.revenue_low + g.revenue_high) / 2
        if midpoint > 0:
            beat_pct = (inc.revenue - midpoint) / midpoint * 100
            direction = "beat" if beat_pct > 0 else "missed"
            annotations.append(
                f"Revenue guidance: actual {inc.revenue:.1f} vs midpoint {midpoint:.1f} "
                f"({direction} by {abs(beat_pct):.1f}%)"
            )

    # EPS vs guidance
    if g.eps_low is not None and g.eps_high is not None and inc.eps_diluted is not None:
        eps_mid: float = (g.eps_low + g.eps_high) / 2
        if eps_mid != 0:
            eps_beat_pct = (inc.eps_diluted - eps_mid) / abs(eps_mid) * 100
            direction = "beat" if eps_beat_pct > 0 else "missed"
            annotations.append(
                f"EPS guidance: actual {inc.eps_diluted:.2f} vs midpoint {eps_mid:.2f} "
                f"({direction} by {abs(eps_beat_pct):.1f}%)"
            )

    return annotations


def _compute_fcf_context(data: FinancialData) -> list[str]:
    """Return pre-computed FCF margin and quality annotations for the user message.

    Args:
        data: Validated :class:`FinancialData` instance.

    Returns:
        A list of annotation strings (empty if FCF or revenue data is absent).
    """
    annotations: list[str] = []
    inc = data.income_statement
    cf = data.cash_flow

    if cf.free_cash_flow is not None and inc.revenue is not None and inc.revenue > 0:
        fcf_margin = (cf.free_cash_flow / inc.revenue) * 100
        annotations.append(f"FCF margin (FCF / revenue): {fcf_margin:.1f}%")

        if inc.net_margin is not None:
            delta = fcf_margin - inc.net_margin
            if delta > 2.0:
                annotations.append(
                    f"FCF margin exceeds net margin by {delta:.1f}pp — cash conversion outpacing reported earnings"
                )
            elif delta < -2.0:
                annotations.append(
                    f"FCF margin trails net margin by {abs(delta):.1f}pp — earnings quality warrants scrutiny"
                )

    return annotations


def _check_data_sufficiency(data: FinancialData) -> tuple[int, int]:
    """Count present vs total tracked financial fields.

    Args:
        data: Validated :class:`FinancialData` instance.

    Returns:
        A ``(present, total)`` tuple of field counts.
    """
    inc = data.income_statement
    bs = data.balance_sheet
    cf = data.cash_flow

    tracked = [
        inc.revenue, inc.gross_profit, inc.ebitda, inc.ebit, inc.net_income,
        inc.eps_diluted, inc.gross_margin, inc.ebitda_margin, inc.net_margin,
        bs.total_assets, bs.total_debt, bs.cash_and_equivalents, bs.net_debt,
        bs.total_equity, bs.working_capital,
        cf.operating_cash_flow, cf.capex, cf.free_cash_flow, cf.dividends_paid,
    ]
    total = len(tracked)
    present = sum(1 for v in tracked if v is not None)
    return present, total


def build_user_message(data: FinancialData, tone: str = "balanced") -> str:
    """Assemble the user message sent to Claude for analyst note generation.

    Pre-computes derived metrics (FCF margin, guidance beat/miss percentages)
    and injects them as context so the model has accurate anchors for
    its analytical commentary.

    Args:
        data: Validated :class:`FinancialData` instance.
        tone: Analyst tone key — ``"conservative"``, ``"balanced"``, or ``"bullish"``.

    Returns:
        The complete user message string.
    """
    c = data.company

    context_lines: list[str] = [f"Company:     {c.name}"]
    if c.ticker:
        context_lines.append(f"Ticker:      {c.ticker}")
    if c.period or c.fiscal_year:
        context_lines.append(f"Period:      {c.period or c.fiscal_year}")
    if c.sector:
        context_lines.append(f"Sector:      {c.sector}")
    if c.currency:
        context_lines.append(f"Currency:    {c.currency} (all monetary figures in millions)")

    # Inject sector multiple context for the Comparable Valuation section
    sector_key = _resolve_sector_key(c.sector)
    multiples = _SECTOR_MULTIPLES[sector_key]
    context_lines.append(
        f"Sector multiples (typical public-market, for context only): "
        f"P/E {multiples['pe']}, EV/EBITDA {multiples['ev_ebitda']}"
    )

    if tone != "balanced":
        context_lines.append(f"Analyst tone: {tone.upper()}")

    # Pre-computed analytics to anchor the model
    guidance_notes = _compute_guidance_beat(data)
    fcf_notes = _compute_fcf_context(data)
    if guidance_notes or fcf_notes:
        context_lines.append("")
        context_lines.append("Pre-computed analytics (use these values directly — do not re-derive):")
        for note in guidance_notes + fcf_notes:
            context_lines.append(f"  • {note}")

    context = "\n".join(context_lines)

    # Data sufficiency check — warn model if >30% of fields are missing
    present, total = _check_data_sufficiency(data)
    missing_pct = (total - present) / total * 100
    if missing_pct > 30:
        missing_count = total - present
        context_lines.append(
            f"\n⚠ DATA SUFFICIENCY WARNING: {missing_count}/{total} tracked financial fields "
            f"are absent ({missing_pct:.0f}% missing). "
            "Your note MUST open with a prominent one-sentence caveat stating that the analysis "
            "is materially constrained by data gaps, and you should avoid strong directional "
            "conclusions where key inputs are absent. Flag specific missing fields by name where "
            "they would have changed the analysis."
        )

    context = "\n".join(context_lines)
    payload = data.model_dump(exclude_none=True)
    pretty = json.dumps(payload, indent=2)

    return (
        f"Write an analyst note for the following company.\n\n"
        f"{context}\n\n"
        f"Financial data:\n{pretty}"
    )
