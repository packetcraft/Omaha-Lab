# Attack Prompt Library

Curated attack prompts organised by OWASP Top 10 for LLM Applications category.
Each prompt is a self-contained YAML file with metadata that describes how to
run it, what the expected outcome is, and which lab it relates to.

---

## Directory Structure

```
prompts/
├── llm01_prompt_injection/       LLM01 — direct and indirect injection
├── llm02_sensitive_disclosure/   LLM02 — PII and data extraction
├── llm05_output_handling/        LLM05 — dangerous output payloads
├── llm06_excessive_agency/       LLM06 — unauthorised tool use
├── llm07_system_prompt_leakage/  LLM07 — system prompt extraction
├── llm08_rag_poisoning/          LLM08 — poisoned retrieval context
├── llm09_misinformation/         LLM09 — hallucination and grounding
└── llm10_unbounded_consumption/  LLM10 — runaway loops and token floods
```

---

## Prompt Schema

Every `.yaml` file follows this schema:

```yaml
id: <string>              # unique key, e.g. llm01-direct-001
category: <string>        # OWASP category code, e.g. LLM01
name: <string>            # short human-readable title
description: <string>     # one-line summary of the attack vector
persona: <string>         # persona to load: customer_service | hr_assistant |
                          #   security_analyst | code_assistant | any
rag: <bool>               # whether RAG retrieval should be enabled
hitl: <bool>              # whether HITL should be enabled
guard_expected: <string>  # blocked | passes | varies
layer: <string>           # which layer catches it:
                          #   regex | llama_guard | hitl | presidio | model | none
lab: <string>             # path to the associated lab file
difficulty: <string>      # easy | medium | hard
prompt: |
  <the exact text to paste at the You: prompt>
notes: |
  <what to look for in the trace output; which log file records it>
```

### Field notes

- **`guard_expected: blocked`** — the guardrail stack stops this before the agent responds.
- **`guard_expected: passes`** — the prompt reaches the agent; the defence is in the agent's persona constraints or output layer.
- **`guard_expected: varies`** — outcome depends on model temperature or Llama Guard version.
- **`layer: none`** — no automated defence catches this; it is shown as a gap.

---

## Usage

### Manual (lab exercises)

Start the agent with the flags shown in the prompt's YAML, then paste the
`prompt` field at the `You:` input:

```bash
# example: llm01-direct-001 (customer_service persona, guard on)
python agent.py --persona customer_service --guard on
```

### Programmatic (evaluation harness)

The `bench.py` evaluation harness (see PROJECT_REVIEW.md) loads all YAML files
in this directory tree and fires each prompt against the configured agent,
comparing `guard_expected` to the actual outcome.  The schema is stable — new
prompts added here are automatically picked up by the harness.

---

## Prompt Count

| Category | Prompts |
|---|---|
| LLM01 — Prompt Injection | 10 |
| LLM02 — Sensitive Disclosure | 3 |
| LLM05 — Improper Output Handling | 2 |
| LLM06 — Excessive Agency | 4 |
| LLM07 — System Prompt Leakage | 3 |
| LLM08 — Vector & Embedding Weaknesses | 1 |
| LLM09 — Misinformation | 1 |
| LLM10 — Unbounded Consumption | 2 |
| **Total** | **26** |
