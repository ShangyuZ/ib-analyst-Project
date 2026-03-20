#!/bin/bash

# -------------------------------------------------------
# IB Analyst — Claude AI Mode (requires ANTHROPIC_API_KEY)
# -------------------------------------------------------
# Usage:
#   ./run_ai.sh                                → Markdown report (default)
#   ./run_ai.sh --format html                 → HTML report
#   ./run_ai.sh --input path/to/file.json     → use custom input
#   ./run_ai.sh --output note.md              → custom output path
#   ./run_ai.sh --dry-run                     → validate only, no report
# -------------------------------------------------------

# Load API key from .env
if [ ! -f .env ]; then
    echo "Error: .env file not found."
    echo "Create a .env file with your key:"
    echo "  echo 'ANTHROPIC_API_KEY=your-key-here' > .env"
    exit 1
fi

export $(grep -v '^#' .env | xargs)

if [ -z "$ANTHROPIC_API_KEY" ]; then
    echo "Error: ANTHROPIC_API_KEY is not set in your .env file."
    exit 1
fi

INPUT=$(ls examples/*.json 2>/dev/null | sort | tail -1)
if [ -z "$INPUT" ]; then
    echo "Error: no JSON file found in examples/"
    exit 1
fi

IB_INPUT="$INPUT" python3 -c "
import sys, os
sys.path.insert(0, 'src')
sys.argv = ['ib-analyst', '--input', os.environ['IB_INPUT'], '--use-llm', '--model', 'claude-sonnet-4-6']
from ib_analyst.cli import app
app()
"
