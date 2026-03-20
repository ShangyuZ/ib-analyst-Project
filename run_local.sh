#!/bin/bash

# -------------------------------------------------------
# IB Analyst — Local Mode (no API key required)
# -------------------------------------------------------
# NOTE: Local mode is for development and testing only.
# It uses rule-based logic and produces generic template output.
# For meaningful analysis, use run_ai.sh instead.
#
# Usage:
#   ./run_local.sh                              → Markdown report (default)
#   ./run_local.sh --format html               → HTML report
#   ./run_local.sh --input path/to/file.json   → use custom input
#   ./run_local.sh --output note.md            → custom output path
#   ./run_local.sh --dry-run                   → validate only, no report
# -------------------------------------------------------

INPUT=$(ls examples/*.json 2>/dev/null | sort | tail -1)
if [ -z "$INPUT" ]; then
    echo "Error: no JSON file found in examples/"
    exit 1
fi

IB_INPUT="$INPUT" python3 -c "
import sys, os
sys.path.insert(0, 'src')
sys.argv = ['ib-analyst', '--input', os.environ['IB_INPUT'], '--format', 'html']
from ib_analyst.cli import app
app()
"
