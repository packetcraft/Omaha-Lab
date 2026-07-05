# Omaha-Lab

**A hands-on lab guide for local LLM security, agentic tool-calling, and OWASP mitigation.**

Omaha-Lab (**O**llama + **M**ac/Windows + **H**uman + **A**gent) is a local-first environment for exploring autonomous agent reasoning and security guardrails. All inference runs on your hardware — no cloud LLM endpoints.

---

## Prerequisites

| Requirement | Version | Notes |
|---|---|---|
| Python | **3.11** | `python3.11 --version` |
| Ollama | 0.3.x+ | [ollama.com](https://ollama.com) |
| Git | Any recent | — |
| RAM | 16 GB min | 32 GB recommended |
| Storage | 25 GB free | 50 GB recommended |
| OS | macOS 13+ or Windows 11 | — |

**Optional API keys** (free tier — DuckDuckGo is used if absent):
- [OpenWeatherMap](https://openweathermap.org/api) — `WEATHER_API_KEY`
- [Tavily](https://tavily.com) — `SEARCH_API_KEY`

---

## Setup

### Option A — one command (recommended)

```bash
git clone https://github.com/omaha-lab/omaha-lab.git
cd omaha-lab
make install   # venv + all deps (core, UI, observability) + spacy model + .env
make models    # pulls ~7 GB of Ollama models — grab a coffee
```

> **macOS:** `make` requires Xcode Command Line Tools — run `xcode-select --install` first.  
> **Windows (Git Bash):** install `make` via `winget install GnuWin32.Make` or `choco install make`, then restart Git Bash.

### Option B — manual steps

```bash
# 1. Clone
git clone https://github.com/omaha-lab/omaha-lab.git
cd omaha-lab

# 2. Create venv (Python 3.11 required)
python3.11 -m venv venv          # macOS
py -3.11    -m venv venv          # Windows Git Bash

# 3. Install dependencies (core + Web UI + observability — all pinned in requirements.txt)
venv/bin/pip install -r requirements.txt                              # macOS
venv/Scripts/pip install -r requirements.txt                          # Windows

# 4. Download spacy model
venv/bin/python -m spacy download en_core_web_lg    # macOS
venv/Scripts/python -m spacy download en_core_web_lg # Windows

# 5. Pull Ollama models (~7 GB total)
ollama pull qwen2.5:1.5b       # default model, CPU-friendly
ollama pull nomic-embed-text   # RAG embeddings
ollama pull llama-guard3       # input safety classifier

# 6. Configure environment
cp .env.example .env           # then add your API keys
```

> **Higher-end machines:** set `OLLAMA_MODEL=qwen2.5:7b` in `.env` for stronger reasoning (~8 GB VRAM required).

### Option C — Docker (no local Python 3.11 needed)

Build the whole lab environment — venv, deps, spacy model — *inside* a container, while Ollama keeps running natively on the host for GPU access:

```bash
git clone https://github.com/omaha-lab/omaha-lab.git
cd omaha-lab
docker-compose up -d --build
docker exec -it omaha-lab-coding-agent bash

# now inside the container:
cd /workspace
make install   # venv + all deps + spacy model + .env — runs against Debian/Linux, not Windows/macOS
make models    # pulls ~7 GB of Ollama models onto the HOST via host.docker.internal
```

See [Running Inside Docker](#running-inside-docker-ollama-stays-on-the-host) below for the full walkthrough, port mappings, and troubleshooting.

### Running Inside Docker (Ollama stays on the host)

A ready-to-use `Dockerfile` and `docker-compose.yml` are included in the repo root (adapted from the `docker-coding-agents` project). The container gets Python 3.11, Node.js, `git`, `gh`, and Claude Code preinstalled; the project directory is bind-mounted in rather than baked into the image, so `venv/`, `.chroma/`, and `.env` persist across rebuilds; and Ollama itself keeps running natively on the host, so it keeps native GPU access with no NVIDIA Container Toolkit passthrough required.

```yaml
services:
  coding-agent:
    build: .
    container_name: omaha-lab-coding-agent
    volumes:
      - .:/workspace
      - ~/.gitconfig:/root/.gitconfig:ro
      - ~/.config/gh:/root/.config/gh
    environment:
      - OLLAMA_BASE_URL=http://host.docker.internal:11434
      - OPENAI_API_BASE=http://host.docker.internal:11434/v1
    extra_hosts:
      - "host.docker.internal:host-gateway"
    ports:
      - "8000:8000"  # Chainlit UI — started via `make ui`
      - "6006:6006"  # Phoenix — started via `make phoenix`
    stdin_open: true
    tty: true
```

**1. Build the image and start the container:**

```bash
docker-compose up -d --build
```

**2. Attach a shell:**

```bash
docker exec -it omaha-lab-coding-agent bash
```

**3. Run the normal setup and lab commands from inside the container** — the `Makefile`'s OS check falls through to its Linux branch (`python3.11 -m venv venv`, `venv/bin/python`) automatically, since `make` (via `build-essential`) and `python3.11` are already on the image:

```bash
cd /workspace
make install
make models
make run           # or run-secure / run-rag / run-full
```

**4. Chainlit and Phoenix run as separate long-lived processes**, typically in two different `docker exec` sessions attached to the same container, which is why both ports are published up front in the compose file rather than added later:

```bash
# session A
docker exec -it omaha-lab-coding-agent bash -c "cd /workspace && make ui"        # http://localhost:8000

# session B
docker exec -it omaha-lab-coding-agent bash -c "cd /workspace && make phoenix"   # http://127.0.0.1:6006
```

**5. Rebuild after Dockerfile changes:**

```bash
docker-compose down && docker-compose up -d --build
```

Notes:

- You do **not** need to edit `.env`'s `OLLAMA_BASE_URL` for Docker — `load_dotenv()` (used in `agent.py`, `ui.py`, `bench.py`) never overrides an already-set environment variable, and `docker-compose.yml` already injects `OLLAMA_BASE_URL=http://host.docker.internal:11434` as a container env var. You still need `.env` for `WEATHER_API_KEY` / `SEARCH_API_KEY` if you use those — run `cp .env.example .env` inside the container (or on the host, since it's bind-mounted) and fill them in.
- `host.docker.internal` is provided automatically by Docker Desktop; the compose file's `extra_hosts: host.docker.internal:host-gateway` covers plain Docker Engine under WSL2 too.
- If the container still can't reach Ollama, set `OLLAMA_HOST=0.0.0.0` as a host environment variable for the Ollama service and restart it, so it listens on all interfaces instead of only `127.0.0.1`.

---

## Quick Start

```bash
make run           # base agent — no guardrails, no RAG
make run-secure    # Llama Guard + Presidio + HITL
make run-rag       # RAG analyst — security_analyst persona + retrieval
make run-full      # full defense stack — all layers on
```

Or call the CLI directly for custom combinations:

```bash
# 1. Baseline — observe raw agent traffic, no defenses
#    Labs: 1.3 Reading the ReAct Trace · 1.6 Visualizing the Agent Pipeline with Phoenix
venv/bin/python agent.py --persona customer_service --observe on

# 2. RAG only — watch retrieval traces in Phoenix
#    Labs: 1.5 Enabling RAG with a Markdown Context Document · 4.3 RAG Pipeline Internals
venv/bin/python agent.py --persona security_analyst --rag on --observe on

# 3. Guard only — see Llama Guard blocks + Presidio redactions in traces
#    Labs: 3.1 Enabling Llama Guard 3 on Inputs · 3.3 PII Redaction with Microsoft Presidio
venv/bin/python agent.py --persona hr_assistant --guard on --observe on

# 4. RAG + Guard — retrieval with safety filter; compare latency vs. option 2
#    Labs: 3.2 Applying Llama Guard 3 to Retrieved RAG Chunks · 3.9 Grounding with RAG and Search
venv/bin/python agent.py --persona code_assistant --rag on --guard on --observe on

# 5. Full stack — all layers on; use as the hardened baseline for evaluation
#    Labs: 3.4 HITL Authorization Breakpoint · 3.10 Measuring Guard Coverage with the Evaluation Harness
venv/bin/python agent.py --persona hr_assistant --rag on --guard on --hitl on --observe on
```

**CLI flags:**

| Flag | Values | Default | Description |
|---|---|---|---|
| `--persona` | `customer_service`, `hr_assistant`, `security_analyst`, `code_assistant` | none | Load an agent persona |
| `--rag` | `on` / `off` | `off` | Enable RAG retrieval from `context_docs/` |
| `--guard` | `on` / `off` | `off` | Enable Llama Guard 3 input filter + Presidio output redaction |
| `--hitl` | `on` / `off` | `off` | Enable Human-in-the-Loop authorization for high-risk tool calls |
| `--max-iterations` | integer | `10` | Hard cap on agent steps — stops runaway tool loops |
| `--observe` | `on` / `off` | `off` | Stream traces to a running Phoenix server at `http://127.0.0.1:6006` |

---

## Web UI (Optional)

A browser-based chat interface that renders each pipeline layer as collapsible step cards.

```bash
make ui    # opens http://localhost:8000
```

Select a **Lab Mode** from the profile picker:

| Lab Mode | Active layers | CLI equivalent |
|---|---|---|
| **Bare** | None | `python agent.py` |
| **Guarded** | Llama Guard 3 · Presidio · HITL | `python agent.py --guard on --hitl on` |
| **RAG Analyst** | RAG · Security Analyst persona | `python agent.py --persona security_analyst --rag on` |
| **Full Defense** | All layers | `python agent.py --persona hr_assistant --rag on --guard on --hitl on` |

The sidebar gear icon lets you toggle individual layers mid-session without restarting. A colour-coded pipeline diagram (🟢 fired · 🔵 idle · 🔴 blocked) updates after every message. See [Lab 1.7](labs/module1/lab1_7_chainlit_pipeline_diagram.md).

---

## Observability / LLM Traces (Optional)

[Arize Phoenix](https://phoenix.arize.com) captures the full input/output at every pipeline node with token-level detail.

Start Phoenix in a **dedicated terminal** and leave it running:

```bash
make phoenix    # opens http://127.0.0.1:6006
```

Then run the agent with the observe flag:

```bash
venv/bin/python agent.py --observe on
# or add --observe on to any make run-* command via the CLI directly
```

| What Phoenix shows | Where to look |
|---|---|
| Input / output at every LLM node | Span detail → Input messages / Output tabs |
| Tool call arguments and results | `get_weather`, `web_search` spans |
| Guard short-circuit (blocked input) | Trace ends after `guard_input` span |
| RAG retrieved chunks | `rag` span → Output tab |
| Token counts and latency per node | Span header |

Traces persist in `~/.phoenix/` across restarts. If Phoenix is already running when you launch `make ui`, the Chainlit UI connects automatically — no extra flags needed. See [Lab 1.6](labs/module1/lab1_6_visualizing_the_pipeline.md).

---

## Pipeline Architecture

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
                       │ thought injected into context
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
                       │ approved → Tool executes
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

| Layer | Technology |
|---|---|
| Local LLM inference | Ollama (Metal / CUDA / CPU) |
| Default model | Qwen 2.5 1.5B — CPU-friendly, supports tool calling |
| Full-power option | Qwen 2.5 7B — stronger reasoning, ~8 GB VRAM |
| Agent orchestration | LangGraph (ReAct loop) |
| Vector store / RAG | ChromaDB + nomic-embed-text |
| Input guardrail | Regex pre-filter + Llama Guard 3 |
| PII redaction | Microsoft Presidio |
| Authorization | Human-in-the-Loop (HITL) |

---

## Lab Guide

> **Before you begin:** Read [`FOUNDATIONS.md`](FOUNDATIONS.md). It establishes the CPU/OS/Harness mental model that every lab builds on.

| Module | Focus | Labs |
|---|---|---|
| [Module 1 — Foundations](labs/module1/) | Environment, first agent, personas, RAG, Phoenix, Chainlit | 1.1 – 1.7 |
| [Module 2 — Offensive Security](labs/module2/) | OWASP LLM01–LLM10 attack exercises | 2.1 – 2.9 |
| [Module 3 — Defensive Architecture](labs/module3/) | Enable and validate each guardrail layer; measure coverage | 3.1 – 3.10 |
| [Module 4 — Architecture Deep Dive](labs/module4/) | Read and modify the core code — LangGraph, tools, RAG, guardrails | 4.1 – 4.5 |

Start here: [`labs/module1/lab1_1_environment_setup.md`](labs/module1/lab1_1_environment_setup.md)

---

## Development

```bash
make test          # 107 tests, no live Ollama required
make bench-regex   # evaluation harness — regex pre-filter only, instant
make bench         # evaluation harness — full guard stack (needs llama-guard3)
```

---

## Contributing

See [CONTRIBUTING.md](.github/CONTRIBUTING.md) for pull request guidelines and issue triage policy.

## License

[MIT](LICENSE) © 2026 Omaha-Lab Contributors
