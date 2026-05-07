# Omaha-Lab — Project Review

**Initial review:** 2026-05-07  
**Last updated:** 2026-05-07  
**Reviewer:** Claude Sonnet 4.6  
**Scope:** Full codebase + lab content audit, gap analysis, and improvement tracking

---

## Summary

Omaha-Lab is a well-engineered, pedagogically sound LLM security research environment. The 11-stage PRD-driven build is complete, the code is clean, and the layered architecture (input guard → RAG → reason → agent → HITL → output guard) mirrors real-world patterns students will encounter in production systems. The FOUNDATIONS.md and DECISIONS.md documents are a cut above what most labs bother to produce.

**Post-review session (2026-05-07):** All P1 and P2 items from the original backlog were implemented in one session. Six fixes shipped across seven commits.

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

### 5. LlamaGuard fails open — not surfaced in a lab 🔲 OPEN

`llama_guard.py:108-110`: when Llama Guard is unreachable, the function logs a warning and returns `GuardResult(safe=True)`. This is the right default for availability, but it is a meaningful security property — a network partition silently disables the guardrail.

The fail-open behaviour is now covered by `tests/test_llama_guard.py::TestFailOpen` (network error and timeout both verified to return `safe=True`). However, no lab explicitly attacks this surface.

**Remaining:** Add a note in `lab3_1_llama_guard_inputs.md` Discussion Questions, and consider a Module 2 lab targeting guard availability.

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

### C. Add a Makefile (or `setup.sh` / `setup.ps1`) 🔲 OPEN

Setup still requires six manual commands across two platforms. A thin Makefile or platform-specific script would reduce first-run friction.

---

### D. Add a GitHub Actions CI workflow 🔲 OPEN

No CI exists. A minimal workflow running `pytest tests/` on push/PR would catch regressions. The test suite (107 tests, no Ollama required) makes this straightforward.

Suggested `.github/workflows/ci.yml`:
```yaml
on: [push, pull_request]
jobs:
  test:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - uses: actions/setup-python@v5
        with: { python-version: "3.11" }
      - run: pip install -r requirements.txt pytest
      - run: python -m spacy download en_core_web_sm
      - run: pytest tests/ -v
```

Note: the CI spacy model can be `en_core_web_sm` (small/fast) rather than `en_core_web_lg` since the tests don't exercise PII redaction directly.

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

Implementation: extend `build_graph()` to accept a `peer_agents` list and add an inter-agent communication tool. Injected payload travels in tool results — bypassing the existing S15 regex pre-filter.

---

### Evaluation Harness (`bench.py`) 🔲 OPEN

A script that fires a fixed set of attack prompts and reports hits/misses per guard configuration. Especially useful for the regex pre-filter coverage gap exposed by `test_llama_guard.py`.

---

### Attack Prompt Library (`prompts/`) 🔲 OPEN

A curated `prompts/` directory organised by OWASP category. Removes the burden on students to craft novel attacks and ensures lab exercises are reproducible across cohorts.

---

### Docker Compose 🔲 OPEN

A `docker-compose.yml` for classroom/demo deployments. Non-blocking for local development use.

---

## Remaining Priority Order

| Priority | Item | Effort |
|---|---|---|
| P1 | Add note to `lab3_1` about Llama Guard fail-open (Issue #5) | 30 min |
| P2 | GitHub Actions CI (pytest on push/PR) | 30 min |
| P2 | Makefile / `setup.sh` / `setup.ps1` | 1 hour |
| P3 | Split `requirements.txt` into core + optional files | 30 min |
| P3 | Evaluation harness (`bench.py`) | 1 day |
| P3 | Attack prompt library (`prompts/`) | 2–4 hours |
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
