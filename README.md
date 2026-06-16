# IB Analyst

![Python](https://img.shields.io/badge/python-3.10%2B-blue?logo=python&logoColor=white)
![License](https://img.shields.io/badge/license-MIT-green)
![CI](https://github.com/ShangyuZ/ib-analyst-Project/actions/workflows/ci.yml/badge.svg)

**Turn a JSON file of company financials into a professional analyst note — in seconds.**

---

## The Problem

Writing IB analyst notes is repetitive, time-intensive work. A analyst takes raw financial data, validates it, identifies key signals, structures the narrative, and formats the output — every time, for every company.

This tool automates the full pipeline. Give it structured financial data, and it produces a clean, investment-grade analyst note with key metrics, risk observations, capital position, and an investment signal. Either via Claude AI for a full narrative, or a local rule-based engine when you don't need the API.

---

## How It Works

```
examples/company.json
        │
        ▼
  Schema validation       ← Rejects malformed input immediately
        │
        ▼
  Financial checks        ← Flags missing fields, inconsistencies
        │
        ├── AI mode   ──► Claude Sonnet  ──► full analyst narrative
        └── Local mode ──► rule-based engine ──► structured template
                                    │
                                    ▼
                        outputs/  ← Markdown or HTML report
```

---

## Key Features

- **Structured input** — JSON schema with Pydantic validation; bad data fails fast
- **Two analysis modes** — Claude AI for narrative depth, local engine for instant output
- **Financial logic layer** — catches missing FCF, margin inconsistencies, null fields before generation
- **Investment signal** — every report ends with a directional signal and supporting rationale
- **Clean output** — Markdown by default, HTML available; auto-named with ticker, period, timestamp

---

## Example Output

> *From a real AI-generated report on Zephyr Software (ZPHY), FY2024:*

```
Net income growth of 24% YoY significantly outpaced revenue growth of 12%,
indicating operating leverage is materializing through margin expansion and
disciplined cost management. Cloud Services drove the performance divergence,
growing 18% YoY and representing 61% of revenue... FY2024 actuals of $18.5B
beat guidance midpoint of $18.0B by 2.8%, and diluted EPS of $6.85 beat the
midpoint of $6.5 by 5.4%, signaling conservatism and execution credibility.
```

**Investment Signal: Cautious** — strong FY2024 execution, but FY2025 guidance implies
a sharp deceleration to flat-to-1.6% revenue growth from 12%, and Software Licensing's
3% YoY signals structural headwinds the cloud business alone may not offset.

→ See full sample: [`ib_analyst/sample_outputs/ai/`](ib_analyst/sample_outputs/ai/)

---

## Quick Start

**Requirements:** Python 3.10+ · Anthropic API key (AI mode only)

```bash
cd ib_analyst
pip install -e .
cp .env.example .env        # add your ANTHROPIC_API_KEY
./scripts/run_ai.sh         # generates report in outputs/ai/
```

No API key? Use local mode:

```bash
./scripts/run_local.sh      # no key required, instant output
```

---

## Project Structure

```
ib-analyst/
├── README.md                  ← you are here
└── ib_analyst/
    ├── README.md              ← architecture, CLI reference, design decisions
    ├── scripts/
    │   ├── run_ai.sh          ← main entry point
    │   └── run_local.sh
    ├── examples/              ← sample JSON inputs (tech + financial services)
    ├── sample_outputs/        ← real generated reports (AI + local)
    └── core/ib_analyst/       ← Python package
```

→ [Full technical documentation](ib_analyst/README.md)
