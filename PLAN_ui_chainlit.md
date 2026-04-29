# PLAN: Chainlit Web UI (Stage 12)

**Status:** Planned  
**Decision date:** 2026-04-29  
**Depends on:** Stage 11 (all CLI stages complete)

---

## Decision Summary

Add an optional browser-based chat UI using Chainlit. The UI is additive — it wraps the existing
LangGraph agent and does not change `agent.py`, `graph.py`, or any lab content. Participants can
use either mode interchangeably:

```
python agent.py          # CLI mode (all existing labs unchanged)
chainlit run ui.py       # Web UI mode (http://localhost:8000)
```

---

## Why Chainlit

Chainlit is the best fit for this lab's pedagogical goal because it natively renders agentic steps
as collapsible cards in the browser. Participants can see each guardrail decision, RAG retrieval,
tool call, and HITL prompt as a distinct visual step — making the security pipeline legible without
any extra instrumentation code.

| Option | Why not chosen |
|---|---|
| Gradio | Generic UI, no native concept of agent steps / tool calls |
| Streamlit | Requires manual threading and state management for streaming agents |
| Langflow | Rebuilds the pipeline in a visual canvas rather than exposing the Python code |
| Open WebUI | Bypasses the LangGraph pipeline entirely |

---

## File Structure Change

```
omaha-lab/
├── agent.py          ← unchanged CLI entry point
├── graph.py          ← unchanged
├── ui.py             ← NEW: Chainlit wrapper (~40 lines)
└── requirements.txt  ← add: chainlit>=1.0
```

---

## Implementation Outline

### `ui.py` skeleton

```python
import chainlit as cl
from graph import build_graph          # existing LangGraph builder
from langchain_core.messages import HumanMessage

graph = build_graph()                  # reuse existing compiled graph

@cl.on_message
async def on_message(message: cl.Message):
    config = {"configurable": {"thread_id": cl.user_session.get("thread_id")}}

    async with cl.Step(name="Agent", type="run") as root:
        async for event in graph.astream_events(
            {"messages": [HumanMessage(content=message.content)]},
            config=config,
            version="v2",
        ):
            kind = event["event"]

            if kind == "on_chain_start" and event["name"] in ("llama_guard", "rag_retrieval", "hitl"):
                async with cl.Step(name=event["name"], type="tool") as step:
                    step.input = event.get("data", {}).get("input", "")

            elif kind == "on_chain_end" and event["name"] == "agent":
                output = event["data"]["output"]["messages"][-1].content
                await cl.Message(content=output).send()
```

### Key implementation notes

- `graph.py` must expose a compiled async-compatible graph (`graph.astream_events`).
  LangGraph supports this natively — no changes to graph logic required, only ensure
  `graph.compile()` returns a `CompiledGraph` (not `CompiledStateGraph` in sync-only mode).
- CLI flags (`--persona`, `--rag`, `--guard`, `--hitl`) become Chainlit chat settings
  (sidebar toggles), configured via `@cl.on_chat_start`.
- HITL prompts (`[HITL] Approve? yes/no`) map to `await cl.AskActionMessage(...).send()` —
  Chainlit's built-in human approval widget. No keyboard input polling needed.
- Thread ID for LangGraph memory is stored in `cl.user_session` per browser session.

---

## Lab Mode Selector (Chat Profiles)

The Chainlit profile selector field is labelled **"Lab Mode"** (replaces the default generic
"Profile name" label). Participants pick a mode before their first message — it maps directly
to the four CLI quick-start commands in the README.

| Lab Mode | Active layers | Equivalent CLI |
|---|---|---|
| **Bare** | None — raw agent, attack surface open | `python agent.py` |
| **Guarded** | Llama Guard + HITL | `python agent.py --guard on --hitl on` |
| **RAG Analyst** | RAG + Security Analyst persona | `python agent.py --persona security_analyst --rag on` |
| **Full Defense** | All layers on (HR Assistant persona) | `python agent.py --persona hr_assistant --rag on --guard on --hitl on` |

"Bare" and "RAG Analyst" are the natural choices for Module 2 (offensive) labs; "Guarded" and
"Full Defense" for Module 3 (defensive) labs. The name signals posture before the participant
reads any lab instructions.

**Secondary: Chat Settings** (sidebar gear icon) — individual controls that mirror the four CLI
flags. Profiles act as one-click presets that initialize all four controls; users can then override
any flag independently mid-session without restarting.

### Chat Settings widgets

| Widget | Type | Values | Maps to CLI flag |
|--------|------|--------|-----------------|
| Persona | `Select` | none / customer_service / hr_assistant / security_analyst / code_assistant | `--persona` |
| Guard | `Select` | off / on | `--guard on` |
| RAG | `Select` | off / on | `--rag on` |
| HITL | `Select` | off / on | `--hitl on` |

### Recommended design: profiles as presets, controls as overrides

1. On profile selection (`@cl.on_chat_start`), initialize all four `ChatSettings` widgets to the
   profile's preset values — matching the four CLI recipes exactly.
2. Any individual widget change fires `@cl.on_settings_update`, which reads the current values of
   **all four** widgets and calls `_build_session(persona, rag, guard, hitl)` to rebuild the agent.
3. The HITL queues (`hitl_req_q` / `hitl_res_q`) are torn down and recreated on each rebuild so
   toggling HITL mid-session does not leave stale queue state.

This means the four profiles are just named shortcuts — participants who need a custom combination
(e.g. RAG on + guard on, no HITL) can compose it freely via the sidebar controls without touching
the CLI.

---

## Visible Steps in the UI

| Pipeline layer | Chainlit step type | What the participant sees |
|---|---|---|
| Regex pre-filter | `tool` step | Input text, matched pattern or "pass" |
| Llama Guard | `tool` step | Safety category or "safe" |
| RAG retrieval | `tool` step | Top-3 chunk previews + source file |
| Tool call (weather, search…) | `tool` step | Tool name, arguments, raw result |
| HITL authorization | `ask` message | Approve / Deny buttons |
| Presidio redaction | `tool` step | Entities redacted and their types |
| Final response | `message` | LLM output |

---

## Participant Setup (delta only)

```bash
pip install chainlit          # one additional package
chainlit run ui.py            # starts browser at http://localhost:8000
```

No Ollama changes, no new models, no new API keys.

---

## Out of Scope for this Stage

- Authentication or multi-user sessions
- Persistent chat history across browser restarts (LangGraph memory covers within-session)
- Deployment beyond localhost
- Modifying any existing lab Markdown files (all labs remain CLI-first)

---

## Coding Agent Prompt (Stage 12)

> **Prompt a coding agent:** "Add a Chainlit web UI to Omaha-Lab as `ui.py`. The UI wraps
> the existing `graph.py` LangGraph agent — do not modify `agent.py` or `graph.py`. Requirements:
> (1) Implement four Chainlit chat profiles using `@cl.set_chat_profiles`. Label the selector
> field **"Lab Mode"** (not the default "Profile name"). The four profiles are: **Bare** (no
> guardrails), **Guarded** (`--guard on --hitl on`), **RAG Analyst** (`--persona security_analyst
> --rag on`), **Full Defense** (`--persona hr_assistant --rag on --guard on --hitl on`). Each
> profile pre-configures the graph on `@cl.on_chat_start` with the equivalent CLI flags.
> (2) Also expose fine-grained Chat Settings (sidebar gear icon) with individual toggles for
> guard, RAG, HITL, and a persona dropdown — for custom combinations beyond the four profiles.
> (3) `@cl.on_message` streams graph events using `astream_events` and renders each pipeline
> layer (llama_guard, rag_retrieval, hitl, tool calls, presidio) as a named `cl.Step`.
> (4) HITL approval uses `cl.AskActionMessage` with Approve/Deny buttons instead of stdin.
> (5) Add `chainlit>=1.0` to `requirements.txt`. (6) Add a `## Web UI (Optional)` section to
> README.md with two-line setup: `pip install chainlit` and `chainlit run ui.py`. The CLI path
> (`python agent.py`) must remain fully functional and unchanged."

**Deliverables:** `ui.py`, updated `requirements.txt`, updated `README.md` (Web UI section)  
**Depends on:** Stage 11
