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
    body { font-family: Georgia, serif; max-width: 860px; margin: 48px auto; padding: 0 24px; color: #1a1a1a; line-height: 1.7; }
    h1 { font-size: 1.6rem; border-bottom: 2px solid #1a1a1a; padding-bottom: 8px; margin-bottom: 4px; }
    h2 { font-size: 1.15rem; margin-top: 2rem; color: #1a1a1a; border-left: 3px solid #555; padding-left: 10px; }
    .meta { color: #555; font-size: 0.9rem; margin-bottom: 1.5rem; }
    table { border-collapse: collapse; width: 100%; margin: 1rem 0 1.5rem; font-size: 0.95rem; }
    th { background: #1a1a1a; color: #fff; text-align: left; padding: 8px 12px; }
    td { padding: 7px 12px; border-bottom: 1px solid #e0e0e0; }
    tr:nth-child(even) td { background: #f7f7f7; }
    ul { padding-left: 1.4rem; }
    li { margin-bottom: 0.4rem; }
    hr { border: none; border-top: 1px solid #ddd; margin: 2rem 0; }
    p { margin: 0.6rem 0; }
    em { color: #555; }
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
  <h1>{title}</h1>
  <div class="meta">{meta_html}</div>

  <h2>Key Metrics</h2>
  <table>
    <thead><tr><th>Metric</th><th>Value</th></tr></thead>
    <tbody>
{table_rows_html}
    </tbody>
  </table>

  <hr>

  {body_html}
  {limitations_html}
</body>
</html>
"""
