# Langflow Visual Flows

This directory contains four Langflow 1.x JSON flow exports that visually represent the Omaha-Lab agent configurations. Each flow corresponds to a progressively more secure version of the same ReAct agent.

---

## Prerequisites

1. **Install Langflow 1.x**
   ```bash
   pip install langflow>=1.0.0
   langflow run
   ```
   Open `http://localhost:7860` in your browser.

2. **Ollama must be running** on `http://localhost:11434` with the required models pulled:
   ```bash
   ollama pull llama3.1:8b        # reasoning model
   ollama pull nomic-embed-text   # RAG embeddings (rag_agent only)
   ollama pull llama-guard3       # safety filter (secured_agent only)
   ```

3. **Environment variables** — copy `.env.example` to `.env` and fill in your keys before running tool-calling flows:
   ```
   WEATHER_API_KEY=<your OpenWeatherMap free-tier key>
   ```

---

## How to Import a Flow

1. Open Langflow at `http://localhost:7860`
2. Click **New Flow → Import** (or drag-and-drop the `.json` file onto the canvas)
3. Select the desired `.json` file from this directory
4. The flow opens with all nodes and edges pre-configured
5. Click **Playground** (bottom bar) to chat with the agent

> **Note:** Langflow's component registry evolves between minor versions. If a node shows a red error badge after import, right-click it → **Edit** and verify the field values match your installed Langflow version. The core structure (node types, edge connections, field names) follows the Langflow 1.0.x schema.

---

## Flow Reference

### `base_agent.json` — Baseline Agent (Stage 2–3)

**What it demonstrates:** The unguarded baseline — Ollama LLM driving a ReAct loop with all five live tools. Use this to explore normal agent behaviour before adding security layers.

**Nodes:**
| Node | Type | Role |
|------|------|------|
| Chat Input | `ChatInput` | User message entry point |
| Ollama | `OllamaModel` | Local LLM (llama3.1:8b) |
| DuckDuckGo Search | `DuckDuckGoSearchRun` | No-key web search |
| Weather Tool | `PythonFunctionTool` | OpenWeatherMap current weather |
| HTTP GET Tool | `PythonFunctionTool` | Domain allow-listed GET requests |
| Read File Tool | `PythonFunctionTool` | Read from workspace/ sandbox |
| Write File Tool | `PythonFunctionTool` | Write to workspace/ (HIGH-RISK) |
| ReAct Agent | `ReActAgentComponent` | Reason → Act → Observe loop |
| Chat Output | `ChatOutput` | Display response |

**CLI equivalent:**
```bash
python agent.py
```

---

### `secured_agent.json` — Security-Hardened Agent (Stage 6–8)

**What it demonstrates:** The full defensive stack from Module 3. Three security nodes wrap the base agent: an input guardrail, an output PII redactor, and a HITL approval breakpoint for high-risk tool calls.

**Nodes:**
| Node | Type | Role |
|------|------|------|
| Chat Input | `ChatInput` | Raw user message |
| **Llama Guard 3 Filter** | `CustomComponent` | Screens input via `llama-guard3`; blocks unsafe content (LLM01, LLM08) |
| Ollama | `OllamaModel` | Local LLM |
| DuckDuckGo Search | `DuckDuckGoSearchRun` | Web search (low-risk) |
| Weather Tool | `PythonFunctionTool` | Weather (low-risk) |
| Write File Tool | `PythonFunctionTool` | File write (HIGH-RISK — intercepted by HITL) |
| ReAct Agent | `CustomComponent` | Agent node wired between guardrails |
| **Presidio PII Redactor** | `CustomComponent` | Scrubs names, emails, SSNs, phone numbers from output (LLM02) |
| **HITL Approval Breakpoint** | `CustomComponent` | Presents high-risk tool calls for human approval; logs decisions to `logs/hitl_log.jsonl` (LLM06) |
| Chat Output | `ChatOutput` | PII-cleaned response |

**Data flow:**
```
ChatInput → LlamaGuard3 → ReActAgent → PresidioRedactor → ChatOutput
                                  ↓
                          HITLBreakpoint (write_file)
```

**CLI equivalent:**
```bash
python agent.py --guard on --hitl on
```

**Lab use:** Run Module 2 attack payloads against this flow to see which are now blocked.

---

### `rag_agent.json` — RAG-Augmented Agent (Stage 5)

**What it demonstrates:** Retrieval-Augmented Generation using local Markdown documents. On each query, ChromaDB retrieves the top-3 most relevant chunks from `context_docs/` and prepends them to the agent's context window before reasoning.

**Nodes:**
| Node | Type | Role |
|------|------|------|
| Directory Loader | `DirectoryLoader` | Loads all `.md` files from `context_docs/` |
| Text Splitter | `CharacterTextSplitter` | Chunks documents (~600 chars, 100-char overlap) |
| Ollama Embeddings | `OllamaEmbeddings` | Local embeddings via `nomic-embed-text` |
| **ChromaDB** | `Chroma` | Vector store — persists to `.chroma/`, retrieves top-3 chunks |
| Chat Input | `ChatInput` | User query (also used as retrieval query) |
| Ollama | `OllamaModel` | Local LLM |
| DuckDuckGo Search | `DuckDuckGoSearchRun` | Web search fallback for live data |
| ReAct Agent (RAG) | `ReActAgentComponent` | Reasons over retrieved context + tools |
| Chat Output | `ChatOutput` | Grounded response |

**Data flow:**
```
DirectoryLoader → TextSplitter ↘
                               ChromaDB ← OllamaEmbeddings
ChatInput (query) ────────────→ ChromaDB → (top-3 chunks)
                                                    ↓
ChatInput ──────────────────────────────→ ReActAgent → ChatOutput
OllamaModel ────────────────────────────→ ReActAgent
DuckDuckGoSearch ───────────────────────→ ReActAgent
```

**CLI equivalent:**
```bash
python agent.py --rag on
```

**Lab use:**
- Lab 1.5 — Enable RAG and observe how retrieved context changes responses
- Lab 2.3 — Inject `poisoned_policy.md` and observe indirect injection via retrieval
- Lab 2.8 — Full RAG poisoning attack with `poisoned_policy.md`
- Lab 3.9 — Compare hallucination rate with RAG on vs. off

---

### `persona_agent.json` — Persona-Driven Agent (Stage 4)

**What it demonstrates:** Swappable agent identities. A `Prompt` node injects a persona-specific system prompt before any user message, controlling the agent's tone, scope, and (via the tool connections) which tools it may use.

**Nodes:**
| Node | Type | Role |
|------|------|------|
| **Persona System Prompt** | `Prompt` | System prompt template with `persona_name`, `persona_instructions`, `allowed_tools`, `risk_level` fields |
| Persona Presets (Reference) | `TextInput` | Reference card — paste values from `personas/*.yaml` |
| Chat Input | `ChatInput` | User message |
| Ollama | `OllamaModel` | Local LLM |
| DuckDuckGo Search | `DuckDuckGoSearchRun` | Web search |
| Weather Tool | `PythonFunctionTool` | Weather |
| Write File Tool | `PythonFunctionTool` | File write (disconnect for low-risk personas) |
| ReAct Agent (Persona) | `ReActAgentComponent` | System prompt → identity injection |
| Chat Output | `ChatOutput` | Persona-voice response |

**Switching personas:**
1. Click the **Persona System Prompt** node
2. Update `Persona Name` (dropdown) and paste the matching `system_prompt` from `personas/<name>.yaml` into `Persona Instructions`
3. Update `Allowed Tools` to match the persona's `allowed_tools` list
4. Disconnect any tool nodes not in the persona's allowed list

**Persona quick-reference:**

| Persona | `persona_name` | `allowed_tools` | `risk_level` | Lab Use |
|---------|----------------|-----------------|--------------|---------|
| Customer Service | `Aria (Customer Service Bot)` | `web_search, get_weather` | low | LLM01 direct injection, LLM07 prompt leakage |
| HR Assistant | `Jordan (HR Assistant)` | `web_search, read_file, write_file` | high | LLM02 PII disclosure, LLM06 excessive agency |
| Security Analyst | `Morgan (Security Analyst)` | `web_search, http_get` | medium | LLM01 indirect injection, LLM08 RAG poisoning |
| Code Assistant | `Riley (Code Assistant)` | `web_search, read_file, write_file` | high | LLM05 improper output, LLM03 supply chain |

**CLI equivalent:**
```bash
python agent.py --persona customer_service
python agent.py --persona hr_assistant
python agent.py --persona security_analyst
python agent.py --persona code_assistant
```

---

## Combining Flows

The four flows are building blocks. For a fully secured RAG + persona agent, combine the layers:

```bash
# CLI equivalent of the combined configuration:
python agent.py --persona hr_assistant --rag on --guard on --hitl on
```

In Langflow, build this by:
1. Starting with `persona_agent.json`
2. Adding the ChromaDB + embeddings pipeline from `rag_agent.json`
3. Inserting the LlamaGuard and Presidio `CustomComponent` nodes from `secured_agent.json`

---

## Troubleshooting

| Symptom | Fix |
|---------|-----|
| Node shows red error badge | Component name changed in your Langflow version — check the Langflow component sidebar for the current name |
| Ollama connection error | Run `ollama serve` and verify the base URL matches your setup |
| `llama-guard3` not found | `ollama pull llama-guard3` (requires ~6 GB) |
| `nomic-embed-text` not found | `ollama pull nomic-embed-text` |
| Presidio import error | `pip install presidio-analyzer presidio-anonymizer && python -m spacy download en_core_web_lg` |
| ChromaDB empty | Run the CLI agent with `--rag on` once first to build the index, or set the Langflow DirectoryLoader path to the absolute path of `context_docs/` |
