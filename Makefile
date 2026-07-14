.PHONY: install fmt run clean

UV ?= uv

install:
	$(UV) sync
	@echo ""
	@echo "  + .venv ready (runtime + dev deps from pyproject.toml)"

fmt:
	$(UV) run ruff check --select I --fix figures.py constants.py style.py
	$(UV) run ruff format figures.py constants.py style.py

run:
	$(UV) run figures.py results

clean:
	find . -type d -name __pycache__ -exec rm -rf {} + 2>/dev/null || true
