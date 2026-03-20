# IB Analyst Note Generator

A command-line tool that takes a structured JSON file of company financials and produces a
professional investment banking analyst note — either via Claude AI (full narrative) or a
local rule-based engine (instant, no API key required).

---

## Project Structure

```
ib-analyst-project/
├── src/
│   └── ib_analyst/         # Core Python package
│       ├── cli.py           # Typer CLI entrypoint
│       ├── client.py        # Anthropic API client
│       ├── local_analysis.py # Rule-based local analysis engine
│       ├── prompt.py        # Prompt templates for Claude
│       ├── report_formatter.py # HTML/Markdown output rendering
│       ├── schema.py        # Pydantic input schema
│       ├── sector_benchmarks.py # Sector comparison data
│       └── validators.py    # Input validation logic
├── examples/
│   ├── Zephyr_Software_FY2024.json   # Tech company — fully populated
│   └── AtlasBank_FY2024.json         # Financial services — sparse (tests null handling)
├── outputs/                # Generated reports (gitignored)
│   ├── ai/
│   └── local/
├── run_ai.sh               # Run with Claude AI (requires API key)
├── run_local.sh            # Run without API key (rule-based)
├── pyproject.toml
└── .env.example
```

---

## Setup

**Requirements:** Python 3.10+

```bash
# Install the package in editable mode
pip install -e .
```

**Configure your API key** (only needed for `run_ai.sh`):

```bash
cp .env.example .env
# Edit .env and add your Anthropic API key:
# ANTHROPIC_API_KEY=sk-ant-...
```

---

## Usage

### AI mode (Claude-generated narrative)

```bash
./run_ai.sh
# Output: outputs/ai/<TICKER>_FY<YEAR>_ai_<timestamp>.html
```

### Local mode (rule-based, no API key)

```bash
./run_local.sh
# Output: outputs/local/<TICKER>_FY<YEAR>_local_<timestamp>.html
```

Both scripts pick up the most recently modified `.json` file from `examples/` by default.
Pass `--input`, `--output`, or `--format` flags to override:

```bash
./run_ai.sh --input examples/AtlasBank_FY2024.json --format html
./run_local.sh --input examples/Zephyr_Software_FY2024.json --output my_note.md
```

---

## Example Inputs

| File | Ticker | Sector | What it exercises |
|---|---|---|---|
| `Zephyr_Software_FY2024.json` | ZPHY | Technology Software | Fully populated — segments, guidance, margins, YoY growth |
| `AtlasBank_FY2024.json` | ATLB | Financial Services | Sparse data — tests null handling and financial-sector logic |

---

## Local vs AI Mode

| | Local mode | AI mode |
|---|---|---|
| API key required | No | Yes (`ANTHROPIC_API_KEY`) |
| Output quality | Rule-based template | Full analyst narrative |
| Speed | Instant | ~10–20 seconds |
| Use case | Dev/testing | Final reports |

---

## GitHub Setup

```bash
git init
git add .
git commit -m "Initial commit"

# On GitHub: create a new empty repository (no README, no .gitignore)
git remote add origin https://github.com/YOUR_USERNAME/YOUR_REPO_NAME.git
git branch -M main
git push -u origin main
```
