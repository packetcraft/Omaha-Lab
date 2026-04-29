# Lab 1.1 — Environment Setup

**Module:** 1 — Foundations
**Estimated time:** 20–30 minutes
**Prerequisite:** None — this is the starting point.

---

## Objective

Install all dependencies, pull the required Ollama models, and verify that the Omaha-Lab environment is ready to run on your machine (macOS or Windows with Git Bash).

---

## What You Will Need

| Requirement | Minimum version | Check command |
|---|---|---|
| Python | 3.11, 3.12, or 3.13 | `python --version` or `python3 --version` |
| Ollama | 0.3.x+ | `ollama --version` |
| Git | Any recent | `git --version` |
| RAM | 16 GB | — |
| Disk space | 25 GB free | — |

**Free API keys (optional but recommended for Lab 1.2):**
- [OpenWeatherMap](https://openweathermap.org/api) — free tier, 60 calls/min
- [Tavily](https://tavily.com) — free tier 1,000 searches/month (DuckDuckGo is used automatically if absent)

---

## Step 1: Install Ollama

### macOS

```bash
brew install ollama
```

After installation, start the Ollama daemon:

```bash
ollama serve &
```

Verify it is running:

```bash
curl http://localhost:11434/api/tags
```

Expected output: a JSON object with a `"models"` key (may be an empty list on first run).

### Windows (Git Bash)

Download the Ollama Windows installer from [ollama.com/download/windows](https://ollama.com/download/windows) and run it. Ollama runs as a background service automatically after installation.

Open Git Bash and verify:

```bash
curl http://localhost:11434/api/tags
```

Expected output: same JSON as above.

> **Note:** All remaining commands in this lab guide are written for bash syntax. On Windows, use Git Bash (not PowerShell or CMD).

---

## Step 2: Pull Required Models

Pull the three models used across all labs. This will take several minutes depending on your connection speed.

```bash
# Recommended reasoning model — best tool-calling discipline (~4.7 GB)
ollama pull qwen2.5:7b

# Embedding model for RAG (~274 MB)
ollama pull nomic-embed-text

# Safety classifier for Module 3 labs (~6.0 GB)
ollama pull llama-guard3
```

**Low-VRAM / CPU-only machines:** If `qwen2.5:7b` is too slow (>60 seconds per response), use the lightweight fallback:

```bash
ollama pull qwen2.5:1.5b
```

> **What about `llama3.1:8b`?** It works for conversational responses but its tool-calling
> fine-tune is over-eager — it will call `web_search` for greetings and simple knowledge
> questions. `qwen2.5:7b` has much better judgement about when to use tools.

Verify all models are available:

```bash
ollama list
```

Expected output (your versions may differ):

```
NAME                  ID              SIZE    MODIFIED
llama3.1:8b           91ab477bec9d    4.7 GB  ...
nomic-embed-text      0a109f422b47    274 MB  ...
llama-guard3          36a04e2bff6b    6.0 GB  ...
```

---

## Step 3: Clone the Repository

```bash
git clone https://github.com/omaha-lab/omaha-lab.git
cd omaha-lab
```

> If you received this project as a zip file or are working from a local copy, navigate to the project directory instead: `cd /path/to/omaha-lab`

---

## Step 4: Create a Python Virtual Environment

> **Python version requirement:** Use Python 3.11, 3.12, or 3.13. Python 3.14+ is not yet
> supported by all native dependencies (`pydantic-core`, `chromadb`). If your system default
> is 3.14, see the note below.

### macOS

```bash
python3.12 -m venv venv    # or python3.11 / python3.13
source venv/bin/activate
```

### Windows (Git Bash)

Check which Python versions are installed:

```bash
py --list
```

Create the venv with a supported version:

```bash
py -3.12 -m venv venv      # or py -3.11 / py -3.13
source venv/Scripts/activate
```

Verify the right version is active before installing:

```bash
python --version   # must show 3.11.x, 3.12.x, or 3.13.x
```

> If Python 3.12 (or 3.11/3.13) is not listed by `py --list`, download the installer
> from [python.org/downloads](https://www.python.org/downloads/) before continuing.

Your prompt should now show `(venv)` as a prefix. **All remaining lab commands assume the virtual environment is active.** If you open a new terminal, re-run the activation command above before continuing.

---

## Step 5: Install Python Dependencies

```bash
pip install -r requirements.txt
```

This installs all pinned dependencies including LangGraph, LangChain, ChromaDB, Presidio, and the Ollama Python client. The install takes 2–5 minutes.

Verify key packages:

```bash
pip show langgraph langchain-ollama chromadb | grep -E "^(Name|Version)"
```

---

## Step 6: Configure Environment Variables

Copy the example environment file and fill in your API keys:

```bash
cp .env.example .env
```

Open `.env` in a text editor and set:

```
OLLAMA_BASE_URL=http://localhost:11434
OLLAMA_MODEL=qwen2.5:7b

WEATHER_API_KEY=your_openweathermap_key_here
SEARCH_API_KEY=your_tavily_key_here
```

> If you do not have an OpenWeatherMap key, leave `WEATHER_API_KEY` blank. Weather lookups will return an error message, but all other functionality will work. DuckDuckGo search requires no key and works automatically.

**Low-VRAM machines:** Set `OLLAMA_MODEL=qwen2.5:1.5b` to use the lightweight fallback.

---

## Step 7: Verify the Setup

Run the built-in Ollama connectivity check:

```bash
python -c "
import requests
resp = requests.get('http://localhost:11434/api/tags', timeout=5)
models = [m['name'] for m in resp.json().get('models', [])]
print('Ollama is running.')
print('Available models:', ', '.join(models))
"
```

Then confirm the project structure looks correct:

```bash
ls -1
```

Expected files at the root level:

```
agent.py
graph.py
state.py
requirements.txt
README.md
LICENSE
.env
.env.example
.gitignore
pyproject.toml
```

And the key directories:

```
context_docs/   guardrails/   labs/   personas/   rag/   tools/   workspace/
```

---

## Step 8: Smoke Test

Run the agent with no arguments to confirm everything is wired up:

```bash
python agent.py --help
```

Expected output:

```
usage: agent.py [-h] [--model MODEL] [--base-url BASE_URL] [--persona NAME]
                [--rag {on,off}] [--list-personas]

Omaha-Lab ReAct agent — local LLM security sandbox
...
```

If you see this output, your environment is ready. Proceed to **Lab 1.2**.

---

## Troubleshooting

| Symptom | Likely cause | Fix |
|---|---|---|
| `Error: cannot reach Ollama` | Ollama daemon not running | Run `ollama serve` in a separate terminal |
| `ModuleNotFoundError` | venv not activated | Run `source venv/bin/activate` (or `Scripts/activate` on Windows) |
| `Warning: model 'llama3.1:8b' not found` | Model not yet pulled | Run `ollama pull llama3.1:8b` |
| `pip install` fails on `presidio-*` | Missing build tools | Install `build-essential` (Linux) or Xcode CLI tools (macOS) |
| Slow responses (>60s per turn) | 8B model too large for your hardware | Set `OLLAMA_MODEL=qwen2.5:1.5b` in `.env` |
| `pydantic-core` build fails with "version (3.14) is newer than PyO3's maximum" | venv created with Python 3.14 | Recreate venv: `rm -rf venv && py -3.12 -m venv venv` |

---

## Discussion Questions

1. Why does Omaha-Lab run all inference locally rather than calling a cloud LLM API? What privacy and security properties does this provide — and what does it give up?

2. Ollama exposes an unauthenticated HTTP API on `localhost:11434` by default. What would happen if an attacker on the same machine could reach that port? How would you mitigate this in a production deployment?

3. You pulled `llama-guard3` in Step 2 even though it isn't used until Module 3. What does it mean to trust a model pulled from a public registry? What supply chain risks exist? (This connects to OWASP LLM03, covered in Lab 3.8.)

---

**Next lab:** [Lab 1.2 — Your First Tool-Calling Agent](lab1_2_first_agent.md)
