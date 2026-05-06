# Product Requirements Document: Omaha-Lab (V4)

**Subtitle:** A hands-on lab guide for local LLM security, agentic tool-calling, and OWASP mitigation.
**Version:** 4.4
**Status:** Draft
**Last Updated:** 2026-04-29

---

## 1. Executive Summary

**Omaha-Lab** (Ollama + Mac/Windows + Human + Agent) is a research and development environment designed to explore the intersection of autonomous agent reasoning and cybersecurity guardrails. Operating on local hardware with optional internet access for live tool-calling (weather, search, APIs), the system provides a sandbox for testing LLM tool-calling capabilities, Human-in-the-Loop (HITL) authorization patterns, and multi-layer security architectures.

The platform serves two primary audiences: security practitioners who want a realistic agentic testbed, and learners who want a structured, hands-on path through the OWASP Top 10 for LLM Applications. Realism is achieved through swappable agent personas and Markdown-based RAG context documents that simulate enterprise deployments under attack.

---

## 2. Objectives & Scope

### 2.1 Primary Objectives

- Demonstrate how agentic AI can be safely integrated into enterprise workflows using a low-code, high-visibility platform.
- Provide a structured lab guide covering the full OWASP Top 10 for LLM Applications (2025/2026) through both offensive simulation and defensive mitigation exercises.
- Publish as a reproducible, open-source project on GitHub targeting both macOS (Apple Silicon) and Windows (Git Bash) environments.

### 2.2 In Scope

- Local LLM inference via Ollama
- Agentic orchestration via LangGraph (ReAct loop with tool calling)
- Live internet-connected tools: web search, weather API, REST endpoints
- Visual flow design via Langflow
- Optional browser chat UI via Chainlit (renders agent steps visually; wraps existing CLI agent)
- Security guardrails: Llama Guard 3, Microsoft Presidio, canary token detection, HITL breakpoints
- Swappable agent personas (system prompt templates)
- RAG pipeline using local Markdown documents as context
- Lab guide (3 modules, 10 OWASP risk labs)

### 2.3 Out of Scope

- Cloud-hosted inference (no OpenAI, Anthropic, or Bedrock endpoints)
- Cloud-hosted or mobile browser deployments (Chainlit UI runs on localhost only)
- Production hardening or enterprise SSO integration

---

## 3. System Architecture

| Layer | Component | Technical Specification |
|---|---|---|
| Inference | LLM Engine | Ollama (Metal / CUDA / CPU) |
| Reasoning | Default Model | Qwen 2.5 1.5B (CPU-friendly, supports tool calling) |
| Reasoning | Full-power Option | Qwen 2.5 7B (stronger reasoning, requires ~8 GB VRAM) |
| Reasoning | Dedicated Reason Node | Text-only LLM call before tool dispatch — surfaces explicit [REASON] step, solving Qwen 2.5's text/tool-call separation |
| Orchestration | State Machine | LangGraph (Python 3.11+) |
| Persona | Agent Identity | YAML persona configs; system prompt template loader |
| Context / RAG | Document Store | Markdown files → ChromaDB (local vector store) |
| Context / RAG | Embeddings | `nomic-embed-text` via Ollama (fully local) |
| Tool Calling | External APIs | Weather API, Search API, custom Python tools |
| Security | Input Guardrail (fast) | Regex pre-filter — keyword/pattern matching for prompt injection (S15) |
| Security | Input Guardrail (LLM) | Llama Guard 3 — content safety classifier (S1–S14) |
| Security | PII Redaction | Microsoft Presidio |
| Security | Output Validation | Canary token detection, output schema enforcement |
| Security | Authorization | Human-in-the-Loop (HITL) interrupt node |
| Interface | Visual Flow Builder | Langflow with embeddable chat widget |
| Interface | Web Chat UI (optional) | Chainlit — chat-native, renders guardrail/tool/HITL steps as browser cards; includes colour-coded Mermaid pipeline diagram (topology at session start + per-turn path highlight) |
| Observability | Pipeline Trace Viewer (optional) | Arize Phoenix — local OpenTelemetry span tree; captures input/output at every LangGraph node; toggled via `--observe on` |

### 3.1 Minimum Hardware Requirements

| Spec | Minimum | Recommended |
|---|---|---|
| RAM | 16 GB | 32 GB |
| VRAM (GPU) | 0 GB (CPU mode) | 8 GB (for 8B model) |
| Storage | 25 GB free | 50 GB free |
| OS | macOS 13+ or Windows 11 | Same |

---

## 4. Deployment Requirements

### 4.1 Cross-Platform Setup

The workbench must provide parity across both macOS and Windows environments.

**macOS (Apple Silicon):**
- Ollama installed via Homebrew
- Python 3.11+ virtual environment (`venv`)
- Metal GPU acceleration enabled by default

**Windows (Git Bash):**
- Ollama for Windows installer
- Python virtual environment created and activated within Git Bash
- CUDA acceleration if NVIDIA GPU present; otherwise CPU mode
- Git Bash used as the primary shell throughout all lab instructions

### 4.2 Model Strategy

`qwen2.5:1.5b` is the default model — it runs on CPU-only machines and supports the Ollama tools API, making it the baseline for all labs. Users with ~8 GB of VRAM can set `OLLAMA_MODEL=qwen2.5:7b` for stronger reasoning. Both models are from the same Qwen 2.5 family and produce consistent tool-calling behaviour. `phi3:mini` is not a valid alternative as it does not support tool calling (returns HTTP 400). Any lab that requires noticeably better reasoning quality should note "7B recommended" but must not require it.

---

## 5. Open-Source Publication Requirements

### 5.1 Repository Structure

```
omaha-lab/
├── README.md                   # Setup guide (macOS + Windows)
├── FOUNDATIONS.md              # Conceptual framework: LLM architecture analogy + 5-stage evolution roadmap
├── LICENSE                     # MIT License
├── requirements.txt            # Pinned Python dependencies
├── pyproject.toml              # Optional: modern dependency spec
├── .env.example                # API key template (gitignored actual .env)
├── .gitignore
├── .github/
│   ├── CONTRIBUTING.md
│   └── ISSUE_TEMPLATE/
│       ├── bug_report.md
│       ├── lab_feedback.md
│       └── feature_request.md
├── flows/                      # Langflow JSON exports
│   ├── base_agent.json
│   ├── secured_agent.json
│   ├── rag_agent.json
│   └── persona_agent.json
├── labs/                       # Lab guide markdown files
│   ├── module1/
│   ├── module2/
│   └── module3/
├── personas/                   # Agent persona YAML configs
│   ├── customer_service.yaml
│   ├── hr_assistant.yaml
│   ├── security_analyst.yaml
│   └── code_assistant.yaml
├── context_docs/               # Markdown files used as RAG context
│   ├── company_policy.md
│   ├── employee_handbook.md
│   ├── threat_intel_report.md
│   └── poisoned_policy.md      # Used in LLM08 lab (contains injection payload)
├── tools/                      # Python tool implementations
│   ├── weather.py
│   ├── search.py
│   ├── http_request.py
│   └── file_ops.py
├── ui.py                       # Optional: Chainlit web chat UI (wraps agent.py pipeline)
└── guardrails/                 # Llama Guard and Presidio configs
    ├── llama_guard_config.py
    └── presidio_config.py
```

### 5.2 README Requirements

- Step-by-step setup for macOS and Windows (Git Bash), clearly separated
- Model download commands (`ollama pull qwen2.5:7b`, `ollama pull nomic-embed-text`, `ollama pull llama-guard3`, `ollama pull qwen2.5:1.5b` for low-VRAM fallback)
- API key setup instructions for weather and search tool integrations
- Quick-start: "run your first agent in under 10 minutes"

### 5.3 Licensing & Contribution

- License: **MIT**
- Contributions accepted via pull request; issues triaged within 7 days (aspiration)
- Issue templates for: bug report, lab feedback, feature request

---

## 6. Functional Requirements

### 6.1 Agentic Logic & Tool Calling

- **ReAct Loop:** LangGraph state machine with a dedicated **Reason Node** (LLM call, tools disabled) that runs before the **Agent Node** (LLM + tool registry). The Reason Node produces an explicit `[REASON]` thought that is injected into the Agent Node's context, solving the Qwen 2.5 limitation where text and tool calls cannot coexist in a single response. After a tool executes, the Agent Node produces the final `[RESPOND]` without re-running reasoning. Full cycle: Reason → Act → Observe → Respond.
- **Tool Registry:** Modular Python tool definitions callable by the agent
- **Live Tools (internet-connected):**
  - Web search (DuckDuckGo or Tavily API)
  - Weather lookup (OpenWeatherMap API)
  - HTTP request tool for generic REST endpoint calls
- **Local Tools:**
  - File read/write (sandboxed to a `/workspace` directory)
  - Calculator / code interpreter (restricted execution environment)

### 6.2 Agent Personas

The system must support swappable agent personas that define the model's identity, tone, and scope via system prompt templates.

**Pre-built Personas:**

| Persona | Role Description | Primary Lab Use |
|---|---|---|
| **Customer Service Bot** | Retail assistant; never discusses competitors or internal systems | LLM01 direct injection, LLM07 prompt leakage |
| **HR Assistant** | HR helper with access to simulated employee records | LLM02 PII disclosure, LLM06 excessive agency |
| **Security Analyst** | SOC analyst summarizing threat intel from retrieved documents | LLM01 indirect injection via RAG, LLM08 RAG poisoning |
| **Code Assistant** | Coding helper that can explain and run code snippets | LLM05 improper output handling, LLM03 supply chain |

**Implementation Requirements:**
- Each persona defined as a YAML file in `personas/` with fields: `name`, `system_prompt`, `allowed_tools`, `risk_level`
- Persona loaded at agent startup via CLI flag (`--persona customer_service`) or Langflow dropdown
- System prompt injected as the first message in the LangGraph state before any user input
- Persona selection logged for audit purposes

### 6.3 RAG Pipeline (Markdown Context Documents)

The system must support retrieval-augmented generation using local Markdown files as the knowledge base.

**Pipeline:**
1. At startup, `.md` files in `context_docs/` are chunked and embedded using `nomic-embed-text` (via Ollama)
2. Embeddings stored in a local ChromaDB database (persisted to disk, not rebuilt each run)
3. On each user query, top-K relevant chunks retrieved and prepended to the LLM context window
4. Retrieval step sits between input guardrail and LLM reasoning node in the LangGraph graph

**Context Documents (pre-built for labs):**

| File | Content | Lab Use |
|---|---|---|
| `company_policy.md` | Fictional corporate policy document | Grounding, LLM04 few-shot poisoning |
| `employee_handbook.md` | Fictional HR handbook with fake PII entries | LLM02 disclosure via retrieval |
| `threat_intel_report.md` | Fictional SOC threat report | LLM09 misinformation grounding |
| `poisoned_policy.md` | Policy doc with embedded injection payload | LLM08 RAG poisoning lab |

**Implementation Requirements:**
- ChromaDB collection rebuilt only when source `.md` files change (hash-checked)
- `nomic-embed-text` model pulled automatically if not present
- Retrieval is toggled on/off via CLI flag (`--rag on/off`) or Langflow switch
- Retrieved chunks displayed in agent trace output for transparency

### 6.4 Security & Guardrails

- **Input Filtering:** User inputs pass through two sequential layers before reaching the reasoning model. First, a regex pre-filter checks for known prompt injection patterns (instruction overrides, role-play escapes, system prompt extraction attempts) and blocks matches instantly as category S15, with no LLM inference cost. Inputs that pass the regex are then evaluated by Llama Guard 3 against its standard S1–S14 content safety categories. Blocked inputs are logged to `logs/blocked_inputs.jsonl` with timestamp, category, and layer attribution.
- **PII Redaction:** Microsoft Presidio scrubs names, emails, phone numbers, SSNs, and credit card patterns from both inputs and outputs in real time.
- **Canary Token Detection:** Post-processing step checks model outputs for embedded tracking strings before delivery to the user.
- **Output Schema Enforcement:** Structured tool call outputs validated against expected JSON schema before execution.
- **HITL Authorization:** Any tool execution classified as high-risk (file write, HTTP POST, delete operations) requires explicit human approval before proceeding.

### 6.5 Success Criteria

| Requirement | Acceptance Threshold |
|---|---|
| Regex pre-filter blocks explicit prompt injection | 100% detection of patterns in `_INJECTION_PATTERNS` (zero LLM cost) |
| Llama Guard blocks unsafe content | ≥ 90% detection on standard S1–S14 content corpus |
| Presidio PII redaction | 100% of seeded PII patterns removed before output |
| HITL trigger rate | 100% of high-risk tool calls intercepted |
| RAG retrieval relevance | Correct chunk retrieved in top-3 results for all lab queries |
| Poisoned doc injection detected | Llama Guard catches payload in retrieved chunk ≥ 80% of runs |
| Agent completes weather query | End-to-end in < 15 seconds on minimum hardware (CPU mode) |
| Lab reproducibility | All 3 modules complete without error on fresh macOS and Windows installs |

---

## 7. OWASP Top 10 for LLM Applications — Coverage Plan

| # | Risk | Lab Feasibility | Offensive Exercise | Defensive Mitigation | Architecture Component |
|---|---|---|---|---|---|
| LLM01 | Prompt Injection | **High** | Direct injection via chat; indirect injection via poisoned tool response or RAG chunk | Regex pre-filter (explicit overrides), Llama Guard 3 (content safety), system prompt hardening | Regex pre-filter, Llama Guard 3, LangGraph system prompt |
| LLM02 | Sensitive Information Disclosure | **High** | Embed PII in prompts or RAG docs; extract via role-play or retrieval | Presidio PII redaction on inputs, outputs, and retrieved chunks | Microsoft Presidio |
| LLM03 | Supply Chain Vulnerabilities | **Medium** | Discuss risks of pulling unverified Ollama models; inspect model provenance | Model verification checklist; known-good Modelfile hashes | Ollama model pull process (documented) |
| LLM04 | Data and Model Poisoning | **Medium** | Override system prompt via adversarial few-shot examples in RAG context | Prompt structure isolation, guardrail on injected context | LangGraph system prompt, Llama Guard 3, RAG chunk filtering |
| LLM05 | Improper Output Handling | **High** | Generate outputs containing script tags, shell commands, or malformed JSON | Output schema validation, canary token detection, output escaping | Canary token post-processor, Pydantic schema enforcement |
| LLM06 | Excessive Agency | **High** | Trigger agent to perform unauthorized file writes or external POSTs | HITL breakpoint for high-risk tools, tool permission scoping per persona | LangGraph HITL interrupt node, persona `allowed_tools` config |
| LLM07 | System Prompt Leakage | **High** | Attempt to extract system prompt via adversarial questioning against a persona | Prompt confidentiality instructions, Llama Guard detection | System prompt design, Llama Guard 3 |
| LLM08 | Vector and Embedding Weaknesses | **High** | Inject a poisoned `.md` document into the RAG store; observe payload execution | Guardrail on retrieved chunks before injection into context; source trust scoring | Llama Guard 3 on retrieved content, ChromaDB source metadata |
| LLM09 | Misinformation | **Medium** | Ask verifiable factual questions without RAG; observe hallucinations. Then enable RAG. | Grounding via retrieved `.md` context and live web search; compare outputs | Web search tool + RAG retrieval, ReAct observe step |
| LLM10 | Unbounded Consumption | **High** | Craft recursive tool-call loops or excessive token requests | LangGraph step limit, token budget enforcement, rate limiting | LangGraph `max_iterations` config |

---

## 8. Lab Guide Framework

**Title:** *Intro to LLM and LLM Security*

**Prerequisite reading:** [`FOUNDATIONS.md`](FOUNDATIONS.md) — establishes the CPU/OS/Harness architectural analogy and the 5-stage agent evolution roadmap. All three modules assume this mental model. Learners should read it before Lab 1.1.

### Module 1: Foundations

**Goal:** Get the environment running and understand how agents reason, use tools, adopt personas, and retrieve context.

**Learning Objectives:**
- Install Ollama and pull required models on macOS or Windows (Git Bash)
- Run a basic LangGraph ReAct agent that calls a live weather tool
- Load a persona and observe how the system prompt changes agent behavior
- Enable RAG and see how retrieved Markdown context influences responses
- Understand the full flow: user input → guardrail → retrieval → persona → model → tool → output
- Use Phoenix to see the raw input/output data flowing through every pipeline node
- Use the Chainlit Mermaid diagram to read pipeline topology and per-turn execution path at a glance

**Labs:**
- Lab 1.1 — Environment Setup (macOS or Windows)
- Lab 1.2 — Your First Tool-Calling Agent
- Lab 1.3 — Reading the ReAct Trace
- Lab 1.4 — Loading a Persona (Customer Service Bot)
- Lab 1.5 — Enabling RAG with a Markdown Context Document
- Lab 1.6 — Visualizing the Agent Pipeline with Phoenix
- Lab 1.7 — Reading the Pipeline Diagram in Chainlit

---

### Module 2: Offensive Security

**Goal:** Think like an attacker. Exploit common LLM vulnerabilities against realistic persona-driven agents with RAG context.

**Learning Objectives:**
- Craft direct and indirect prompt injection payloads (LLM01)
- Extract simulated PII from unguarded models and RAG documents (LLM02)
- Leak a persona's system prompt through adversarial questioning (LLM07)
- Force an agent to exceed its authorized tool permissions (LLM06)
- Poison a RAG document and observe payload retrieval and execution (LLM08)
- Generate dangerous outputs through improper output handling (LLM05)
- Trigger recursive consumption loops (LLM10)

**Labs:**

| Lab | OWASP Risk | Target Persona | Attack Vector |
|---|---|---|---|
| Lab 2.1 — Direct Prompt Injection | LLM01 | Customer Service Bot | Chat input |
| Lab 2.2 — Indirect Injection via Tool Response | LLM01 | Security Analyst | Poisoned web search result |
| Lab 2.3 — Indirect Injection via RAG Document | LLM01 + LLM08 | Security Analyst | Poisoned `.md` file in vector store |
| Lab 2.4 — PII Extraction Attack | LLM02 | HR Assistant | Chat role-play + RAG employee handbook |
| Lab 2.5 — System Prompt Leakage | LLM07 | Customer Service Bot | Adversarial questioning |
| Lab 2.6 — Excessive Agency: Unauthorized File Write | LLM06 | HR Assistant | Tool manipulation |
| Lab 2.7 — Improper Output Handling | LLM05 | Code Assistant | Malicious code output payload |
| Lab 2.8 — RAG Poisoning and Embedding Attack | LLM08 | Security Analyst | `poisoned_policy.md` injection |
| Lab 2.9 — Unbounded Consumption Loop | LLM10 | Any | Recursive tool-call payload |

**Persona note:** Learner acts as a red-team tester. Each lab specifies which persona to load and what document context (if any) should be active. No prior exploitation experience required.

---

### Module 3: Defensive Architecture

**Goal:** Layer defenses. Rebuild the secured agent and observe which Module 2 attacks are now blocked.

**Learning Objectives:**
- Enable Llama Guard 3 on both chat inputs and RAG-retrieved chunks (LLM01, LLM08)
- Add Presidio PII redaction across inputs, retrieved context, and outputs (LLM02)
- Implement HITL and confirm high-risk tool calls require approval (LLM06)
- Configure output schema validation and canary token detection (LLM05)
- Scope tool permissions per persona via `allowed_tools` config (LLM06)
- Set LangGraph iteration limits to kill runaway loops (LLM10)
- Discuss supply chain hygiene for Ollama models (LLM03)
- Compare hallucination rate with and without RAG grounding (LLM09)

**Labs:**
- Lab 3.1 — Enabling Llama Guard 3 on Inputs
- Lab 3.2 — Applying Llama Guard 3 to Retrieved RAG Chunks
- Lab 3.3 — PII Redaction with Microsoft Presidio
- Lab 3.4 — HITL Authorization Breakpoint
- Lab 3.5 — Output Validation and Canary Tokens
- Lab 3.6 — Scoping Tool Permissions per Persona
- Lab 3.7 — Iteration Limits and Rate Control
- Lab 3.8 — Supply Chain Hygiene: Verifying Ollama Models
- Lab 3.9 — Grounding with RAG and Search: Reducing Misinformation

---

## 9. Non-Functional Requirements

| Category | Requirement |
|---|---|
| **Connectivity** | Internet access is permitted and required for live tool-calling labs (weather, search). All inference and embedding remain local. |
| **Privacy** | No user data, prompts, tool call results, or RAG content is transmitted to cloud LLM providers. |
| **Python Version** | Python 3.11 or higher. All dependencies pinned in `requirements.txt`. |
| **Ollama Version** | Ollama 0.3.x or higher. Minimum version documented in README. |
| **Langflow Version** | Langflow 1.x. Exported `.json` flows include the version they were built on. |
| **Chainlit Version** | Chainlit 1.x. UI is optional; CLI path remains fully functional without it. |
| **Phoenix Version** | Arize Phoenix 15.x. Observability is optional; all labs function without it. Phoenix runs fully locally — no data is transmitted to Arize cloud. Toggled via `--observe on/off` (default off). |
| **Execution Environment** | macOS 13+ (Apple Silicon preferred) or Windows 11 with Git Bash. Intel Mac and Windows ARM not formally tested. |
| **API Keys** | Weather and search integrations require free-tier API keys. Keys stored in `.env` (gitignored). `.env.example` provided. |
| **Performance** | Agent round-trip (prompt → retrieval → tool call → response) must complete in < 15 seconds on minimum hardware in CPU mode. |
| **RAG Rebuild** | ChromaDB collection rebuilds only when source `.md` files change (hash-checked on startup). Cold build of all 4 context docs < 60 seconds. |
| **Reproducibility** | A clean install on a supported platform must reach a working agent in < 30 minutes following the README. |

---

## 10. User Personas

| Persona | Profile | Primary Interaction |
|---|---|---|
| **Research Architect** | Security engineer or AI practitioner exploring guardrail design | LangGraph backend, direct Python scripting, custom tool and persona authoring |
| **Learner / Student** | Developer or analyst new to LLM security; follows structured labs | Lab guide (Module 1–3), Langflow visual canvas, chat interface |
| **Open Source Contributor** | GitHub-native developer interested in extending the project | Repository, issues, pull requests, CONTRIBUTING.md |

---

## 11. Development Stages (Coding Agent Handoff)

Each stage is designed as a discrete, self-contained unit that can be handed to a coding agent independently. Stages within the same phase can be parallelized; stages across phases must be completed in order.

---

### Phase 1 — Project Foundation

**Stage 1: Repository Scaffold**

> **Prompt a coding agent:** "Create the Omaha-Lab project scaffold. Set up the directory structure exactly as specified in Section 5.1 of the PRD. Create: `requirements.txt` (with placeholder deps for langgraph, langchain, chromadb, presidio-analyzer, presidio-anonymizer, ollama, python-dotenv, pydantic, requests), `.env.example` with keys for `WEATHER_API_KEY`, `SEARCH_API_KEY`, `OLLAMA_BASE_URL`, `.gitignore` excluding `.env`, `__pycache__`, `.chroma`, `venv/`. Create stub `README.md` with sections: Overview, Prerequisites, Setup (macOS), Setup (Windows/Git Bash), Quick Start, Lab Guide. MIT `LICENSE` file. No implementation code yet — structure and config only."

**Deliverables:** Directory tree, `requirements.txt`, `.env.example`, `.gitignore`, stub `README.md`, `LICENSE`
**Depends on:** Nothing

---

### Phase 2 — Core Agent

**Stage 2: Base ReAct Agent**

> **Prompt a coding agent:** "Build the base LangGraph ReAct agent for Omaha-Lab. Use Ollama as the LLM backend (model configurable via env var `OLLAMA_MODEL`, default `qwen2.5:1.5b`). The agent should implement a standard ReAct loop: receive user message → reason → optionally call a tool → observe result → respond. No tools yet — tool registry should exist but be empty. The agent should run from CLI: `python agent.py`. Print the full ReAct trace to stdout on each turn. Validate it works with both `qwen2.5:1.5b` (default) and `qwen2.5:7b` (full-power). Do not use `phi3:mini` — it does not support the tools API."

**Deliverables:** `agent.py`, `graph.py` (LangGraph state machine), `state.py` (AgentState schema)
**Depends on:** Stage 1

---

### Phase 3 — Tools

**Stage 3: Tool Registry + Live Tools**

> **Prompt a coding agent:** "Add tool calling to the Omaha-Lab agent. Implement a tool registry pattern where tools are Python functions decorated with `@tool` (LangChain tool decorator). Build these tools in `tools/`: (1) `weather.py` — OpenWeatherMap current weather by city name, API key from `.env`; (2) `search.py` — DuckDuckGo web search using `duckduckgo-search` library, no API key required; (3) `http_request.py` — generic HTTP GET tool with URL allow-list validation; (4) `file_ops.py` — read and write files sandboxed to `./workspace/` directory only. Register all tools with the LangGraph agent. Test each tool works end-to-end."

**Deliverables:** `tools/weather.py`, `tools/search.py`, `tools/http_request.py`, `tools/file_ops.py`, updated `agent.py`
**Depends on:** Stage 2

---

### Phase 4 — Persona Engine

**Stage 4: Persona System**

> **Prompt a coding agent:** "Build the persona system for Omaha-Lab. Each persona is a YAML file in `personas/` with fields: `name` (str), `description` (str), `system_prompt` (str, multi-line), `allowed_tools` (list of tool names), `risk_level` (low/medium/high). Create the 4 personas defined in PRD Section 6.2: customer_service, hr_assistant, security_analyst, code_assistant. Build a `PersonaLoader` class in `personas/loader.py` that reads a YAML file, validates fields with Pydantic, and returns a `Persona` object. Inject the system prompt as the first `SystemMessage` in the LangGraph state. Enforce `allowed_tools` by filtering the tool registry at agent startup. Add `--persona <name>` CLI argument to `agent.py`."

**Deliverables:** `personas/*.yaml` (4 files), `personas/loader.py`, `personas/schema.py`, updated `agent.py`
**Depends on:** Stage 3

---

### Phase 5 — RAG Pipeline

**Stage 5: Markdown RAG Context**

> **Prompt a coding agent:** "Add a RAG pipeline to the Omaha-Lab agent using local Markdown files as the knowledge base. Requirements: (1) Use `nomic-embed-text` model via Ollama for embeddings (fully local). (2) Use ChromaDB as the vector store, persisted to `.chroma/` directory. (3) On startup, check if source `.md` files in `context_docs/` have changed (MD5 hash stored in `.chroma/manifest.json`). Rebuild only changed collections. (4) Add a retrieval node in the LangGraph graph that runs after input guardrail and before the LLM reasoning node. Retrieve top-3 relevant chunks and prepend to the LLM context as a `SystemMessage`. (5) Add `--rag on/off` CLI flag (default off). (6) Print retrieved chunks and their source file in the trace output. Create the 4 context documents in `context_docs/` with realistic fictional content as described in PRD Section 6.3. Include `poisoned_policy.md` with an embedded indirect prompt injection payload for Lab 2.8."

**Deliverables:** `rag/embedder.py`, `rag/retriever.py`, `rag/graph_node.py`, `context_docs/*.md` (4 files), updated `graph.py`
**Depends on:** Stage 4

---

### Phase 6 — Security Guardrails

**Stage 6: Input Guardrail (Regex Pre-filter + Llama Guard 3)**

> **Prompt a coding agent:** "Implement the two-layer input filtering node for Omaha-Lab. Build `guardrails/llama_guard.py` with a `check_input(text: str) -> GuardResult` method that first runs a regex pre-filter against known prompt injection patterns (instruction overrides, role-play escapes, system prompt extraction attempts) — returning category S15 on match with `raw_response='injection-prefilter'` and no LLM call. If the regex passes, forward the text to Llama Guard 3 via Ollama (model: `llama-guard3`) for S1–S14 content safety classification. `GuardResult` has fields: `safe` (bool), `category` (str or None), `raw_response` (str). Add this as the first node in the LangGraph graph — before retrieval and before the LLM. If `safe=False`, short-circuit the graph: return a blocked message to the user (with layer attribution — `regex-prefilter` or `llama-guard3`) and log the attempt to `logs/blocked_inputs.jsonl` with timestamp, category, and truncated input. The guard must also be callable on RAG-retrieved chunks (same function, called in the retrieval node after fetch, before context injection). Add `--guard on/off` CLI flag (default off for Stage 6, so earlier stages still work)."

**Deliverables:** `guardrails/llama_guard.py`, `guardrails/guard_result.py`, updated `graph.py`, `logs/` directory with `.gitkeep`
**Depends on:** Stage 5

**Stage 7: Output Guardrails (Presidio + Canary + Schema)**

> **Prompt a coding agent:** "Implement the three output guardrails for Omaha-Lab: (1) **Presidio PII Redaction** in `guardrails/presidio_guard.py` — use `presidio-analyzer` and `presidio-anonymizer` to scrub names, emails, phone numbers, SSNs, and credit card numbers from LLM output text. Replace detected entities with type labels like `[PERSON]`, `[PHONE_NUMBER]`. (2) **Canary Token Detection** in `guardrails/canary.py` — maintain a registry of canary strings (loaded from `guardrails/canary_tokens.txt`, one per line). Scan every output for canary string presence. If found, log the event to `logs/canary_alerts.jsonl` and append a warning to the user-visible response. (3) **Output Schema Enforcement** in `guardrails/schema_guard.py` — for tool call results, validate the JSON payload against a Pydantic schema before the agent processes it. Invalid schemas are rejected and logged. Wire all three as a post-processing pipeline node in LangGraph, after the LLM response and before delivery to the user."

**Deliverables:** `guardrails/presidio_guard.py`, `guardrails/canary.py`, `guardrails/canary_tokens.txt`, `guardrails/schema_guard.py`, updated `graph.py`
**Depends on:** Stage 6

---

### Phase 7 — HITL Authorization

**Stage 8: Human-in-the-Loop**

> **Prompt a coding agent:** "Implement the HITL (Human-in-the-Loop) authorization node for Omaha-Lab. High-risk tool calls must pause for human approval before execution. (1) Define a `RISK_LEVEL` dict in `tools/risk_registry.py` mapping each tool action to low/high: file write = high, HTTP POST = high, file read = low, weather = low, search = low. (2) Add a `hitl_node` in LangGraph that intercepts tool calls classified as high-risk before they execute. Display the proposed tool name and arguments to the user and prompt: `[HITL] Approve this action? (yes/no):`. (3) If approved, proceed. If denied, skip the tool call and return a message explaining the action was blocked by the user. (4) Log all HITL decisions (approved and denied) to `logs/hitl_log.jsonl` with timestamp, tool name, arguments, and decision. Add `--hitl on/off` CLI flag (default off)."

**Deliverables:** `tools/risk_registry.py`, `graph_nodes/hitl_node.py`, updated `graph.py`, updated `logs/`
**Depends on:** Stage 7

---

### Phase 8 — Langflow Flows

**Stage 9: Langflow Visual Flows**

> **Prompt a coding agent:** "Create four Langflow JSON flow exports in the `flows/` directory. Each flow should visually represent the corresponding agent configuration: (1) `base_agent.json` — Ollama LLM + tool calling only, no guardrails; (2) `secured_agent.json` — adds Llama Guard input node, Presidio output node, HITL node; (3) `rag_agent.json` — adds ChromaDB retriever, nomic-embed-text embedder, context injection; (4) `persona_agent.json` — adds system prompt template node with persona selector dropdown. Use Langflow 1.x component schema. Add a `flows/README.md` explaining how to import each flow into Langflow and what it demonstrates."

**Deliverables:** `flows/*.json` (4 files), `flows/README.md`
**Depends on:** Stage 8

---

### Phase 9 — Lab Content & Publication

**Stage 10: Lab Markdown Files**

> **Prompt a coding agent:** "Write the lab guide Markdown files for Omaha-Lab. Create one `.md` file per lab in `labs/module1/`, `labs/module2/`, `labs/module3/`. Each lab file must follow this structure: (1) Title and OWASP risk reference; (2) Objective (1–2 sentences); (3) Persona and context doc to load (if applicable); (4) Step-by-step instructions with exact CLI commands; (5) Expected output / what to look for; (6) Discussion questions. Use the labs defined in PRD Section 8. Module 2 labs must include the specific attack payload the learner should try. Module 3 labs must reference the exact config flag or code change that enables the defense."

**Deliverables:** `labs/module1/*.md`, `labs/module2/*.md`, `labs/module3/*.md`
**Depends on:** Stage 9

**Stage 11: Final README and GitHub Publication Prep**

> **Prompt a coding agent:** "Complete the Omaha-Lab README.md and GitHub publication files. README must include: (1) Project overview and architecture diagram (ASCII); (2) Prerequisites list with versions; (3) Full setup for macOS (Homebrew, venv, model pulls); (4) Full setup for Windows Git Bash (Ollama installer, venv in bash, model pulls); (5) Quick-start commands to run the base agent, secured agent, and a RAG-enabled persona agent; (6) Table of all CLI flags; (7) Link to lab guide. Also complete: `CONTRIBUTING.md` with PR and issue guidelines; `.github/ISSUE_TEMPLATE/` with the three templates (bug report, lab feedback, feature request). Verify `.env.example` includes all required keys."

**Deliverables:** Final `README.md`, `CONTRIBUTING.md`, `.github/ISSUE_TEMPLATE/*.md`, verified `.env.example`
**Depends on:** Stage 10

---

### Phase 10 — Web UI (Optional)

**Stage 12: Chainlit Web Chat UI**

> **Prompt a coding agent:** See `PLAN_ui_chainlit.md` for full implementation brief and coding agent prompt.

**Deliverables:** `ui.py`, `.chainlit/config.toml`, updated `requirements.txt`, updated `README.md` (Web UI section), updated `chainlit.md` (in-app welcome screen with lab index)
**Depends on:** Stage 11

**Web UI design (implemented):**

The Chainlit UI exposes the four CLI configurations as **Lab Mode profiles** (selected before the first message) and as individually overridable **Chat Settings** (sidebar gear icon):

| Lab Mode profile | Presets | CLI equivalent |
|---|---|---|
| Bare | guard off · RAG off · HITL off | `python agent.py` |
| Guarded | guard on · HITL on | `python agent.py --guard on --hitl on` |
| RAG Analyst | RAG on · security_analyst persona | `python agent.py --persona security_analyst --rag on` |
| Full Defense | all on · hr_assistant persona | `python agent.py --persona hr_assistant --rag on --guard on --hitl on` |

Chat Settings widgets (sidebar gear): **Persona** (Select), **Guard** (Switch), **RAG** (Switch), **HITL** (Switch). Profiles initialize all four widgets; any widget change triggers a full agent rebuild using the current widget values — profile presets are not re-applied on settings updates.

---

### Phase 11 — Reasoning Architecture

**Stage 13: Dedicated Reason Node**

> **What was built:** Qwen 2.5 (and most local models) enforce a strict separation between text responses and tool calls — a single LLM turn can produce one or the other, but not both. This means any "Thought:" the model produces always appears *after* observing a tool result, not *before* deciding which tool to call. The dedicated Reason Node solves this architecturally.

**Implementation:**
- A `reason_node` is added to the LangGraph graph that calls the LLM with **no tools bound** and a reasoning-focused system prompt. It runs before `agent_node` on every new user turn.
- The model is forced into a text-only response, producing a step-by-step thought stored in `AgentState.reasoning`.
- `agent_node` injects the stored reasoning as a `SystemMessage` ("Your prior reasoning: …") before calling the tool-capable LLM, then clears the field.
- `tools → agent_node` edges bypass `reason_node` — post-observation synthesis does not re-reason.
- Full trace: `[REASON]` → `[ACT]` → `[OBSERVE]` → `[RESPOND]`

**Graph wiring:**
- Entry path: `reason → agent` (no guard/RAG), or `guard_input → reason → agent`, or `rag → reason → agent`
- Loop path: `tools → agent` (reason bypassed for the synthesis turn)

**`AgentState` change:** Added `reasoning: str` field.

**Display:** Both CLI (`_print_event`) and web UI (`_handle_event`) render the reason node output as `[REASON]` / "Reasoning" step card before any tool call.

**Deliverables:** Updated `state.py`, `graph.py`, `agent.py`, `ui.py`
**Depends on:** Stage 12

---

### Phase 12 — Observability (optional, additive)

**Stage 14: Phoenix Pipeline Trace Viewer**

> **What was built:** Students following the CLI trace (`[REASON]`, `[ACT]`, `[OBSERVE]`, `[RESPOND]`) can see the flow but not the raw data at each node. Phoenix adds a local OpenTelemetry span tree that captures the exact input and output of every LangGraph node — giving students two complementary views: flow topology (CLI) and data trace (Phoenix UI).

**Implementation:**
- `arize-phoenix`, `arize-phoenix-otel`, `openinference-instrumentation-langchain`, and supporting OTel packages added to the optional section of `requirements.txt` at exact pinned versions.
- `_setup_phoenix()` helper added to `agent.py`: checks that a Phoenix server is reachable at `http://127.0.0.1:6006` (exits with a clear fix instruction if not), registers an OTel `TracerProvider` via `phoenix.otel.register(project_name="omaha-lab")`, and instruments all LangChain/LangGraph calls with `LangChainInstrumentor().instrument()`. Returns the UI URL.
- `--observe on/off` CLI flag added to `agent.py` (default `off`). When `on`, `_setup_phoenix()` is called before Ollama startup and the returned URL is shown in the startup banner (`Observe: on → http://127.0.0.1:6006`).
- Phoenix must be started as a **separate persistent server** before running agent.py: `python -m phoenix.server.main serve`. This keeps traces from all agent sessions — traces are not lost when agent.py exits and restarts.
- No changes to `graph.py` — `LangChainInstrumentor` auto-instruments all downstream LangChain calls.
- Phoenix stores traces locally in `~/.phoenix/` (SQLite). No data is transmitted to Arize cloud.

**Known dependency note:** Phoenix pulls in several `opentelemetry-instrumentation-*` packages at version `0.62b1` (urllib3, redis, requests, etc.) that conflict with `opentelemetry-semantic-conventions 0.60b1` already present in the environment. Pip reports these as warnings during install. They do not affect the LangGraph tracing path and can be safely ignored. Documented in `requirements.txt` and `labs/module1/lab1_6_visualizing_the_pipeline.md`.

**Lab added:** `labs/module1/lab1_6_visualizing_the_pipeline.md` — 9-step walkthrough: install verification, start Phoenix server (persistent, dedicated terminal), open UI, run agent as client, read a tool-call trace, read a blocked guard trace, read a RAG retrieval trace, compare traces across sessions, and understand what Phoenix does not capture. Includes a comparison table of what Phoenix shows vs. what the `logs/` JSONL files cover.

**Deliverables:** Updated `requirements.txt`, updated `agent.py` (`_setup_phoenix`, `--observe` flag, banner line), `labs/module1/lab1_6_visualizing_the_pipeline.md`, updated `README.md` (CLI flags table)
**Depends on:** Stage 13

---

### Phase 13 — Chainlit Pipeline Diagram (optional, additive)

**Stage 15: Mermaid Pipeline Diagram in Chainlit UI**

> **What was built:** The Chainlit web UI now renders a colour-coded Mermaid `graph LR` flowchart at two moments: (1) at session start, showing the configured pipeline topology (all nodes blue); (2) after every turn, as a collapsible "Pipeline path" step showing which nodes actually fired (green = fired, blue = configured but idle, red = guard blocked with short-circuit path). This is Option D from DECISIONS.md D-02 — complementary to Phoenix (Option A) at a different level of abstraction: topology and path, not raw data.

**Implementation:**
- `_pipeline_mermaid(use_rag, use_guard, use_hitl, fired, guard_blocked)` added to `ui.py`: generates a Mermaid `graph LR` string. Declares only nodes relevant to the current path (guard-blocked traces omit downstream nodes cleanly). Uses `classDef` for colour coding.
- `_build_session()`: added `"use_rag"` to returned session dict (was missing, required for diagram generation).
- `_init_session()`: sends a static topology `cl.Message` after the "Ready" confirmation.
- `on_message()`: accumulates `fired_nodes` set and `guard_blocked` flag from raw LangGraph events each turn; sends `_pipeline_mermaid()` output as a collapsible `cl.Step` after the agent response. No changes to `_handle_event()`.
- No new dependencies — Chainlit renders Mermaid natively in markdown.

**Lab added:** `labs/module1/lab1_7_chainlit_pipeline_diagram.md` — introduces Chainlit as a distinct interface from the CLI; walks students through reading the topology card, the per-turn path step, and how the diagram changes across the four lab profiles and a blocked guard input.

**Deliverables:** Updated `ui.py`, `labs/module1/lab1_7_chainlit_pipeline_diagram.md`, updated `README.md` (Web UI section), updated `PRD_Omaha-Lab.md`
**Depends on:** Stage 12 (Chainlit web UI)

---

### Development Stage Summary

```
Phase 1: Foundation
  └─ Stage 1: Project Scaffold

Phase 2: Core Agent
  └─ Stage 2: Base ReAct Agent

Phase 3: Tools
  └─ Stage 3: Tool Registry + Live Tools

Phase 4: Persona Engine
  └─ Stage 4: Persona System

Phase 5: RAG
  └─ Stage 5: Markdown RAG Pipeline

Phase 6: Security (can run Stages 6 & 7 sequentially)
  ├─ Stage 6: Input Guardrail (Llama Guard 3)
  └─ Stage 7: Output Guardrails (Presidio + Canary + Schema)

Phase 7: HITL
  └─ Stage 8: Human-in-the-Loop

Phase 8: UI
  └─ Stage 9: Langflow Visual Flows

Phase 9: Content & Publish (can run Stages 10 & 11 in parallel)
  ├─ Stage 10: Lab Markdown Files
  └─ Stage 11: README + GitHub Publication Prep

Phase 10: Web UI (optional, additive)
  └─ Stage 12: Chainlit Web Chat UI

Phase 11: Reasoning Architecture (additive, no breaking changes)
  └─ Stage 13: Dedicated Reason Node

Phase 12: Observability (optional, additive)
  └─ Stage 14: Phoenix Pipeline Trace Viewer
```

---

## 12. Tooling Decisions

Architectural and tooling alternatives that were evaluated but not adopted — including the reasoning behind each choice — are documented in [`DECISIONS.md`](DECISIONS.md). Refer to that file when a tooling question arises (e.g., "why not n8n?", "why not LangGraph Studio for visualization?") rather than re-litigating decisions in issues or PRs.

---

## 13. Glossary

| Term | Definition |
|---|---|
| **Ollama** | Open-source tool for running LLMs locally on consumer hardware |
| **LangGraph** | Python library for building stateful, multi-step agentic workflows as directed graphs |
| **Langflow** | Visual, low-code builder for LLM pipelines; exports flows as JSON |
| **Chainlit** | Python framework for building chat UIs for LLM apps; renders agentic steps (tool calls, guardrail decisions, HITL prompts) as collapsible browser cards |
| **ReAct Loop** | Reasoning + Action pattern: the model reasons about a goal, calls a tool, observes the result, and repeats |
| **HITL** | Human-in-the-Loop: a mandatory pause in agent execution requiring a human to approve before a high-risk action proceeds |
| **Persona** | A YAML-defined agent identity that sets the system prompt, allowed tools, and risk posture for a conversation |
| **RAG** | Retrieval-Augmented Generation: enriching LLM context with chunks retrieved from a document store before generating a response |
| **ChromaDB** | Open-source, locally-hosted vector database used to store and query document embeddings |
| **nomic-embed-text** | A local embedding model available via Ollama used to convert text chunks into vectors for RAG |
| **Regex Pre-filter** | A fast, pattern-based input guard that matches known prompt injection signatures (instruction overrides, role-play escapes) before any LLM inference. Blocks as category S15 with zero model-inference cost. |
| **Llama Guard 3** | A fine-tuned classifier model from Meta that detects unsafe or policy-violating content in LLM inputs and outputs across categories S1–S14. Does not natively detect prompt injection, which is why the regex pre-filter runs first. |
| **Microsoft Presidio** | Open-source library for detecting and anonymizing PII (Personally Identifiable Information) in text |
| **Canary Token** | A unique, trackable string embedded in data; its appearance in model output signals a data-leakage or injection event |
| **PII** | Personally Identifiable Information — data that can identify a specific individual (name, SSN, email, etc.) |
| **OWASP LLM Top 10** | Open Worldwide Application Security Project list of the 10 most critical security risks for LLM-based applications |
| **Prompt Injection** | An attack where adversarial text in the input (or retrieved context) manipulates the model into ignoring its instructions |
| **Excessive Agency** | An LLM risk where an agent takes actions beyond what was authorized, often due to overpermissioned tools |
| **Vector Store** | A database optimized for storing high-dimensional embedding vectors and performing similarity search |
| **Indirect Injection** | A prompt injection attack delivered through a secondary channel (retrieved document, tool response) rather than direct user input |
