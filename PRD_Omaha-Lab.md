# Product Requirements Document: Omaha-Lab (V4)

**Subtitle:** A hands-on lab guide for local LLM security, agentic tool-calling, and OWASP mitigation.
**Version:** 4.2
**Status:** Draft
**Last Updated:** 2026-04-23

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
- Security guardrails: Llama Guard 3, Microsoft Presidio, canary token detection, HITL breakpoints
- Swappable agent personas (system prompt templates)
- RAG pipeline using local Markdown documents as context
- Lab guide (3 modules, 10 OWASP risk labs)

### 2.3 Out of Scope

- Cloud-hosted inference (no OpenAI, Anthropic, or Bedrock endpoints)
- Mobile or browser-native deployments
- Production hardening or enterprise SSO integration

---

## 3. System Architecture

| Layer | Component | Technical Specification |
|---|---|---|
| Inference | LLM Engine | Ollama (Metal / CUDA / CPU) |
| Reasoning | Core Model | Llama 3.1 8B (default) or 70B (high-resource) |
| Fallback Model | Lightweight Option | Phi-3 Mini 3.8B (low-VRAM / CPU-only machines) |
| Orchestration | State Machine | LangGraph (Python 3.11+) |
| Persona | Agent Identity | YAML persona configs; system prompt template loader |
| Context / RAG | Document Store | Markdown files → ChromaDB (local vector store) |
| Context / RAG | Embeddings | `nomic-embed-text` via Ollama (fully local) |
| Tool Calling | External APIs | Weather API, Search API, custom Python tools |
| Security | Input Guardrail | Llama Guard 3 |
| Security | PII Redaction | Microsoft Presidio |
| Security | Output Validation | Canary token detection, output schema enforcement |
| Security | Authorization | Human-in-the-Loop (HITL) interrupt node |
| Interface | Visual UI | Langflow with embeddable chat widget |

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

### 4.2 Model Fallback Strategy

Users whose hardware cannot run Llama 3.1 8B at acceptable speed should be directed to `phi3:mini` via Ollama. All lab exercises must be validated against both models. Any lab that only functions on 8B+ must be clearly marked.

---

## 5. Open-Source Publication Requirements

### 5.1 Repository Structure

```
omaha-lab/
├── README.md                   # Setup guide (macOS + Windows)
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
└── guardrails/                 # Llama Guard and Presidio configs
    ├── llama_guard_config.py
    └── presidio_config.py
```

### 5.2 README Requirements

- Step-by-step setup for macOS and Windows (Git Bash), clearly separated
- Model download commands (`ollama pull llama3.1:8b`, `ollama pull nomic-embed-text`, `ollama pull phi3:mini`)
- API key setup instructions for weather and search tool integrations
- Quick-start: "run your first agent in under 10 minutes"

### 5.3 Licensing & Contribution

- License: **MIT**
- Contributions accepted via pull request; issues triaged within 7 days (aspiration)
- Issue templates for: bug report, lab feedback, feature request

---

## 6. Functional Requirements

### 6.1 Agentic Logic & Tool Calling

- **ReAct Loop:** LangGraph state machine implementing Reason → Act → Observe cycles
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

- **Input Filtering:** All user inputs pre-processed by Llama Guard 3 before reaching the reasoning model. Flagged inputs are blocked and logged.
- **PII Redaction:** Microsoft Presidio scrubs names, emails, phone numbers, SSNs, and credit card patterns from both inputs and outputs in real time.
- **Canary Token Detection:** Post-processing step checks model outputs for embedded tracking strings before delivery to the user.
- **Output Schema Enforcement:** Structured tool call outputs validated against expected JSON schema before execution.
- **HITL Authorization:** Any tool execution classified as high-risk (file write, HTTP POST, delete operations) requires explicit human approval before proceeding.

### 6.5 Success Criteria

| Requirement | Acceptance Threshold |
|---|---|
| Llama Guard blocks unsafe prompts | ≥ 90% detection on standard LLM01 attack corpus |
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
| LLM01 | Prompt Injection | **High** | Direct injection via chat; indirect injection via poisoned tool response or RAG chunk | Llama Guard 3 input filter, system prompt hardening | Llama Guard 3, LangGraph system prompt |
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

### Module 1: Foundations

**Goal:** Get the environment running and understand how agents reason, use tools, adopt personas, and retrieve context.

**Learning Objectives:**
- Install Ollama and pull required models on macOS or Windows (Git Bash)
- Run a basic LangGraph ReAct agent that calls a live weather tool
- Load a persona and observe how the system prompt changes agent behavior
- Enable RAG and see how retrieved Markdown context influences responses
- Understand the full flow: user input → guardrail → retrieval → persona → model → tool → output

**Labs:**
- Lab 1.1 — Environment Setup (macOS or Windows)
- Lab 1.2 — Your First Tool-Calling Agent
- Lab 1.3 — Reading the ReAct Trace
- Lab 1.4 — Loading a Persona (Customer Service Bot)
- Lab 1.5 — Enabling RAG with a Markdown Context Document

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

> **Prompt a coding agent:** "Build the base LangGraph ReAct agent for Omaha-Lab. Use Ollama as the LLM backend (model configurable via env var `OLLAMA_MODEL`, default `llama3.1:8b`). The agent should implement a standard ReAct loop: receive user message → reason → optionally call a tool → observe result → respond. No tools yet — tool registry should exist but be empty. The agent should run from CLI: `python agent.py`. Print the full ReAct trace to stdout on each turn. Validate it works with both `llama3.1:8b` and `phi3:mini`."

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

**Stage 6: Input Guardrail (Llama Guard 3)**

> **Prompt a coding agent:** "Implement the Llama Guard 3 input filtering node for Omaha-Lab. Llama Guard 3 runs via Ollama (model: `llama-guard3`). Build `guardrails/llama_guard.py` with a `check_input(text: str) -> GuardResult` function that sends the text to Llama Guard 3 and returns: `safe` (bool), `category` (str or None), `raw_response` (str). Add this as the first node in the LangGraph graph — before retrieval and before the LLM. If `safe=False`, short-circuit the graph: return a blocked message to the user and log the attempt to `logs/blocked_inputs.jsonl` with timestamp, category, and truncated input. The guard must also be callable on RAG-retrieved chunks (same function, called in the retrieval node after fetch, before context injection). Add `--guard on/off` CLI flag (default off for Stage 6, so earlier stages still work)."

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
```

---

## 12. Glossary

| Term | Definition |
|---|---|
| **Ollama** | Open-source tool for running LLMs locally on consumer hardware |
| **LangGraph** | Python library for building stateful, multi-step agentic workflows as directed graphs |
| **Langflow** | Visual, low-code builder for LLM pipelines; exports flows as JSON |
| **ReAct Loop** | Reasoning + Action pattern: the model reasons about a goal, calls a tool, observes the result, and repeats |
| **HITL** | Human-in-the-Loop: a mandatory pause in agent execution requiring a human to approve before a high-risk action proceeds |
| **Persona** | A YAML-defined agent identity that sets the system prompt, allowed tools, and risk posture for a conversation |
| **RAG** | Retrieval-Augmented Generation: enriching LLM context with chunks retrieved from a document store before generating a response |
| **ChromaDB** | Open-source, locally-hosted vector database used to store and query document embeddings |
| **nomic-embed-text** | A local embedding model available via Ollama used to convert text chunks into vectors for RAG |
| **Llama Guard 3** | A fine-tuned classifier model from Meta that detects unsafe or policy-violating content in LLM inputs and outputs |
| **Microsoft Presidio** | Open-source library for detecting and anonymizing PII (Personally Identifiable Information) in text |
| **Canary Token** | A unique, trackable string embedded in data; its appearance in model output signals a data-leakage or injection event |
| **PII** | Personally Identifiable Information — data that can identify a specific individual (name, SSN, email, etc.) |
| **OWASP LLM Top 10** | Open Worldwide Application Security Project list of the 10 most critical security risks for LLM-based applications |
| **Prompt Injection** | An attack where adversarial text in the input (or retrieved context) manipulates the model into ignoring its instructions |
| **Excessive Agency** | An LLM risk where an agent takes actions beyond what was authorized, often due to overpermissioned tools |
| **Vector Store** | A database optimized for storing high-dimensional embedding vectors and performing similarity search |
| **Indirect Injection** | A prompt injection attack delivered through a secondary channel (retrieved document, tool response) rather than direct user input |
