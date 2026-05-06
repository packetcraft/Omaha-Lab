# Architecture & Tooling Decisions

This document records significant decisions made during the design and evolution of Omaha-Lab — including options that were evaluated but rejected. The goal is to prevent re-litigating settled choices and to give future contributors and instructors the context behind why the project is built the way it is.

**When to add an entry:** When a tooling alternative is evaluated, an architectural tradeoff is made, or a "why not X?" question comes up more than once. Decisions about what to build belong in the PRD; decisions about how and why belong here.

---

## Index

| # | Decision | Status | Date |
|---|---|---|---|
| [D-01](#d-01--n8n-as-alternative-orchestration-platform) | n8n as alternative orchestration platform | Rejected | 2026-05-06 |
| [D-02](#d-02--live-data-flow-visualization-for-student-learning) | Live data flow visualization for student learning | Pending implementation | 2026-05-06 |

---

## D-01 — n8n as Alternative Orchestration Platform

**Date:** 2026-05-06
**Status:** Rejected

### Context

Whether Omaha-Lab could be rebuilt on **n8n** — a self-hostable, JavaScript-based visual workflow automation platform — instead of the current Python/LangGraph stack. The motivation was to give students a drag-and-drop canvas for understanding data flows through the agent pipeline.

### Why it was considered

n8n provides a node-based canvas (similar to Langflow, which is already in scope), runs locally via Docker or npm, has an AI Agent node backed by LangChain, and supports Ollama via community integrations. It is well-suited to workflow automation and API integration tasks.

### Decision

**Rejected.** n8n cannot substitute for the current Python stack without gutting the lab's core teaching mechanism.

### Rationale

| Blocker | Detail |
|---|---|
| **Python-only dependencies** | Microsoft Presidio (PII redaction) and ChromaDB (vector store/RAG) are Python libraries. n8n runs JavaScript. Using them would require wrapping each as a separate HTTP microservice — keeping 80% of the current Python stack running anyway. |
| **LangGraph state machine is irreplaceable** | The Reason Node → Agent Node → HITL → Tools loop, conditional graph edges, `MemorySaver` checkpointer, and `AgentState` TypedDict are the architectural core. n8n's AI Agent node is an opaque LangChain chain; students cannot inspect or control the internals. |
| **Trace transparency is the teaching mechanism** | Every OWASP lab is built around observing `[REASON]` → `[ACT]` → `[OBSERVE]` → `[RESPOND]` trace output plus guardrail firing events and HITL decisions. n8n's execution log does not expose this granularity — students see that something happened, not why. |
| **Llama Guard wiring is awkward** | Llama Guard 3 can be called via Ollama's HTTP API, but integrating guard decisions as conditional branch logic inside n8n's agent loop requires significant workarounds with no clean pattern. |

### What n8n could handle without compromise

- Replacing Langflow as a visual companion tool (functionally equivalent for static flow diagrams)
- Replacing Chainlit as a webhook-based chat trigger UI
- Orchestration wrapper around the agent (scheduling runs, HITL approval routing, notifications)

### Hybrid path (if n8n is revisited)

Keep the Python/LangGraph core as-is and layer n8n on top as an orchestration/notification wrapper that calls the existing agent via HTTP. Additive, not a replacement.

---

## D-02 — Live Data Flow Visualization for Student Learning

**Date:** 2026-05-06
**Status:** Pending implementation

### Context

Students need to see where their input travels through the pipeline — from input guardrail through RAG retrieval, reasoning, tool execution, and output guardrails — to understand the security architecture they are attacking or defending. The CLI trace (`[REASON]`, `[ACT]`, `[OBSERVE]`) is informative but text-only and not spatially intuitive.

### Options evaluated

| Option | Tool | Effort | Platform | Blocker |
|---|---|---|---|---|
| A | Arize Phoenix | Low (~20 lines) | Windows + Mac, no Docker | None |
| B | LangFuse | Medium (Docker + ~30 lines) | Windows + Mac | Requires Docker on student machine |
| C | LangGraph Studio | Low | Mac only | No Windows support (as of May 2026) |
| D | Mermaid cards in Chainlit | Low (~50 lines in `ui.py`) | Windows + Mac, no new deps | Topology only, no raw data per node |

**Option A — Arize Phoenix**
Open-source LLM observability, fully local, no API key. `pip install arize-phoenix` → runs on `localhost:6006`. Integrates with LangGraph via OpenTelemetry. Each agent turn produces a live collapsible span tree: guard → reason → agent → tools → output guard, with input, output, latency, and token count at each node.

**Option B — LangFuse**
Self-hosted via Docker Compose. Richer than Phoenix (scoring, metadata, span nesting). Useful for multi-student or evaluation workflows. Adds Docker as a student machine requirement — significant for a lab that already has a long setup path.

**Option C — LangGraph Studio**
Official LangChain desktop app. Renders the actual LangGraph graph topology with nodes lighting up in real time — ideal pedagogically. Hard-blocked on Windows, which is a primary supported platform.

**Option D — Mermaid flow cards in Chainlit**
Add a pipeline diagram step card to the existing Chainlit UI showing which nodes are active for the current config (guard/RAG/HITL flags) and which path was taken on the last turn. No new dependencies; Chainlit renders Mermaid natively. Shows topology and path, not raw data.

### Decision

**Adopt Option A + Option D.** These two complement each other at different levels of abstraction without adding heavyweight infrastructure.

- **Mermaid card (D):** Pipeline topology and path taken — visible in the same Chainlit tab, zero additional student setup.
- **Phoenix (A):** Full data trace per span — the "zoom in" view, second browser tab, `pip install` only.

### Rationale

Together they cover two levels of abstraction — *flow topology* (what path did my input take?) and *data trace* (what did each node actually see and produce?). This mirrors how security engineers think: understand the architecture first, then drill into the data.

LangFuse is the upgrade path if the lab evolves toward multi-student deployments or evaluation scoring. LangGraph Studio becomes viable if the project moves to a Docker-based classroom environment or drops Windows support.

### Implementation notes

- Phoenix should be gated behind a `--observe on/off` CLI flag (default off) to keep Module 1 simple.
- Mermaid diagram must reflect the active `--guard`, `--rag`, `--hitl` flags so it matches what the student actually launched.
- Document both as optional enhancements in `labs/module1/lab1_6_visualizing_the_pipeline.md` rather than embedding in earlier labs.

---

## Decision Template

Copy this block when adding a new entry. Update the index table at the top.

```
## D-XX — [Short title]

**Date:** YYYY-MM-DD
**Status:** [Proposed | Accepted | Rejected | Pending implementation | Superseded by D-XX]

### Context

[What question or problem prompted this decision? What was the motivation?]

### Options evaluated

[List or table of alternatives considered, with brief pros/cons.]

### Decision

[One or two sentences stating what was decided.]

### Rationale

[Why this option over the others? Key tradeoffs, blockers, constraints.]

### Implementation notes (if accepted)

[Anything a developer needs to know to implement the decision correctly.]
```
