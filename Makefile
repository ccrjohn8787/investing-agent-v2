.PHONY: setup fmt lint test run

VENV := .venv
PYTHON := python3
PIP := $(VENV)/bin/pip
PYTEST := $(VENV)/bin/pytest

setup:
	$(PYTHON) -m venv $(VENV)
	$(VENV)/bin/pip install -r hybrid_agent/infra/requirements.txt

fmt:
	@echo "No formatter configured; run lint for static checks."

lint:
	$(PYTHON) -m compileall hybrid_agent

test:
	$(PYTEST) -q

run:
	$(VENV)/bin/uvicorn hybrid_agent.api:app --reload
