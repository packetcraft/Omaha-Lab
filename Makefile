.DEFAULT_GOAL := help

# --------------------------------------------------------------------------- #
# Platform detection — works in Git Bash (Windows) and macOS/Linux terminals  #
# --------------------------------------------------------------------------- #
ifeq ($(OS),Windows_NT)
	PYTHON   := venv/Scripts/python
	PIP      := venv/Scripts/pip
	VENV_CMD := py -3.11 -m venv venv
else
	PYTHON   := venv/bin/python
	PIP      := venv/bin/pip
	VENV_CMD := python3.11 -m venv venv
endif

# --------------------------------------------------------------------------- #
# Setup                                                                        #
# --------------------------------------------------------------------------- #

.PHONY: install deps spacy-model env models

install: venv deps spacy-model env  ## Full first-run setup: venv + deps + spacy model + .env

venv:
	$(VENV_CMD)

deps:
	$(PIP) install -r requirements.txt

spacy-model:
	$(PYTHON) -m spacy download en_core_web_lg

env:
	@if [ ! -f .env ]; then \
		cp .env.example .env && echo "Created .env — open it and add your API keys"; \
	else \
		echo ".env already exists, skipping"; \
	fi

models:  ## Pull all required Ollama models (qwen2.5:1.5b, nomic-embed-text, llama-guard3)
	ollama pull qwen2.5:1.5b
	ollama pull nomic-embed-text
	ollama pull llama-guard3

# --------------------------------------------------------------------------- #
# Run                                                                          #
# --------------------------------------------------------------------------- #

.PHONY: run run-secure run-rag run-full ui phoenix

run:  ## Base agent — no guardrails, no RAG
	$(PYTHON) agent.py

run-secure:  ## Guarded agent — Llama Guard + Presidio + HITL
	$(PYTHON) agent.py --guard on --hitl on

run-rag:  ## RAG analyst — security_analyst persona + RAG retrieval
	$(PYTHON) agent.py --persona security_analyst --rag on

run-full:  ## Full-defense stack — all layers on, hr_assistant persona
	$(PYTHON) agent.py --persona hr_assistant --rag on --guard on --hitl on

ui:  ## Chainlit web UI (opens http://localhost:8000)
	$(PYTHON) -m chainlit run ui.py

phoenix:  ## Arize Phoenix trace server (opens http://127.0.0.1:6006)
	$(PYTHON) -m phoenix.server.main serve

# --------------------------------------------------------------------------- #
# Test                                                                         #
# --------------------------------------------------------------------------- #

.PHONY: test bench bench-regex

test:  ## Run the full test suite (107 tests, no live Ollama required)
	$(PYTHON) -m pytest tests/ -v

bench:  ## Run evaluation harness against full guard stack (needs llama-guard3)
	$(PYTHON) bench.py

bench-regex:  ## Run evaluation harness — regex pre-filter only, no Ollama needed
	$(PYTHON) bench.py --regex-only

# --------------------------------------------------------------------------- #
# Clean                                                                        #
# --------------------------------------------------------------------------- #

.PHONY: clean

clean:  ## Remove venv, ChromaDB cache, and Python bytecode
	rm -rf venv .chroma
	find . -type d -name __pycache__ -exec rm -rf {} + 2>/dev/null || true
	find . -name "*.pyc" -delete 2>/dev/null || true

# --------------------------------------------------------------------------- #
# Help                                                                         #
# --------------------------------------------------------------------------- #

.PHONY: help

help:  ## Show this help message
	@echo "Omaha-Lab — available targets:"
	@echo ""
	@grep -E '^[a-zA-Z_-]+:.*##' $(MAKEFILE_LIST) \
		| awk 'BEGIN {FS = ":.*## "}; {printf "  \033[36m%-16s\033[0m %s\n", $$1, $$2}'
	@echo ""
	@echo "Quick start:  make install models run"
