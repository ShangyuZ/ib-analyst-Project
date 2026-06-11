from __future__ import annotations

import re
from datetime import date
from .schema import FinancialData


def _fmt(value: float, currency: str = "") -> str:
    prefix = f"{currency} " if currency else ""
    if abs(value) >= 1_000:
        return f"{prefix}{value:,.1f}"
    return f"{prefix}{value:.1f}"


def _metrics_rows(data: FinancialData) -> list[tuple[str, str]]:
    """Extract key metrics as (label, value) pairs for the summary table."""
    rows: list[tuple[str, str]] = []
    cur = data.company.currency or ""
    inc = data.income_statement
    bs = data.balance_sheet
    cf = data.cash_flow
    yoy = data.yoy_changes or {}

    if inc.revenue is not None:
        rev = _fmt(inc.revenue, cur)
        growth = yoy.get("revenue")
        rev += f" ({growth:+.1f}% YoY)" if growth is not None else ""
        rows.append(("Revenue", rev))

    if inc.gross_margin is not None:
        rows.append(("Gross Margin", f"{inc.gross_margin:.1f}%"))
    if inc.ebitda_margin is not None:
        rows.append(("EBITDA Margin", f"{inc.ebitda_margin:.1f}%"))
    if inc.net_margin is not None:
        rows.append(("Net Margin", f"{inc.net_margin:.1f}%"))
    if inc.eps_diluted is not None:
        rows.append(("EPS (Diluted)", f"{cur} {inc.eps_diluted:.2f}" if cur else f"{inc.eps_diluted:.2f}"))
    if bs.net_debt is not None:
        rows.append(("Net Debt", _fmt(bs.net_debt, cur)))
    if cf.free_cash_flow is not None:
        rows.append(("Free Cash Flow", _fmt(cf.free_cash_flow, cur)))

    return rows


def format_markdown(data: FinancialData, note_body: str) -> str:
    """
    Wraps the 4-section note body in a professional Markdown report.
    Adds: title, metadata line, key metrics table, then the body.
    """
    c = data.company
    title = f"# Analyst Note — {c.name}"
    if c.ticker:
        title += f" ({c.ticker})"
    if c.period or c.fiscal_year:
        title += f" | {c.period or c.fiscal_year}"

    meta_parts = []
    if c.sector:
        meta_parts.append(f"**Sector:** {c.sector}")
    if c.currency:
        meta_parts.append(f"**Currency:** {c.currency}")
    meta_parts.append(f"**Generated:** {date.today().isoformat()}")
    meta_line = " &nbsp;|&nbsp; ".join(meta_parts)

    rows = _metrics_rows(data)
    table_lines = [
        "| Metric | Value |",
        "|--------|-------|",
    ]
    for label, value in rows:
        table_lines.append(f"| {label} | {value} |")
    metrics_table = "\n".join(table_lines)

    # Strip the duplicate title from note_body (local_analysis already adds one)
    body = re.sub(r"^#[^\n]*\n+", "", note_body, count=1).strip()

    missing = _data_limitations(data)
    parts = [title, meta_line, "## Key Metrics\n\n" + metrics_table, "---", body]
    if missing:
        parts.append(_limitations_block_md(missing))
    return "\n\n".join(parts)


def _md_to_html_body(md: str) -> str:
    """
    Minimal Markdown-to-HTML converter for the patterns we use.
    Handles: # headings, - bullets, 1. numbered lists, **bold**, *italic*, plain paragraphs.
    """
    lines = md.splitlines()
    html_parts: list[str] = []
    in_ul = False
    in_ol = False

    def close_lists():
        nonlocal in_ul, in_ol
        if in_ul:
            html_parts.append("</ul>")
            in_ul = False
        if in_ol:
            html_parts.append("</ol>")
            in_ol = False

    for line in lines:
        stripped = line.strip()

        if stripped.startswith("## "):
            close_lists()
            text = _inline_md(stripped[3:])
            html_parts.append(f"<h2>{text}</h2>")

        elif stripped.startswith("# "):
            close_lists()
            text = _inline_md(stripped[2:])
            html_parts.append(f"<h1>{text}</h1>")

        elif stripped.startswith("- "):
            if in_ol:
                html_parts.append("</ol>")
                in_ol = False
            if not in_ul:
                html_parts.append("<ul>")
                in_ul = True
            text = _inline_md(stripped[2:])
            html_parts.append(f"  <li>{text}</li>")

        elif re.match(r"^\d+\. ", stripped):
            if in_ul:
                html_parts.append("</ul>")
                in_ul = False
            if not in_ol:
                html_parts.append("<ol>")
                in_ol = True
            text = _inline_md(re.sub(r"^\d+\. ", "", stripped))
            html_parts.append(f"  <li>{text}</li>")

        elif stripped == "---":
            close_lists()
            html_parts.append("<hr>")

        elif stripped == "":
            close_lists()

        else:
            close_lists()
            text = _inline_md(stripped)
            html_parts.append(f"<p>{text}</p>")

    close_lists()

    return "\n".join(html_parts)


def _inline_md(text: str) -> str:
    """Convert inline Markdown (bold, italic) to HTML."""
    text = re.sub(r"\*\*(.+?)\*\*", r"<strong>\1</strong>", text)
    text = re.sub(r"\*(.+?)\*", r"<em>\1</em>", text)
    return text


def _data_limitations(data: FinancialData) -> list[str]:
    """Return list of limitation strings for analytically critical missing fields."""
    missing: list[str] = []
    inc = data.income_statement
    bs  = data.balance_sheet
    cf  = data.cash_flow
    g   = data.guidance

    if inc.revenue             is None: missing.append("Revenue")
    if inc.ebitda              is None: missing.append("EBITDA")
    if inc.eps_diluted         is None: missing.append("EPS (diluted)")
    if inc.ebitda_margin       is None: missing.append("EBITDA margin")
    if bs.total_debt           is None: missing.append("Total debt")
    if bs.cash_and_equivalents is None: missing.append("Cash and equivalents")
    if cf.operating_cash_flow  is None: missing.append("Operating cash flow")
    if cf.free_cash_flow       is None: missing.append("Free cash flow")

    no_guidance = (
        g is None or (
            g.revenue_low is None and g.revenue_high is None and
            g.ebitda_low  is None and g.ebitda_high  is None and
            g.eps_low     is None and g.eps_high     is None
        )
    )
    if no_guidance:
        missing.append("Forward guidance (no numeric ranges provided)")

    return missing


def _limitations_block_md(missing: list[str]) -> str:
    items = "\n".join(f"- {m}" for m in missing)
    return (
        "---\n\n"
        "## Data Limitations\n\n"
        "The following key fields are absent from the input data. "
        "Conclusions relying on these metrics are omitted or flagged as unavailable above.\n\n"
        f"{items}\n\n"
        "*This note reflects only the data provided. Independent verification is recommended.*"
    )


def _limitations_block_html(missing: list[str]) -> str:
    items_html = "\n".join(f"    <li>{m}</li>" for m in missing)
    return (
        '<hr>\n'
        '<div style="border-left:3px solid #b8860b; padding:0.6rem 1rem; '
        'background:#fffdf0; margin-top:1.5rem;">\n'
        '  <h2 style="border-left:none; color:#b8860b; margin-top:0;">Data Limitations</h2>\n'
        '  <p>The following key fields are absent from the input data. '
        'Conclusions relying on these metrics are omitted or flagged as unavailable above.</p>\n'
        '  <ul>\n'
        f'{items_html}\n'
        '  </ul>\n'
        '  <p><em>This note reflects only the data provided. '
        'Independent verification is recommended.</em></p>\n'
        '</div>'
    )


def format_html(data: FinancialData, note_body: str) -> str:
    """
    Builds a standalone HTML report with simple inline CSS.
    Same structure as Markdown: title, metadata, metrics table, 4 sections.
    """
    c = data.company

    title = f"Analyst Note — {c.name}"
    if c.ticker:
        title += f" ({c.ticker})"
    if c.period or c.fiscal_year:
        title += f" | {c.period or c.fiscal_year}"

    meta_parts = []
    if c.sector:
        meta_parts.append(f"<strong>Sector:</strong> {c.sector}")
    if c.currency:
        meta_parts.append(f"<strong>Currency:</strong> {c.currency}")
    meta_parts.append(f"<strong>Generated:</strong> {date.today().isoformat()}")
    meta_html = " &nbsp;|&nbsp; ".join(meta_parts)

    rows = _metrics_rows(data)
    table_rows_html = "\n".join(
        f"      <tr><td>{label}</td><td>{value}</td></tr>"
        for label, value in rows
    )

    body = re.sub(r"^#[^\n]*\n+", "", note_body, count=1).strip()
    body_html = _md_to_html_body(body)

    missing = _data_limitations(data)
    limitations_html = _limitations_block_html(missing) if missing else ""

    css = """
    *, *::before, *::after { box-sizing: border-box; }
    body {
      font-family: 'Helvetica Neue', Arial, sans-serif;
      max-width: 900px;
      margin: 0 auto;
      padding: 0;
      color: #1c1c1c;
      line-height: 1.65;
      background: #f4f4f4;
    }
    .report-wrapper {
      background: #ffffff;
      margin: 36px auto;
      box-shadow: 0 2px 12px rgba(0,0,0,0.10);
    }
    /* ── Header band ── */
    .report-header {
      background: #0d1b2a;
      color: #ffffff;
      padding: 28px 36px 22px;
    }
    .report-header h1 {
      font-size: 1.45rem;
      font-weight: 700;
      margin: 0 0 6px;
      letter-spacing: 0.01em;
      color: #ffffff;
      border: none;
    }
    .report-header .meta {
      color: #a8bbd0;
      font-size: 0.82rem;
      letter-spacing: 0.03em;
      text-transform: uppercase;
    }
    /* ── Metrics table ── */
    .metrics-section {
      padding: 0 36px;
      border-bottom: 1px solid #e4e4e4;
      background: #f9f9f9;
    }
    .metrics-section h2 {
      font-size: 0.72rem;
      font-weight: 700;
      letter-spacing: 0.12em;
      text-transform: uppercase;
      color: #6b7280;
      margin: 0;
      padding: 16px 0 8px;
      border: none;
    }
    table {
      border-collapse: collapse;
      width: 100%;
      margin: 0 0 16px;
      font-size: 0.88rem;
    }
    thead th {
      background: #0d1b2a;
      color: #c9d8e8;
      text-align: left;
      padding: 7px 14px;
      font-weight: 600;
      font-size: 0.78rem;
      letter-spacing: 0.06em;
      text-transform: uppercase;
    }
    td {
      padding: 7px 14px;
      border-bottom: 1px solid #ebebeb;
      color: #1c1c1c;
    }
    tr:nth-child(even) td { background: #f5f7fa; }
    /* ── Body content ── */
    .report-body {
      padding: 28px 36px 36px;
    }
    h2 {
      font-size: 0.72rem;
      font-weight: 700;
      letter-spacing: 0.12em;
      text-transform: uppercase;
      color: #0d1b2a;
      margin-top: 2rem;
      margin-bottom: 0.5rem;
      padding-bottom: 5px;
      border-bottom: 2px solid #0d1b2a;
    }
    p { margin: 0.5rem 0 0.7rem; font-size: 0.93rem; }
    ul, ol { padding-left: 1.3rem; margin: 0.4rem 0 0.8rem; }
    li { margin-bottom: 0.45rem; font-size: 0.93rem; }
    hr { border: none; border-top: 1px solid #e4e4e4; margin: 1.8rem 0; }
    strong { color: #0d1b2a; }
    em { color: #6b7280; font-style: italic; }
    /* ── Footer disclaimer ── */
    .disclaimer {
      background: #f0f4f8;
      border-top: 1px solid #d1dde8;
      padding: 10px 36px;
      font-size: 0.75rem;
      color: #6b7280;
      text-align: center;
    }
    """

    return f"""<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="UTF-8">
  <meta name="viewport" content="width=device-width, initial-scale=1.0">
  <title>{title}</title>
  <style>{css}</style>
</head>
<body>
<div class="report-wrapper">
  <div class="report-header">
    <h1>{title}</h1>
    <div class="meta">{meta_html}</div>
  </div>

  <div class="metrics-section">
    <h2>Key Metrics</h2>
    <table>
      <thead><tr><th>Metric</th><th>Value</th></tr></thead>
      <tbody>
{table_rows_html}
      </tbody>
    </table>
  </div>

  <div class="report-body">
    {body_html}
    {limitations_html}
  </div>

  <div class="disclaimer">
    For informational purposes only. Not a buy/sell recommendation.
    All figures sourced from provided data; independent verification recommended.
  </div>
</div>
</body>
</html>
"""
