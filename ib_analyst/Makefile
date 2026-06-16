# Makefile — common dev commands for ib-analyst-Project
# Run from the ib_analyst/ directory.

PYTHON   := python3
CORE     := core
PKG      := ib_analyst
EXAMPLES := examples
OUT_AI   := outputs/ai
OUT_LOC  := outputs/local

.PHONY: help run run-local test lint clean

help:           ## Show this help message
	@grep -E '^[a-zA-Z_-]+:.*##' $(MAKEFILE_LIST) | \
	  awk 'BEGIN {FS = ":.*##"}; {printf "  \033[36m%-14s\033[0m %s\n", $$1, $$2}'

run:            ## Generate AI analyst note from the first example JSON
	@echo "Running AI analyst on $(EXAMPLES)/Zephyr_Software_FY2024.json ..."
	PYTHONPATH=$(CORE) $(PYTHON) -m $(PKG).cli \
	  --input $(EXAMPLES)/Zephyr_Software_FY2024.json \
	  --format html \
	  --use-llm
	@echo "Output saved to $(OUT_AI)/"

run-local:      ## Generate local (rule-based) note — no API key required
	@echo "Running local analyst on $(EXAMPLES)/Zephyr_Software_FY2024.json ..."
	PYTHONPATH=$(CORE) $(PYTHON) -m $(PKG).cli \
	  --input $(EXAMPLES)/Zephyr_Software_FY2024.json \
	  --format html
	@echo "Output saved to $(OUT_LOC)/"

test:           ## Run the full test suite
	PYTHONPATH=$(CORE) $(PYTHON) -m pytest tests/ -v

lint:           ## Check syntax on all Python source files
	@find $(CORE)/$(PKG)/ -name "*.py" -exec $(PYTHON) -m py_compile {} + && \
	  echo "All files compile OK"

clean:          ## Remove generated output files and Python cache
	rm -rf $(OUT_AI) $(OUT_LOC)
	find . -type d -name "__pycache__" -exec rm -rf {} + 2>/dev/null || true
	find . -name "*.pyc" -delete 2>/dev/null || true
