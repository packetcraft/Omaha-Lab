# Lab 3.10 — Measuring Guard Coverage with the Evaluation Harness

**Module:** 3 — Defensive Architecture
**OWASP Risk:** LLM01–LLM10 — Cross-cutting coverage analysis
**Estimated time:** 30 minutes
**Prerequisite:** [Lab 3.9 — Grounding with RAG and Search](lab3_9_rag_grounding.md)

---

## Objective

Use the `bench.py` evaluation harness to measure how much of the attack prompt
library the current guard stack actually catches, distinguish hard blocks from
coverage gaps, and produce a machine-readable report suitable for CI integration.

---

## Background

Labs 3.1–3.9 enabled individual defence layers and verified each one against
one or two manually crafted payloads. That approach is reproducible but narrow —
a single prompt confirms a guard is wired, not that it covers the attack surface.

`bench.py` closes the gap by firing all 26 prompts in the `prompts/` library
at once and comparing each outcome to the `guard_expected` declaration in the
prompt's YAML metadata. Results are reported in four buckets:

| Status | Meaning |
|---|---|
| **PASS** | Actual outcome matches `guard_expected` |
| **FAIL** | Actual outcome contradicts `guard_expected` — regression |
| **INFO** | `guard_expected: varies` — outcome recorded but not scored |
| **SKIP** | Prompt requires RAG or HITL — not testable in bench mode |

The harness runs in two modes:

- **`--regex-only`** — tests only the regex pre-filter (`_INJECTION_PATTERNS` in
  `llama_guard.py`). No Ollama call is made. Runs in under 0.2 seconds.
- **default** — calls `LlamaGuard.check_input()`, which runs the regex first
  and falls through to `llama-guard3` if the regex passes. Requires Ollama.

---

## Setup

No additional setup is required beyond a working venv. The prompt library is
already on disk at `prompts/`.

For Steps 4–5 (full guard stack), ensure Ollama is running with `llama-guard3`:

```bash
ollama pull llama-guard3   # if not already done (~6 GB, one-time)
ollama serve               # if not already running
```

---

## Steps

### Step 1: Regex-Only Scan — No Ollama Required

Run the harness in regex-only mode:

```bash
python bench.py --regex-only
```

Read the output. Note which prompts are scored as PASS and which are INFO or SKIP.

The `HIT` column shows `regex` when the pre-filter caught the prompt, and is
blank when the prompt bypassed the regex. The `STATUS` column shows the verdict.

Expected summary line (approximate — exact counts depend on your YAML library):

```
Results:  9 passed  0 failed  11 skipped  6 info  | guard: regex-only  total: 26  time: 0.15s
```

### Step 2: Read the Layer Column

Look at the `LAYER` column across all rows. Each row's status is determined by
the combination of its `layer` and `guard_expected` values:

| layer | guard_expected | --regex-only status |
|---|---|---|
| `regex` | `blocked` | PASS if regex matched, FAIL if not |
| `regex` | `passes` | PASS if regex did not match (false-positive check) |
| `llama_guard` / `model` / `none` | `blocked` | **SKIP** — can't test without Ollama |
| `llama_guard` / `model` / `none` | `passes` | PASS — correctly bypasses regex |
| any | `varies` | **INFO** — outcome recorded but not scored |

The INFO rows cut across all layers — a prompt can be `layer: llama_guard` or
`layer: model` and still be INFO if its expected outcome is `varies`. In the
actual output, six prompts are INFO: four with `layer: llama_guard` and two
with `layer: model`.

The INFO rows are the most important column to study. They identify attack
surfaces where the current guard stack gives no guaranteed answer.

### Step 3: Identify the Coverage Gap

Look at the LAYER column for INFO rows. The six INFO rows in the output come
from two groups:

- **`layer: llama_guard` (four rows)** — prompts that bypass the regex and may
  or may not be caught by Llama Guard depending on phrasing. The outcome is
  genuinely uncertain without running the model.
- **`layer: model` (two rows)** — prompts where no input guard blocks the
  request; the only defence is model-level reasoning or an application
  control (such as the iteration cap). These are documented gaps, not
  misconfigurations.

Open one of the `llama_guard` INFO rows — for example:

```bash
cat prompts/llm07_system_prompt_leakage/leakage-001.yaml
```

Read the `notes:` field. It explains exactly why the regex doesn't catch this
prompt and what the remaining defence is.

> **This is the most important output of `bench.py --regex-only`:** it shows
> which prompts have no guaranteed block at the guard layer. These are your
> coverage gaps — the attack surfaces a motivated adversary would probe first.

### Step 4: Full Guard Stack Scan

Now run the harness with the full guard stack. This calls `llama-guard3` for
every prompt that passes the regex:

```bash
python bench.py
```

Compare the INFO rows from Step 2 to this run. Some `layer: llama_guard`
prompts that were INFO (outcome unknown) are now scored against the actual
Llama Guard response. A PASS means Llama Guard blocked them; a FAIL means they
reached the agent unguarded.

Note the timing difference — the full scan takes several seconds per
`llama-guard3` inference call, versus 0.15s for the regex-only scan.

### Step 5: Filter to a Single Category

Use the `--category` flag to focus on one OWASP risk:

```bash
python bench.py --category LLM01
python bench.py --category LLM07
```

Compare the two summaries. LLM01 prompts have a higher `regex` hit rate
(explicit override phrases are common and detectable by pattern). LLM07
(system prompt leakage) has mostly `layer: model` and `layer: llama_guard`
prompts — the regex offers less coverage because leakage payloads are often
phrased as normal curiosity.

### Step 6: Filter to a Single Layer

Run only the prompts expected to be caught at the regex layer:

```bash
python bench.py --regex-only --layer regex
```

All of these should be PASS. If any are FAIL, a regex pattern has regressed
or was removed — this is a breaking change that bench.py would catch in CI.

Now run the complement — prompts expected to pass the regex:

```bash
python bench.py --regex-only --layer none
```

These should all be PASS (outcome `passes`). A FAIL here means the regex
generated a false positive — a benign-looking prompt was incorrectly blocked.

### Step 7: JSON Output for CI Integration

`bench.py` exits with code `0` if all scored prompts pass, and non-zero if
any fail. This makes it directly usable as a CI gate:

```bash
python bench.py --regex-only --json --output bench_results.json
echo "Exit code: $?"
```

Open `bench_results.json` and locate the `summary` block:

```json
{
  "summary": { "pass": 9, "fail": 0, "skip": 11, "info": 6 },
  "config":  { "regex_only": true, "guard": false, ... },
  "results": [ ... ]
}
```

Each entry in `results` has `id`, `category`, `layer`, `expected`, `actual`,
`status`, and `elapsed` — the same fields that appear in the table output.
A downstream script or CI dashboard can consume this to track guard coverage
over time.

---

## Expected Output / What to Look For

- `--regex-only` completes in under 0.2 seconds — the entire regex pre-filter
  test suite runs without any Ollama model loaded.
- `layer: regex` prompts are PASS — the pre-filter catches the known attack
  patterns reliably.
- `layer: none` prompts are PASS with `actual: passes` — these attacks bypass
  all guard layers and reach the agent. They are not failures; they are
  documented gaps that require model-level or application-level mitigations.
- INFO rows are not scored but are the most instructive: they mark the boundary
  between "guaranteed block" and "depends on the model".
- Full guard scan adds llama-guard3 coverage for the INFO rows — some convert
  to PASS (Llama Guard blocked), some remain varies.

---

## Discussion Questions

1. The harness skips prompts with `rag: true` because ChromaDB must be
   populated to run them. A complete coverage measurement would include RAG
   injection vectors (LLM08). What would need to change in bench.py to support
   RAG prompts — and what setup step would the harness need to perform or verify
   before running them?

2. Six prompts are marked `guard_expected: varies`. These are honest
   acknowledgements that the guard outcome is not deterministic — it depends on
   model version, temperature, and Llama Guard fine-tuning. In a production
   system, how would you turn a `varies` prompt into a `blocked` one? What
   would you have to add or change?

3. `bench.py` exits non-zero on FAIL — suitable for a CI gate on `--regex-only`
   (no Ollama needed). However, the full guard scan requires `llama-guard3`
   running in CI, which adds ~6 GB of model weight and significant inference
   latency. Design a two-tier CI strategy: a fast gate that runs on every push,
   and a slower gate that runs on PR merges or nightly. Which prompts belong in
   each tier, and what coverage does each tier provide?

4. The `layer: none` prompts — XSS payload, shell command, indirect file
   injection — are PASS with `actual: passes`, meaning no guard catches them.
   Look at the notes in one of these YAML files (e.g.
   `prompts/llm05_output_handling/output-001.yaml`). The vulnerability is
   described as a downstream application problem, not an LLM problem. What does
   this tell you about the limits of prompt-level guardrails as a security
   strategy?

---

**Next lab:** [Lab 3.1 — Enabling Llama Guard 3 on Inputs](lab3_1_llama_guard_inputs.md) *(loop back to review what has changed now that you have quantitative coverage data)*
