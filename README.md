# Omaha-Lab

**A hands-on lab guide for local LLM security, agentic tool-calling, and OWASP mitigation.**

Omaha-Lab (**O**llama + **M**ac/Windows + **H**uman + **A**gent) is a local-first research and development environment for exploring autonomous agent reasoning and cybersecurity guardrails. All inference stays on your hardware — no cloud LLM endpoints.

```
User Input
    │
    ▼
┌─────────────────────────────────────────────────────────┐
│  Llama Guard 3 (Input Guardrail)                        │
└──────────────────────┬──────────────────────────────────┘
                       │ safe
                       ▼
┌─────────────────────────────────────────────────────────┐
│  RAG Retrieval  (ChromaDB + nomic-embed-text)           │
└──────────────────────┬──────────────────────────────────┘
                       │ top-3 chunks
                       ▼
┌─────────────────────────────────────────────────────────┐
│  Persona System Prompt  (YAML → SystemMessage)          │
└──────────────────────┬──────────────────────────────────┘
                       │
                       ▼
┌─────────────────────────────────────────────────────────┐
│  LangGraph ReAct Agent  (Ollama LLM)                    │
│    Reason → Tool Call → Observe → Respond               │
└──────────────────────┬──────────────────────────────────┘
                       │ high-risk tool?
                       ▼
┌─────────────────────────────────────────────────────────┐
│  HITL Authorization  (human approve/deny)               │
└──────────────────────┬──────────────────────────────────┘
                       │
                       ▼
┌─────────────────────────────────────────────────────────┐
│  Output Guardrails                                      │
│    Presidio PII Redaction                               │
│    Canary Token Detection                               │
│    Output Schema Validation                             │
└──────────────────────┬──────────────────────────────────┘
                       │
                       ▼
                   Response
```

---

## Overview

| Layer | Technology |
|---|---|
| Local LLM inference | Ollama (Metal / CUDA / CPU) |
| Default model | Qwen 2.5 7B (recommended — best tool-calling discipline) |
| Alternative | Llama 3.1 8B |
| Fallback model | Phi-3 Mini 3.8B (low-VRAM / CPU-only) |
| Agent orchestration | LangGraph (ReAct loop) |
| Visual UI | Langflow |
| Vector store / RAG | ChromaDB + nomic-embed-text |
| Input guardrail | Llama Guard 3 |
| PII redaction | Microsoft Presidio |
| Authorization | Human-in-the-Loop (HITL) |

---

## Prerequisites

| Requirement | Version | Notes |
|---|---|---|
| Python | 3.11+ | `python --version` |
| Ollama | 0.3.x+ | [ollama.com](https://ollama.com) |
| Git | Any recent | — |
| RAM | 16 GB min | 32 GB recommended |
| Storage | 25 GB free | 50 GB recommended |
| OS | macOS 13+ or Windows 11 | — |

**Required Ollama models** (pulled during setup):

```bash
ollama pull qwen2.5:7b         # Recommended reasoning model (~4.7 GB) — best tool-calling
ollama pull nomic-embed-text   # RAG embeddings (~274 MB)
ollama pull llama-guard3       # Input safety classifier (~6.0 GB)
ollama pull phi3:mini          # Fallback for low-VRAM / CPU-only machines (~2.3 GB)
# Optional alternative reasoning model:
ollama pull llama3.1:8b        # Works but has aggressive tool-calling behaviour
```

**API keys** (free tier, optional):
- [OpenWeatherMap](https://openweathermap.org/api) — `WEATHER_API_KEY`
- [Tavily](https://tavily.com) — `SEARCH_API_KEY` (DuckDuckGo used if absent)

---

## Setup — macOS (Apple Silicon)

```bash
# 1. Install Ollama via Homebrew
brew install ollama
ollama serve &

# 2. Pull required models
ollama pull qwen2.5:7b
ollama pull nomic-embed-text
ollama pull llama-guard3
ollama pull phi3:mini

# 3. Clone the repo
git clone https://github.com/omaha-lab/omaha-lab.git
cd omaha-lab

# 4. Create and activate virtual environment
python3.11 -m venv venv
source venv/bin/activate

# 5. Install dependencies
pip install -r requirements.txt

# 6. Configure environment
cp .env.example .env
# Edit .env and add your WEATHER_API_KEY and SEARCH_API_KEY
```

---

## Setup — Windows (Git Bash)

```bash
# 1. Install Ollama for Windows
# Download and run the installer from https://ollama.com/download/windows
# Then open Git Bash:
ollama serve &

# 2. Pull required models
ollama pull qwen2.5:7b
ollama pull nomic-embed-text
ollama pull llama-guard3
ollama pull phi3:mini

# 3. Clone the repo
git clone https://github.com/omaha-lab/omaha-lab.git
cd omaha-lab

# 4. Create and activate virtual environment
py -3.11 -m venv venv
source venv/Scripts/activate

# 5. Install dependencies
pip install -r requirements.txt

# 6. Configure environment
cp .env.example .env
# Edit .env and add your WEATHER_API_KEY and SEARCH_API_KEY
```

> **Low-VRAM / CPU-only machines:** Set `OLLAMA_MODEL=phi3:mini` in your `.env` file to use the lightweight fallback model.

---

## Quick Start

**Run your first agent in under 10 minutes:**

```bash
# Activate your virtual environment first
source venv/bin/activate          # macOS
source venv/Scripts/activate      # Windows Git Bash

# 1. Base agent (no guardrails, no RAG)
python agent.py

# 2. Secured agent (Llama Guard + Presidio + HITL)
python agent.py --guard on --hitl on

# 3. RAG-enabled persona agent
python agent.py --persona security_analyst --rag on

# 4. Full stack
python agent.py --persona hr_assistant --rag on --guard on --hitl on
```

**CLI flags:**

| Flag | Values | Default | Description |
|---|---|---|---|
| `--persona` | `customer_service`, `hr_assistant`, `security_analyst`, `code_assistant` | none | Load an agent persona |
| `--rag` | `on`, `off` | `off` | Enable RAG retrieval from `context_docs/` |
| `--guard` | `on`, `off` | `off` | Enable Llama Guard 3 input filtering |
| `--hitl` | `on`, `off` | `off` | Enable Human-in-the-Loop authorization |

---

## Lab Guide

The lab guide is organized into three modules:

| Module | Focus | Labs |
|---|---|---|
| [Module 1 — Foundations](labs/module1/) | Environment setup, first agent, personas, RAG | 1.1 – 1.5 |
| [Module 2 — Offensive Security](labs/module2/) | OWASP attack exercises (LLM01–LLM10) | 2.1 – 2.9 |
| [Module 3 — Defensive Architecture](labs/module3/) | Enable and validate each guardrail layer | 3.1 – 3.9 |

Start with **Lab 1.1 — Environment Setup**: [`labs/module1/lab1_1_environment_setup.md`](labs/module1/lab1_1_environment_setup.md)

---

## Contributing

See [CONTRIBUTING.md](.github/CONTRIBUTING.md) for pull request guidelines and issue triage policy.

## License

[MIT](LICENSE) © 2026 Omaha-Lab Contributors
