from __future__ import annotations

import json
from pathlib import Path
from typing import Optional

import typer
from pydantic import ValidationError
from rich.console import Console

from .client import generate_note
from .local_analysis import generate_local_note
from .prompt import SYSTEM_PROMPT, build_user_message
from .report_formatter import format_html, format_markdown
from .schema import FinancialData
from .validators import validate_financial_data

app = typer.Typer(add_completion=False, help="Generate IB analyst notes from structured financial data.")
console = Console()
err_console = Console(stderr=True)


@app.command()
def main(
    input: Path = typer.Option(..., "--input", "-i", exists=True, readable=True, help="Path to input JSON file."),
    output: Optional[Path] = typer.Option(None, "--output", "-o", help="Output file path. Auto-named if omitted."),
    format: str = typer.Option("markdown", "--format", help="Output format: markdown or html."),
    model: str = typer.Option("claude-sonnet-4-6", "--model", help="Claude model to use (only with --use-llm)."),
    dry_run: bool = typer.Option(False, "--dry-run", help="Validate input and print prompt; skip report generation."),
    use_llm: bool = typer.Option(False, "--use-llm", help="Use Claude AI (requires ANTHROPIC_API_KEY)."),
) -> None:
    # 1. Load JSON
    try:
        raw_dict = json.loads(input.read_text())
    except json.JSONDecodeError as e:
        err_console.print(f"[red]JSON parse error:[/red] {e}")
        raise typer.Exit(1)

    # 2. Validate schema
    try:
        data = FinancialData.model_validate(raw_dict)
    except ValidationError as e:
        err_console.print("[red]Input validation failed:[/red]")
        for error in e.errors():
            loc = " -> ".join(str(x) for x in error["loc"])
            err_console.print(f"  • {loc}: {error['msg']}")
        raise typer.Exit(1)

    c = data.company
    label = f"{c.name}{f' ({c.ticker})' if c.ticker else ''}{f', {c.period or c.fiscal_year}' if c.period or c.fiscal_year else ''}"
    console.print(f"[green]✓[/green]  Input validated — {label}")

    # Financial logic validation (warnings only — analyst can still produce a partial report)
    val_warnings, _val_errors = validate_financial_data(raw_dict)
    for w in val_warnings:
        console.print(f"[yellow][WARN][/yellow] {w}")

    # 3. Dry-run: print prompt and exit
    if dry_run:
        console.print("[bold yellow]-- DRY RUN: user message --[/bold yellow]")
        console.print(build_user_message(data))
        raise typer.Exit(0)

    # 4. Validate format
    if format not in ("markdown", "html"):
        err_console.print(f"[red]Unknown format:[/red] '{format}'. Use 'markdown' or 'html'.")
        raise typer.Exit(1)

    # 5. Generate note body
    if use_llm:
        console.print("   Mode: [bold]Claude AI[/bold]")
        try:
            note_body = generate_note(system=SYSTEM_PROMPT, user_message=build_user_message(data), model=model)
        except Exception as e:
            err_console.print(f"[red]API error:[/red] {e}")
            err_console.print("[yellow]Tip:[/yellow] Ensure ANTHROPIC_API_KEY is set in your environment or .env file.")
            raise typer.Exit(1)
    else:
        console.print(
            "[yellow]⚠  Local mode[/yellow] — rule-based output for development/testing only. "
            "Use [bold]--use-llm[/bold] for analysis quality."
        )
        note_body = generate_local_note(data)

    # 6. Format report
    if format == "html":
        report = format_html(data, note_body)
        ext = "html"
    else:
        report = format_markdown(data, note_body)
        ext = "md"

    # 7. Resolve output path (auto-name if not given)
    if output is None:
        from datetime import datetime
        folder = Path("outputs") / ("ai" if use_llm else "local")
        folder.mkdir(parents=True, exist_ok=True)
        slug = (c.ticker or c.name.replace(" ", "_")).upper()
        period = (c.period or c.fiscal_year or "report").replace(" ", "_")
        mode = "ai" if use_llm else "local"
        ts = datetime.now().strftime("%Y%m%d_%H%M%S")
        output = folder / f"{slug}_{period}_{mode}_{ts}.{ext}"

    output.write_text(report, encoding="utf-8")
    console.print(f"   Report saved: [bold]{output}[/bold]")
