# Changelog

All notable changes to this project will be documented here.
Format follows [Keep a Changelog](https://keepachangelog.com/en/1.0.0/).

---

## [Unreleased]

## [0.2.0] — 2026-06-16

### Added
- Data sufficiency preamble: if more than 30% of tracked financial fields are missing, a prominent caveat is prepended to the analyst note
- `Makefile` with `make run`, `make run-local`, `make test`, `make lint`, `make clean`
- `CHANGELOG.md` (this file)

### Changed
- README badges: Python version, license, CI status

---

## [0.1.2] — 2026-06-13

### Added
- FCF yield and earnings quality commentary in the Profitability Analysis prompt section
- Guidance credibility scoring: if actuals beat guidance midpoint by >5% on revenue or >10% on EPS, the model comments on management track record
- Pre-computed analytics (FCF margin, guidance beat/miss %) injected into user message to prevent model arithmetic errors
- Structured logging throughout (`--verbose` flag in CLI)
- Full PEP 484 type hints across all modules
- 41-test suite: `tests/test_validators.py` (22 tests) and `tests/test_schema.py` (19 tests)
- GitHub Actions CI (`.github/workflows/ci.yml`) — runs across Python 3.10/3.11/3.12

---

## [0.1.1] — 2026-06-11

### Added
- `--tone` flag: `conservative` / `balanced` / `bullish` — adjusts Investment Signal framing
- 6th analyst note section: **Comparable Valuation Context** — injects sector-typical P/E and EV/EBITDA ranges for 10 sectors and prompts for implied EV calculation
- Sharpened Investment Signal: explicit near-term (2Q) and medium-term (1–2Y) catalysts now required
- `--output-dir` flag: override default output directory

### Changed
- HTML report redesign: dark navy header, white card body, IB report-style section headings

---

## [0.1.0] — 2026-06-02

### Added
- Initial release
- AI path: `run_ai.sh` → `prompt.py` → Claude API → 5-section analyst note
- Local fallback path: `run_local.sh` → `local_analysis.py` (rule-based, no API)
- 5-section AI output: Profitability Analysis, Risk Observations, Capital Position, Key Takeaways, Investment Signal
- HTML and Markdown output formats
- Pydantic schema validation for all input JSON
- Financial sanity checks (validators.py)
- Sector benchmark table for local mode (sector_benchmarks.py)
- Example input: `Zephyr_Software_FY2024.json`
