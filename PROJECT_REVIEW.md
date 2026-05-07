# Omaha-Lab — Project Review

**Initial review:** 2026-05-07  
**Last updated:** 2026-05-07  
**Reviewer:** Claude Sonnet 4.6  
**Scope:** Full codebase + lab content audit, gap analysis, and improvement tracking

---

## Summary

Omaha-Lab is a well-engineered, pedagogically sound LLM security research environment. The 11-stage PRD-driven build is complete, the code is clean, and the layered architecture (input guard → RAG → reason → agent → HITL → output guard) mirrors real-world patterns students will encounter in production systems. The FOUNDATIONS.md and DECISIONS.md documents are a cut above what most labs bother to produce.

**Post-review session (2026-05-07):** All P1 and P2 items from the original backlog implemented. Ten commits shipped: schema_guard wiring, Module 4 labs, pyproject.toml fixes, iteration cap, test suite, docs (PRD v4.5), CI workflow, cross-platform test fix, and Makefile.

---

## Strengths

### Architecture

- **`build_graph()` factory pattern** — CLI (`agent.py`) and Chainlit UI (`ui.py`) share the exact same LangGraph graph, instantiated with different `hitl_node_factory` values. This is the correct design: UI-specific behavior is injected, not forked.
- **HITL overwrite trick** — the HITL node patches the AIMessage in-place (same message ID), so `ToolNode` only sees approved calls. Subtle and correct.
- **Dual-layer input guard** — regex pre-filter catches adversarial S15 (prompt injection) patterns that Llama Guard 3 misses because the base model was not fine-tuned on them. This gap is well-documented in `llama_guard.py`.
- **Sandbox traversal guard** — `file_ops.py` uses `.resolve()` + `.relative_to()` to block path traversal. This is the correct pattern.
- **Workspace gitignore** — `workspace/*` is properly excluded from git; `exfil.txt` stays local. Same for `audit/*.jsonl` and `logs/*.jsonl`. The `.gitignore` is clean.

### Documentation

- **FOUNDATIONS.md** — the CPU/firmware/OS analogy is a rare pedagogical artifact that actually earns its keep. It frames every attack and defense before students touch the code.
- **DECISIONS.md** — records n8n evaluation (rejected), live visualization options (Phoenix + Mermaid adopted). Prevents future wheel reinvention. Worth extending.
- **README.md** — ASCII pipeline diagram, dual-platform setup (macOS/Windows), all CLI flags documented, Web UI section, Observability section. Comprehensive.

### Lab Content

- Module 2 (offensive) and Module 3 (defensive) cover OWASP LLM01–LLM10 with corresponding attack/defend pairs — a logical, testable structure.
- Module 4 (architecture deep-dive) is now complete: 5 labs covering state machine, tool decorator, RAG pipeline, guardrail code, and schema guard integration.

---

## Issues — Status

### 1. `pyproject.toml` references wrong search package name ✅ FIXED

`pyproject.toml` listed `duckduckgo-search>=6.3.7` but the library was renamed to `ddgs`. `requirements.txt` and `tools/search.py` already used the correct name.

**Fix applied (commit `d9a4f79`):** Updated `pyproject.toml:25` to `"ddgs>=6.3.7"`.

---

### 2. Module 4 claims five labs; only one existed ✅ FIXED

`README.md` stated `labs/module4/` contains labs 4.1–4.5 but only `lab4_1_langgraph_state_machine.md` existed.

**Fix applied (commit `d9a4f79`):** Labs 4.2–4.5 written and merged:
- `lab4_2_tool_decorator.md` — `@tool` decorator, risk registry, HITL wiring; add `list_files` tool exercise
- `lab4_3_rag_pipeline.md` — manifest delta system, chunking algorithm, cosine distance, chunk-size tuning
- `lab4_4_guardrail_code.md` — regex pre-filter, Llama Guard prompt format, fail-open, custom pattern exercise
- `lab4_5_schema_guard.md` — schema guard integration audit, violation triggering, multi-turn scan bug

---

### 3. `schema_guard.py` was unintegrated dead code ✅ FIXED

`guardrails/schema_guard.py` implemented `validate_tool_result()` but nothing in `graph.py` or any node called it.

**Fix applied (commit `d9a4f79`):**
- `graph.py`: added `ToolMessage` to imports; added schema validation loop in `output_guard_node`; added `schema_violations` list to `additional_kwargs`
- `agent.py`: extracts `schema_violations` signal; displays `schema: clean` / `schema: N violation(s)` in the guard receipt
- `ui.py`: adds `Schema: clean/N violation(s)` to the Output Guard step card

Lab 4.5 documents the remaining known limitation (multi-turn scan scans historical ToolMessages, not just the current turn) as a Discussion Question with a fix challenge.

---

### 4. `pyproject.toml` missing optional dependencies ✅ FIXED

`chainlit`, `arize-phoenix`, `openinference-instrumentation-langchain`, and `spacy` were in `requirements.txt` but absent from `pyproject.toml`.

**Fix applied (commit `91bf145`):** Added `[project.optional-dependencies]` with four groups:
- `nlp` — spacy
- `ui` — chainlit
- `observe` — arize-phoenix + full OpenTelemetry stack
- `all` — all three above
- `dev` — pytest (added in commit `0d2e4f1`)

Install commands: `pip install ".[ui]"`, `pip install ".[observe]"`, `pip install ".[all]"`.

---

### 5. LlamaGuard fails open — not surfaced in a lab ✅ FIXED

`llama_guard.py:108-110`: when Llama Guard is unreachable, the function logs a warning and returns `GuardResult(safe=True)`. This is the right default for availability, but it is a meaningful security property — a network partition silently disables the guardrail.

**Fix applied (commit `TBD`):**
- `lab3_1_llama_guard_inputs.md`: added a "Security note — fail-open" callout in the Background section pointing students to the relevant code
- Discussion Question 4 added: three-part question covering (a) fail-open vs. fail-closed tradeoffs, (b) guard availability attack surface and OWASP mapping, (c) mitigations — observability alerting and regex pre-filter as a secondary fast-path

---

## Improvements — Status

### A. Add a test suite ✅ DONE

**Implemented (commit `0d2e4f1`):** 107 tests across five files, 0.45s runtime, no live Ollama required:

| File | Tests | Coverage |
|---|---|---|
| `tests/test_file_ops.py` | 13 | Sandbox traversal (dotdot, absolute Unix/Windows, URL-encoded), normal I/O, subdirectory creation |
| `tests/test_schema_guard.py` | 14 | Type/empty/JSON rules, tool-scoping of JSON check, all five built-in tool shapes |
| `tests/test_llama_guard.py` | 42 | All 29 regex patterns + 7 benign pass-throughs; response parsing; fail-open on network error and timeout |
| `tests/test_persona_loader.py` | 22 | All 4 YAMLs, field invariants, customer_service tool scoping, missing-slug error |
| `tests/test_agent_filter.py` | 8 | None persona, subset, full set, empty set, unknown tool warning, order preservation |

Run with: `venv/Scripts/python -m pytest tests/ -v` (Windows) or `venv/bin/python -m pytest tests/ -v` (macOS).

---

### B. Split requirements.txt into core and optional 🔲 OPEN (partial)

The `pyproject.toml` optional dependency groups (fix #4) solve the `pip install .` case. The monolithic `requirements.txt` still installs chainlit + phoenix by default. Consider creating `requirements-core.txt` for students who only need the CLI agent.

---

### C. Add a Makefile ✅ DONE

**Implemented (commit `cc39b4c`):** `Makefile` with platform detection (`OS=Windows_NT` → `venv/Scripts/`; else `venv/bin/`).

Targets: `install` (venv + deps + spacy model + .env), `models` (ollama pulls), `run` / `run-secure` / `run-rag` / `run-full`, `ui`, `phoenix`, `test`, `clean`, `help`. Quick start: `make install models run`. README setup sections updated with shortcut notes for macOS and Windows.

---

### D. Add a GitHub Actions CI workflow ✅ DONE

**Implemented (commit `34bd543`):** `.github/workflows/ci.yml` — runs on push and PR to master.

```yaml
on: push/pull_request (master)
jobs: test (ubuntu-latest, python 3.11)
  - pip install -r requirements.txt + pytest
  - python -m spacy download en_core_web_sm  (small model; tests don't exercise PII redaction)
  - pytest tests/ -v
```

---

### E. Enforce iteration limits in the graph ✅ DONE

**Implemented (commit `6fa0486`):**
- `state.py`: added `iteration_count: int` to `AgentState`
- `graph.py`: added `max_iterations: int = 10` parameter to `build_graph()`; `agent_node` increments counter and replaces tool-calling responses with a graceful cutoff message when the cap is reached
- `agent.py`: added `--max-iterations N` CLI flag (default 10); wired into `build_graph` and `run_repl`; banner shows `Iterations: N max per session`
- `README.md`: added `--max-iterations` row to CLI flags table
- `lab3_7`: Steps 2–4 rewritten to demonstrate the new flag and observe the graceful `[ITER LIMIT]` cutoff

---

## Additions — Status

### Module 4 Labs 4.2–4.5 ✅ DONE

See Issue #2 above. All four labs written and merged in commit `d9a4f79`.

---

### Module 5 — Multi-Agent & Agentic Orchestration Security 🔲 OPEN

Single-agent attack surfaces are fully covered. The next frontier:

| Lab | OWASP Mapping | Attack Scenario |
|---|---|---|
| 5.1 — Agent-to-Agent Trust Escalation | LLM01, LLM08 | Agent A receives a crafted tool result from Agent B that modifies its system prompt |
| 5.2 — Tool Poisoning via MCP | LLM02 (supply chain) | Register a malicious MCP tool that exfiltrates context |
| 5.3 — Orchestrator Bypass | LLM06 (excessive agency) | Sub-agent exceeds scope granted by orchestrator |
| 5.4 — Cross-Agent Prompt Injection | LLM01 | Inject instructions in one agent's output that hijack a downstream agent |

#### New Files

| File | Purpose |
|---|---|
| `tools/delegate.py` | `delegate_to_agent(agent_name, task)` — invokes a named sub-agent synchronously, returns its response as a string. Injection payloads travel here as ToolMessage content, bypassing `guard_input` |
| `tools/malicious_mcp.py` | Simulated poisoned tool for Lab 5.2 — looks legitimate but writes its full input context to `workspace/exfil.txt`. No real MCP protocol required |
| `agents/sub_agent.py` | Thin wrapper around `build_graph()` with an optional tool whitelist (allowed tool names). Used by the delegate tool to instantiate named sub-agents |
| `agents/__init__.py` | Registry mapping agent names (`"researcher"`, `"summarizer"`, `"malicious_peer"`) to their configs. `delegate.py` looks up by name here |
| `multi_agent.py` | Orchestrator entry point (like `agent.py`) that boots an orchestrator with `delegate_to_agent` in its tool list |
| `tests/test_delegate.py` | Tests: correct routing, scope enforcement (5.3), that tool results are not re-guarded (the gap), exfil detection (5.2) |
| `labs/module5/lab5_1_trust_escalation.md` | Lab guide |
| `labs/module5/lab5_2_tool_poisoning_mcp.md` | Lab guide |
| `labs/module5/lab5_3_orchestrator_bypass.md` | Lab guide |
| `labs/module5/lab5_4_cross_agent_injection.md` | Lab guide |

#### Modified Files

| File | Change |
|---|---|
| `graph.py` | Add `peer_agents: dict \| None = None` to `build_graph()`; auto-inject `delegate_to_agent` when present |
| `state.py` | Add `delegation_chain: list` — `{from, to, task}` entries appended per delegation hop; used in trace output and Lab 5.3 escalation path |
| `agent.py` | Add `--peer-agents researcher,summarizer` flag to wire named agents from the registry |
| `README.md` | Add Module 5 row to lab guide table |
| `DECISIONS.md` | D-04: why delegation is implemented as a tool (not a graph node) — add when implementing |
| `prompts/` | ~6 new YAML files for multi-agent injection vectors (`layer: none`, `guard_expected: passes`) — payloads in tool results that bypass the S15 regex |

#### Design Decisions (lock in before building)

1. **Guard scope** — `guard_input` only scans `HumanMessage`, not `ToolMessage`. This is intentional and is the attack surface for Labs 5.1 and 5.4. Do not silently close this gap in the implementation.

2. **Sub-agent isolation** — each `delegate_to_agent` call gets a fresh `thread_id` so sub-agent conversation memory doesn't leak to the orchestrator except through the returned string.

3. **MCP simulation** — no real MCP protocol needed. A `@tool`-decorated function with a `workspace/exfil.txt` side effect is sufficient for the pedagogical point in Lab 5.2.

4. **Scope enforcement (Lab 5.3)** — sub-agents receive a tool whitelist at instantiation time. The bypass is demonstrated by an injection payload that convinces a `["read_file"]`-scoped sub-agent to call `write_file` anyway — showing that whitelist enforcement must happen at the graph level, not just in the prompt.

**Effort estimate:** ~4–6 hours for code + tests, ~3–4 hours for lab content.

---

### Evaluation Harness (`bench.py`) ✅ DONE

**Implemented:** `bench.py` + `labs/module3/lab3_10_bench_coverage.md` — loads all YAML files from `prompts/` and fires each against the guard stack.

Two modes:
- **`--regex-only`** — tests the regex pre-filter only; no Ollama required; instant (0.15s for all 26 prompts)
- **default** — full `LlamaGuard.check_input()` including Llama Guard 3; requires `llama-guard3` running

Filters: `--category LLM01`, `--layer regex`, `--difficulty easy`. Output: coloured table (default) or `--json` for CI. Exits non-zero if any failures.

Skips prompts with `rag: true` (ChromaDB dependency) or `hitl: true` (interactive). `guard_expected: varies` prompts are reported as INFO, not scored.

Makefile targets: `make bench` (full stack) and `make bench-regex` (regex-only).

---

### Attack Prompt Library (`prompts/`) ✅ DONE

**Implemented:** 26 YAML prompts across 8 OWASP categories. Each file includes `id`, `category`, `persona`, `rag`, `hitl`, `guard_expected`, `layer`, `lab`, `difficulty`, `prompt`, and `notes` fields — schema is stable for consumption by `bench.py`.

| Category | Files | Highlights |
|---|---|---|
| LLM01 Prompt Injection | 10 | Direct (6): regex-caught and guard-bypass variants; Indirect (4): tool response, file system, RAG pipeline |
| LLM02 Sensitive Disclosure | 3 | Direct bulk request, authority impersonation, structured JSON extraction |
| LLM05 Output Handling | 2 | XSS script tag, shell command substitution — both pass all guards |
| LLM06 Excessive Agency | 4 | Export, authority-gated dump, path traversal payload, multi-step chain |
| LLM07 System Prompt Leakage | 3 | Direct ask (regex), indirect framing, completion attack |
| LLM08 RAG Poisoning | 1 | Benign query retrieving poisoned_policy.md chunk |
| LLM09 Misinformation | 1 | RAG vs. no-RAG grounding comparison |
| LLM10 Unbounded Consumption | 2 | Recursive search loop, token flood repetition |

---

### Docker Compose 🔲 OPEN

A `docker-compose.yml` for classroom/demo deployments. Non-blocking for local development use.

---

## Remaining Priority Order

| Priority | Item | Effort |
|---|---|---|
| ~~P1~~ | ~~Add note to `lab3_1` about Llama Guard fail-open (Issue #5)~~ | ✅ Done |
| ~~P2~~ | ~~GitHub Actions CI (pytest on push/PR)~~ | ✅ Done |
| ~~P2~~ | ~~Makefile / setup script~~ | ✅ Done |
| P3 | Split `requirements.txt` into core + optional files | 30 min |
| ~~P3~~ | ~~Evaluation harness (`bench.py`)~~ | ✅ Done |
| ~~P3~~ | ~~Attack prompt library (`prompts/`)~~ | ✅ Done |
| P4 | Module 5 (multi-agent security) | 2–3 days |
| P4 | Docker Compose | 2–4 hours |

---

## Commit Log for This Review Session

| Commit | Change |
|---|---|
| `d9a4f79` | Fix pyproject.toml package name; wire schema_guard; write labs 4.2–4.5; update README Module 4 table; add PROJECT_REVIEW.md |
| `91bf145` | Add optional dependency groups to pyproject.toml (nlp, ui, observe, all) |
| `6fa0486` | Add application-level iteration cap (state.py, graph.py, agent.py, lab3_7) |
| `0d2e4f1` | Add pytest test suite — 107 tests across five modules; add dev optional group |
| `3510662` | Update PRD to v4.5, PROJECT_REVIEW, and README to reflect post-review session work |
| `34bd543` | Add GitHub Actions CI workflow; update PROJECT_REVIEW |
| `5265f47` | Fix test_path_traversal_absolute_windows: skip on non-Windows (CI green) |
| `cc39b4c` | Add Makefile with cross-platform setup and run targets |
