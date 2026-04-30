# GGIR QC Tool — Local Development & Testing
# Run any target with: make <target>
# Requires venv to be set up: python3 -m venv venv && pip install -r requirements.txt

VENV     = venv/bin
PYTHON   = $(VENV)/python
PY_TEST  = $(VENV)/pytest
STREAMLIT = $(VENV)/streamlit
UVICORN = $(PYTHON) -m uvicorn

# ── Default ───────────────────────────────────────────────────────────────────
.DEFAULT_GOAL := help

help:
	@echo ""
	@echo "  GGIR QC Tool — local commands"
	@echo ""
	@echo "  make test        Run unit tests (pytest)"
	@echo "  make test-cov    Run tests with coverage report"
	@echo "  make run-mock    Launch mock UI (no Azure credentials needed)"
	@echo "  make run         Launch real app (requires .streamlit/secrets.toml)"
	@echo "  make run-proxy   Launch PDF proxy service (port 8502)"
	@echo "  make check       Run tests then launch mock UI"
	@echo "  make setup       Create venv and install all dependencies"
	@echo ""

# ── Environment ───────────────────────────────────────────────────────────────
setup:
	python3 -m venv venv
	$(VENV)/pip install --upgrade pip -q
	$(VENV)/pip install -r requirements.txt
	@echo ""
	@echo "✅  venv ready. Dependencies installed."

# ── Testing ───────────────────────────────────────────────────────────────────
test:
	$(PY_TEST) -v

test-cov:
	$(PY_TEST) -v --cov=src --cov=config --cov-report=term-missing

# ── Local UI ──────────────────────────────────────────────────────────────────
# No Azure credentials required — safe for rapid UI iteration
run-mock:
	$(STREAMLIT) run app_mock.py

# Real app — needs .streamlit/secrets.toml populated with Azure credentials
run:
	@if [ ! -f .streamlit/secrets.toml ]; then \
		echo "❌  .streamlit/secrets.toml not found."; \
		echo "    Copy .streamlit/secrets.toml.example → secrets.toml and fill in credentials."; \
		exit 1; \
	fi
	$(STREAMLIT) run app.py

# PDF proxy service (required for in-app PDF viewing without SharePoint login)
run-proxy:
	$(UVICORN) pdf_proxy:app --host 0.0.0.0 --port 8502

# ── Pre-push checklist ────────────────────────────────────────────────────────
# Run this before pushing to dev to catch issues before GitHub Actions does
check: test
	@echo ""
	@echo "✅  All tests passed. Launching mock UI for manual verification..."
	@echo "    Close the browser tab and press Ctrl+C when done."
	@echo ""
	$(STREAMLIT) run app_mock.py

.PHONY: help setup test test-cov run-mock run run-proxy check
