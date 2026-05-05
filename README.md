# Omaha-Lab

**A hands-on lab guide for local LLM security, agentic tool-calling, and OWASP mitigation.**

Omaha-Lab (**O**llama + **M**ac/Windows + **H**uman + **A**gent) is a local-first research and development environment for exploring autonomous agent reasoning and cybersecurity guardrails. All inference stays on your hardware — no cloud LLM endpoints.

```
User Input
    │
    ▼
┌─────────────────────────────────────────────────────────┐
│  Regex Pre-filter  (S15: Prompt Injection patterns)     │
└──────────────────────┬──────────────────────────────────┘
                       │ no match
                       ▼
┌─────────────────────────────────────────────────────────┐
│  Llama Guard 3  (Input Guardrail — S1–S14)              │
└──────────────────────┬──────────────────────────────────┘
                       │ safe
                       ▼
┌─────────────────────────────────────────────────────────┐
│  RAG Retrieval  (ChromaDB + nomic-embed-text)           │
└──────────────────────┬──────────────────────────────────┘
                       │ top-3 chunks
                       ▼
┌─────────────────────────────────────────────────────────┐
│  Reason Node  (LLM, tools disabled)                     │
│    [REASON] step-by-step thought before any tool call   │
└──────────────────────┬──────────────────────────────────┘
                       │ Thought injected into context
                       ▼
┌─────────────────────────────────────────────────────────┐
│  Agent Node  (LLM + tool registry)                      │
│    [ACT] tool call  ─or─  [RESPOND] final answer        │
└──────────────────────┬──────────────────────────────────┘
                       │ high-risk tool?
                       ▼
┌─────────────────────────────────────────────────────────┐
│  HITL Authorization  (human approve/deny)               │
└──────────────────────┬──────────────────────────────────┘
                       │ approved → Tool executes → [OBSERVE]
                       │           └─ result fed back to Agent Node
                       ▼
┌─────────────────────────────────────────────────────────┐
│  Output Guardrails                                      │
│    Presidio PII Redaction                               │
│    Canary Token Detection                               │
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
| Default model | Qwen 2.5 1.5B (CPU-friendly, supports tool calling) |
| Full-power option | Qwen 2.5 7B (stronger reasoning, requires ~8 GB VRAM) |
| Pre-tool reasoning | Dedicated Reason Node (LLM, tools disabled — explicit [REASON] step) |
| Agent orchestration | LangGraph (ReAct loop) |
| Visual UI | Langflow |
| Vector store / RAG | ChromaDB + nomic-embed-text |
| Input guardrail | Regex pre-filter (S15) + Llama Guard 3 (S1–S14) |
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
ollama pull qwen2.5:1.5b       # Default model (~1.0 GB) — runs on CPU-only machines, supports tools
ollama pull nomic-embed-text   # RAG embeddings (~274 MB)
ollama pull llama-guard3       # Input safety classifier (~6.0 GB)
# Optional — stronger reasoning if VRAM allows:
ollama pull qwen2.5:7b         # Full-power option (~4.7 GB, requires ~8 GB VRAM)
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
ollama pull qwen2.5:1.5b
ollama pull nomic-embed-text
ollama pull llama-guard3
# optional: ollama pull qwen2.5:7b

# 3. Clone the repo
git clone https://github.com/omaha-lab/omaha-lab.git
cd omaha-lab

# 4. Create virtual environment
python3.11 -m venv venv

# 5. Install dependencies using the venv's pip directly (no activation needed).
# This ensures the correct Python 3.11 wheel is fetched rather than a
# cached wheel built for a different Python version on your PATH.
venv/bin/pip install -r requirements.txt
venv/bin/python -m spacy download en_core_web_lg

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
ollama pull qwen2.5:1.5b
ollama pull nomic-embed-text
ollama pull llama-guard3
# optional: ollama pull qwen2.5:7b

# 3. Clone the repo
git clone https://github.com/omaha-lab/omaha-lab.git
cd omaha-lab

# 4. Create virtual environment
py -3.11 -m venv venv

# 5. Install dependencies using the venv's pip directly (no activation needed).
# This ensures the correct Python 3.11 wheel is fetched rather than a
# cached wheel built for a different Python version on your PATH.
venv/Scripts/pip install -r requirements.txt
venv/Scripts/python -m spacy download en_core_web_lg

# 6. Configure environment
cp .env.example .env
# Edit .env and add your WEATHER_API_KEY and SEARCH_API_KEY
```

> **Higher-end machines:** Set `OLLAMA_MODEL=qwen2.5:7b` in your `.env` file for stronger reasoning if you have ~8 GB of VRAM available.

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
| `--guard` | `on`, `off` | `off` | Enable regex pre-filter + Llama Guard 3 input filtering + Presidio output redaction |
| `--hitl` | `on`, `off` | `off` | Enable Human-in-the-Loop authorization |

---

## Web UI (Optional)

A browser-based chat interface is available alongside the CLI. It renders each pipeline layer
(input guard, RAG retrieval, tool calls, HITL approval, output guard) as collapsible step cards
in the browser. All CLI labs continue to work unchanged.

```bash
pip install chainlit          # one additional package

chainlit run ui.py            # opens http://localhost:8000
```

Select a **Lab Mode** from the profile picker before your first message:

| Lab Mode | Active layers | CLI equivalent |
|---|---|---|
| **Bare** | None — attack surface open | `python agent.py` |
| **Guarded** | Llama Guard 3 · Presidio · HITL | `python agent.py --guard on --hitl on` |
| **RAG Analyst** | RAG · Security Analyst persona | `python agent.py --persona security_analyst --rag on` |
| **Full Defense** | RAG · Llama Guard 3 · Presidio · HITL | `python agent.py --persona hr_assistant --rag on --guard on --hitl on` |

The sidebar gear icon exposes individual **Chat Settings** — Persona, Guard, RAG, and HITL — so any custom combination can be composed without touching the CLI. Profiles initialize all four controls; changing any toggle mid-session rebuilds the agent immediately.

---

## Lab Guide

> **Before you begin:** Read [`FOUNDATIONS.md`](FOUNDATIONS.md) first. It establishes the CPU/OS/Harness mental model and the 5-stage agent evolution roadmap that every lab is built around. Each lab targets a specific architectural layer — knowing the map makes the attacks and defenses land.

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
