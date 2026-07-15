.PHONY: install check fmt run clean

UV ?= uv

install:
	$(UV) sync
	@echo ""
	@echo "  + .venv ready (runtime + dev deps from pyproject.toml)"

check:
	$(UV) run model.py

fmt:
	$(UV) run ruff check --select I --fix .
	$(UV) run ruff format .

run:
	$(UV) run scripts/syndrome_bandwidth.py results
	$(UV) run scripts/latency_ladder.py results
	$(UV) run scripts/breakeven_ladder.py results

clean:
	find . -type d -name __pycache__ -exec rm -rf {} + 2>/dev/null || true
