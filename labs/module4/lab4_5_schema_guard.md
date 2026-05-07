# Lab 4.5 — Architecture Challenge: Schema Guard Integration

**Module:** 4 — Architecture & Framework Deep Dive
**Estimated time:** 40 minutes
**Prerequisite:** [Lab 4.1](lab4_1_langgraph_state_machine.md) and [Lab 4.4](lab4_4_guardrail_code.md) completed.

> **This lab is read + extend.** Unlike Labs 4.1–4.4 which guide you through
> existing, verified code, this lab asks you to understand an integration,
> audit it, and add a new validation rule. The integration is already in place;
> your job is to verify it works end-to-end and then extend it.

> **Before you start — back up `guardrails/schema_guard.py`.**
> ```bash
> cp guardrails/schema_guard.py guardrails/schema_guard.py.bak     # macOS / Git Bash
> copy guardrails\schema_guard.py guardrails\schema_guard.py.bak   # Windows cmd
> ```

---

## Objective

`guardrails/schema_guard.py` provides a `validate_tool_result()` function that
checks every tool return value for structural validity. Your tasks: read the
module, find where it is called in `graph.py`, verify the integration works,
identify its limitations, and extend it with a new validation rule.

---

## Background: Why Validate Tool Results?

Tools return strings. The agent trusts those strings completely — it
incorporates them into its reasoning without structural inspection. If a tool
returns an empty string, a Python exception traceback, or a JSON blob the
agent is not designed to parse, the agent may hallucinate, loop, or produce
garbled output.

Schema validation is a thin but important layer between `ToolNode` (which
executes the tool) and `agent_node` (which consumes the result). It does not
fix bad results — it surfaces them as observable signals so the operator knows
the tool misbehaved.

---

## Step 1: Read the Validator — `guardrails/schema_guard.py`

Open `guardrails/schema_guard.py`. It is 35 lines. The function
`validate_tool_result(tool_name, result)` applies three rules in order:

| Rule | Check | Violation example |
|---|---|---|
| Type check | `result` must be `str` | Tool returned `None` or `int` |
| Empty check | `result.strip()` must be non-empty | Tool returned `""` or `"   "` |
| JSON check | If `tool_name == "http_get"` and result starts with `{`, must be valid JSON | Truncated JSON response |

Each rule logs a warning via `logging.warning` and returns `(False, error_message)`.
A passing result returns `(True, None)`.

**Question:** The JSON check only fires for `http_get`. Why not check
`web_search` results too? What is the return format of `web_search` that makes
JSON validation inapplicable?

---

## Step 2: Find the Integration — `graph.py` output_guard_node

Open `graph.py` and search for `validate_tool_result`. You should find it
imported and called inside `output_guard_node`:

```python
from guardrails.schema_guard import validate_tool_result as _validate_tool

...

schema_violations: list[str] = []
for m in msgs:
    if isinstance(m, ToolMessage):
        ok, err = _validate_tool(getattr(m, "name", "tool"), m.content)
        if not ok:
            schema_violations.append(err)
```

This loop runs over **all** `ToolMessage`s in `state["messages"]`. Because
`MemorySaver` accumulates messages across turns, this includes tool results
from previous turns in the same session, not just the current turn.

**Question:** Is this a problem? Consider a session where the agent calls
`write_file` on turn 1 (result: `"Wrote 42 characters to workspace/out.txt"`)
and then asks a question on turn 2 that calls no tools. On turn 2, will
`schema_violations` be empty or non-empty? Trace through the loop.

---

## Step 3: Verify the Integration End-to-End

Run the agent with guard enabled and trigger a tool call:

```bash
python agent.py --guard on
```
```
You: What is the weather in Denver?
```

At the end of the turn, look for the guard receipt line:

```
[Guard] input: pass | presidio: clean | canary: clean | schema: clean
```

The `schema: clean` entry confirms the integration is live and `validate_tool_result`
ran on the `get_weather` result. If the guard receipt does not include
`schema:`, the `output_guard` node is not firing — check that `--guard on` is
set (Presidio must be active for `output_guard_node` to run).

---

## Step 4: Deliberately Trigger a Violation

The existing rules are hard to trigger with the live tools because all five
tools return non-empty strings. To observe a violation signal, temporarily
add a failing rule that triggers on any result longer than 200 characters.

Open `guardrails/schema_guard.py` and add after the empty-string check:

```python
if len(result) > 200:
    msg = f"{tool_name} result exceeds 200 chars ({len(result)} chars) — possible data flood"
    logger.warning("Schema validation failed: %s", msg)
    return False, msg
```

Restart the agent with guard and ask for a web search (results are typically
200+ characters):

```bash
python agent.py --guard on
```
```
You: Search the web for LangGraph examples
```

The guard receipt should now show:

```
[Guard] input: pass | presidio: clean | canary: clean | schema: 1 violation(s)
```

The violation is logged to your terminal via `logging.warning` (visible if
your log level is WARNING or lower). The agent's response is not blocked —
schema violations are **observability signals**, not hard blocks, by design.

**Note:** Remove the 200-character rule before moving to Step 5. It would flag
nearly every useful tool result in normal operation.

---

## Step 5: Add a Meaningful Validation Rule

With the test rule removed, add a rule that catches a real failure mode:
tool results that contain a Python exception traceback. This can happen when a
tool's internal error handling is incomplete.

Add after the empty-string check in `validate_tool_result`:

```python
if "Traceback (most recent call last)" in result:
    msg = f"{tool_name} returned an unhandled exception traceback"
    logger.warning("Schema validation failed: %s", msg)
    return False, msg
```

This pattern is specific enough that it will not fire on normal results but
will catch any tool that accidentally leaks a Python stack trace.

**Test it** by temporarily modifying `tools/weather.py` to raise an unhandled
exception: in `get_weather`, replace the try/except block with a bare
`raise RuntimeError("simulated failure")`. Run with guard, send a weather
query, and confirm the guard receipt shows `schema: 1 violation(s)`. Then
restore `weather.py`.

**Restore schema_guard.py:**
```bash
cp guardrails/schema_guard.py.bak guardrails/schema_guard.py && rm guardrails/schema_guard.py.bak
```

---

## Step 6: Audit the Integration for the Multi-Turn Bug

Return to the question from Step 2: the validation loop scans *all*
`ToolMessage`s in state, not just those from the current turn. This means
a violation detected on turn 1 will be reported again on every subsequent
turn, even if no tool is called.

Confirm this:

1. On turn 1, cause a violation by temporarily keeping the 200-char rule from
   Step 4 and asking for a web search.
2. On turn 2, ask a simple arithmetic question ("What is 7 × 8?") that
   triggers no tool calls.
3. Observe whether `schema: 1 violation(s)` still appears on turn 2.

**Fix challenge (optional):** The `AgentState` does not currently track which
messages belong to the current turn. One approach: add a `turn_id` field to
`AgentState` and stamp each `ToolMessage` with the current turn. The
validation loop would then filter to only the current turn's messages.

Sketch the change — what fields would you add to `state.py`, and where in
`graph.py` would you increment `turn_id`? You do not need to implement it,
only describe it.

---

## Discussion Questions

1. Schema violations are logged but do not block the agent's response. Under
   what circumstances should a schema violation hard-block the response?
   Propose a new `severity` parameter for `validate_tool_result` that would
   support both blocking and non-blocking rules.

2. The type check rule (`isinstance(result, str)`) is currently unreachable for
   the five built-in tools because LangGraph's `ToolNode` calls
   `str(result)` on any non-string return value before creating the
   `ToolMessage`. Why is the check still worth keeping?

3. You found (Step 2 / Step 6) that the integration scans all historical
   `ToolMessage`s rather than only the current turn. This is a logic bug.
   Without changing `state.py`, describe an alternative filtering strategy
   using only the existing state fields to isolate current-turn tool results.

4. `validate_tool_result` is called inside `output_guard_node`, which only runs
   when `presidio_guard is not None` (i.e., `--guard on`). A student running
   `python agent.py` with no flags gets no schema validation. Is this the right
   gate? What would need to change to make schema validation available
   independently of the Presidio guard?

---

**Module 4 complete.** You have read the LangGraph state machine, the tool
registry, the RAG pipeline, the guardrail source, and audited a live
integration. Return to [Module 2](../module2/) or [Module 3](../module3/) with
this architectural knowledge to reread any lab from the code perspective.
