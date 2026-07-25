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

### Option C — Multipass VM (Apple Silicon: app runtime in a VM, Ollama on the Mac)

Runs Chainlit, LangGraph, Phoenix, and the rest of the app runtime inside an Ubuntu (arm64) [Multipass](https://multipass.run) VM, while Ollama keeps running natively on the Mac host for Metal (GPU) acceleration. The VM reaches Ollama over Multipass's **default network**, via the gateway address back to the host — no bridged networking or interface names to configure.

```
 macOS host                          Ubuntu VM (Multipass, arm64)
┌───────────────┐   gateway route   ┌─────────────────────────────────────┐
│    Ollama      │◄──────────────────│  Chainlit  (:8000) — web UI          │
│   (:11434)     │                   │    • LangGraph  — agent orchestration│
└───────────────┘                   │    • ChromaDB   — embedded RAG store │
                                      │  Phoenix   (:6006) — OTEL tracing    │
                                      └─────────────────────────────────────┘
```

LangGraph and ChromaDB aren't separate services — they run in-process inside the Chainlit app, so only Chainlit and Phoenix get their own port/box.

**Requires:** macOS on Apple Silicon (M1/M2/M3+) and Multipass (`brew install --cask multipass`).

**1. Launch the VM** (default networking — no `--network` flag needed):

```bash
multipass launch --name omaha-lab --cpus 4 --memory 8G --disk 25G
```

Multipass automatically pulls the arm64 Ubuntu image on Apple Silicon hosts.

**2. Expose Ollama beyond localhost** (run on the Mac):

- **Ollama desktop app (easiest):** Settings → "Expose Ollama to the network" — persists across restarts, no command needed.
- **CLI/service**, only if nothing already owns port 11434:
  ```bash
  OLLAMA_HOST=0.0.0.0:11434 ollama serve
  ```
  ("address already in use" means the desktop app or a background service already owns the port — use its toggle instead of fighting it.)

Accept the macOS Firewall prompt the first time the VM connects.

**3. Find the VM's gateway** (its view of the host) and verify it can reach Ollama:

```bash
multipass exec omaha-lab -- ip route show default
# note the address after "via", then:
multipass exec omaha-lab -- curl -s http://<gateway-ip>:11434/api/tags
```

A JSON model list back confirms the VM can reach Ollama — fix networking here before moving on if it doesn't.

**4. Pull models on the host** (this is where Ollama actually runs):

```bash
ollama pull qwen2.5:1.5b
ollama pull nomic-embed-text
ollama pull llama-guard3
```

**5. Shell in, install system deps, and clone the repo:**

```bash
multipass shell omaha-lab

# Current Ubuntu releases (24.04+) dropped python3.11 from the default repos —
# the deadsnakes PPA still packages it:
sudo add-apt-repository -y ppa:deadsnakes/ppa && sudo apt update
sudo apt install -y python3.11 python3.11-venv git build-essential
git clone https://github.com/omaha-lab/omaha-lab.git
cd omaha-lab
```

**6. Point the app at the host's Ollama:**

```bash
cp .env.example .env
# edit .env: OLLAMA_BASE_URL=http://<gateway-ip-from-step-3>:11434
```

**7. Install and run:**

```bash
make install   # venv + all deps + spacy model — models were already pulled in step 4
make run       # or run-secure / run-rag / run-full
make dev       # Chainlit + Phoenix together, one terminal — reachable at http://<vm-ip>:8000 / :6006
```

Get the VM's IP with `multipass info omaha-lab`; the host reaches it directly over Multipass's own network, no port mapping needed.

Notes:

- Don't run `make models` inside the VM — it shells out to the `ollama` CLI, which isn't installed there. Models are pulled on the host in step 4; the VM only ever calls Ollama's HTTP API.
- The gateway address from step 3 is Multipass-managed, not the Mac's LAN IP — it stays valid across Wi-Fi/network changes, though host VPN software that reroutes all traffic can still interfere.
- Stop or remove the VM with `multipass stop omaha-lab` / `multipass delete omaha-lab --purge`.

**Whichever option you used (A, B, or C), running the lab from here is identical** — the CLI (below), [Web UI](#web-ui-optional) (`make ui`, or `make dev` for Chainlit + Phoenix together), and [Observability](#observability--llm-traces-optional) sections all apply regardless of how you installed it.

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

> **Want Phoenix tracing running alongside it?** `make dev` boots Chainlit *and* Phoenix together in a single terminal (via [honcho](https://github.com/nickstenning/honcho) reading `./Procfile`), instead of the two dedicated terminals below.

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

(Or run `make dev` instead of `make ui` + `make phoenix` separately — see [Web UI](#web-ui-optional) above.)

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
