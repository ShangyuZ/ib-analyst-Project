from __future__ import annotations

# ---------------------------------------------------------------------------
# LOCAL / FALLBACK PATH ONLY
#
# This module is used exclusively by local_analysis.py (the rule-based
# fallback path). It is NOT part of the main product experience.
#
# The AI path (prompt.py + Claude) handles sector-aware interpretation
# through contextual reasoning in the system prompt — it does not use
# this threshold table.
#
# Do not extend this module with product-facing analytical improvements.
# Enhancements to sector framing belong in the AI system prompt.
#
# ---------------------------------------------------------------------------
# Sector-specific thresholds for margin and leverage interpretation.
#
# Margin keys (all in percentage points, e.g. 25 means 25%):
#   gross_strong / gross_moderate  — lower bounds for "strong" / "moderate"
#   ebitda_strong / ebitda_moderate
#   net_strong / net_moderate
#
# Leverage key (net debt / EBITDA multiple):
#   leverage_high      — above this = high leverage
#   leverage_elevated  — above this (but <= high) = elevated leverage
# ---------------------------------------------------------------------------

SECTOR_BENCHMARKS: dict[str, dict[str, float]] = {
    "technology": {
        "gross_strong": 65, "gross_moderate": 45,
        "ebitda_strong": 25, "ebitda_moderate": 15,
        "net_strong":    20, "net_moderate":    8,
        "leverage_high": 4.0, "leverage_elevated": 2.0,
    },
    "financial_services": {
        # Gross/EBITDA margins are less meaningful for banks; net margin is key.
        # Leverage thresholds are intentionally wide — banks run on balance-sheet leverage by design.
        "gross_strong": 40, "gross_moderate": 20,
        "ebitda_strong": 30, "ebitda_moderate": 15,
        "net_strong":    15, "net_moderate":     5,
        "leverage_high": 10.0, "leverage_elevated": 6.0,
    },
    "healthcare": {
        "gross_strong": 55, "gross_moderate": 40,
        "ebitda_strong": 20, "ebitda_moderate": 10,
        "net_strong":    12, "net_moderate":     5,
        "leverage_high": 4.0, "leverage_elevated": 2.5,
    },
    "industrials": {
        "gross_strong": 35, "gross_moderate": 20,
        "ebitda_strong": 15, "ebitda_moderate":  8,
        "net_strong":     8, "net_moderate":      3,
        "leverage_high": 4.0, "leverage_elevated": 2.5,
    },
    "consumer_staples": {
        "gross_strong": 40, "gross_moderate": 25,
        "ebitda_strong": 15, "ebitda_moderate":  8,
        "net_strong":     8, "net_moderate":      4,
        "leverage_high": 4.0, "leverage_elevated": 2.5,
    },
    "consumer_discretionary": {
        "gross_strong": 45, "gross_moderate": 30,
        "ebitda_strong": 15, "ebitda_moderate":  8,
        "net_strong":     8, "net_moderate":      3,
        "leverage_high": 4.5, "leverage_elevated": 3.0,
    },
    "energy": {
        # Tighter leverage cap — commodity cash flows are volatile.
        "gross_strong": 40, "gross_moderate": 20,
        "ebitda_strong": 25, "ebitda_moderate": 12,
        "net_strong":    10, "net_moderate":     4,
        "leverage_high": 3.0, "leverage_elevated": 1.5,
    },
    "real_estate": {
        "gross_strong": 50, "gross_moderate": 35,
        "ebitda_strong": 35, "ebitda_moderate": 20,
        "net_strong":    15, "net_moderate":     5,
        "leverage_high": 8.0, "leverage_elevated": 5.0,
    },
    "default": {
        "gross_strong": 50, "gross_moderate": 30,
        "ebitda_strong": 20, "ebitda_moderate": 10,
        "net_strong":    15, "net_moderate":     5,
        "leverage_high": 5.0, "leverage_elevated": 3.0,
    },
}

# Substring → sector key. Checked in order; first match wins.
_KEYWORD_MAP: list[tuple[str, str]] = [
    # Financial services first — avoids "investment technology" matching "tech"
    ("asset management",    "financial_services"),
    ("wealth management",   "financial_services"),
    ("investment bank",     "financial_services"),
    ("financ",              "financial_services"),
    ("bank",                "financial_services"),
    ("insurance",           "financial_services"),
    # Technology
    ("software",            "technology"),
    ("semiconductor",       "technology"),
    ("hardware",            "technology"),
    ("internet",            "technology"),
    ("cloud",               "technology"),
    ("saas",                "technology"),
    ("tech",                "technology"),
    # Healthcare
    ("life science",        "healthcare"),
    ("biotech",             "healthcare"),
    ("pharma",              "healthcare"),
    ("medic",               "healthcare"),
    ("hospital",            "healthcare"),
    ("health",              "healthcare"),
    # Consumer Staples (before generic "consumer")
    ("consumer staple",     "consumer_staples"),
    ("grocery",             "consumer_staples"),
    ("beverage",            "consumer_staples"),
    ("food",                "consumer_staples"),
    # Consumer Discretionary
    ("consumer disc",       "consumer_discretionary"),
    ("retail",              "consumer_discretionary"),
    ("apparel",             "consumer_discretionary"),
    ("luxury",              "consumer_discretionary"),
    ("auto",                "consumer_discretionary"),
    ("consumer",            "consumer_discretionary"),
    # Industrials
    ("aerospace",           "industrials"),
    ("defense",             "industrials"),
    ("logistics",           "industrials"),
    ("transport",           "industrials"),
    ("manufactur",          "industrials"),
    ("industrial",          "industrials"),
    # Energy
    ("renewable",           "energy"),
    ("utilities",           "energy"),
    ("mining",              "energy"),
    ("energy",              "energy"),
    ("oil",                 "energy"),
    ("gas",                 "energy"),
    ("power",               "energy"),
    # Real estate
    ("real estate",         "real_estate"),
    ("reit",                "real_estate"),
    ("property",            "real_estate"),
]

_SECTOR_LABELS: dict[str, str] = {
    "technology":              "Technology",
    "financial_services":      "Financial Services",
    "healthcare":              "Healthcare",
    "industrials":             "Industrials",
    "consumer_staples":        "Consumer Staples",
    "consumer_discretionary":  "Consumer Discretionary",
    "energy":                  "Energy",
    "real_estate":             "Real Estate",
    "default":                 "broad market",
}


def resolve_sector(sector_str: str | None) -> str:
    """Map a free-text sector string to a benchmark key, or 'default' if unrecognised."""
    if not sector_str:
        return "default"
    s = sector_str.lower()
    for keyword, key in _KEYWORD_MAP:
        if keyword in s:
            return key
    return "default"


def get_benchmarks(sector_str: str | None) -> dict[str, float]:
    """Return the threshold dict for the given sector string."""
    return SECTOR_BENCHMARKS[resolve_sector(sector_str)]


def sector_display_name(sector_str: str | None) -> str:
    """Return a human-readable label for the resolved sector."""
    return _SECTOR_LABELS[resolve_sector(sector_str)]


def margin_label(value: float, strong_floor: float, moderate_floor: float) -> str:
    """Classify a margin value relative to sector-specific thresholds."""
    if value >= strong_floor:
        return "strong"
    if value >= moderate_floor:
        return "moderate"
    return "weak"


def leverage_label(leverage: float, high_floor: float, elevated_floor: float) -> str:
    """Classify a leverage ratio relative to sector-specific thresholds."""
    if leverage > high_floor:
        return "high"
    if leverage > elevated_floor:
        return "elevated"
    return "manageable"
