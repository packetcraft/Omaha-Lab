# Lab 3.7 — Iteration Limits and Rate Control

**Module:** 3 — Defensive Architecture
**OWASP Risk:** LLM10 — Unbounded Consumption
**Estimated time:** 20 minutes
**Prerequisite:** [Lab 3.6 — Scoping Tool Permissions per Persona](lab3_6_tool_scoping.md)

---

## Objective

Understand how LangGraph's recursion limit acts as a last-resort loop guard, configure a lower explicit limit to stop runaway agents sooner, and discuss token budget enforcement and rate-limiting strategies for production deployments.

---

## Background

Lab 2.9 showed that a runaway agent will hit LangGraph's default recursion limit of 25 steps and raise a `GraphRecursionError`. This is a safety net — not a design goal. Each of the 25 steps before the error consumed CPU, memory, and inference time.

A well-defended system should apply loop protection at multiple layers:
1. **Recursion limit** — LangGraph default (25) or custom configured; hard stop.
2. **Iteration counter in the agent node** — tracks agent invocations within a single conversation turn and refuses to continue beyond a threshold.
3. **Token budget** — limits `num_ctx` or `max_tokens` at the Ollama level.
4. **Rate limiting** — limits the number of requests per time window at the API gateway level.

This lab configures a custom recursion limit and discusses the other layers.

---

## Setup

```bash
python agent.py
```

---

## Steps

### Step 1: Re-Run the Lab 2.9 Loop Attack

Without any changes, observe the default recursion limit:

```
You: Search the web for the current search results, then search for those results again, and keep searching until you find the definitive answer to everything.
```

Count the `[ACT]` / `[OBSERVE]` pairs before the error appears. The error message should reference the limit of 25:

```
GraphRecursionError: Recursion limit of 25 reached without hitting a stop condition.
```

Note the timestamp from the first `[ACT]` to the error — this is how long 25 wasted steps took.

### Step 2: Inspect the Iteration Counter in state.py and graph.py

Open `state.py`. Find the `iteration_count` field:

```python
# Number of agent_node invocations in the current session; enforces max_iterations cap.
iteration_count: int
```

Now open `graph.py` and find `agent_node`. Near the top of the function:

```python
count = (state.get("iteration_count") or 0) + 1
```

And near the bottom, the cap enforcement:

```python
if count >= max_iterations and getattr(response, "tool_calls", None):
    print(f"\n[ITER LIMIT] Maximum iterations ({max_iterations}) reached — stopping tool calls.")
    response = AIMessage(content=...)
```

This is the application-level cap. It replaces the agent's tool-calling response with a graceful message when the limit is hit, so `should_continue` routes to END instead of looping back through the tools node. LangGraph's `GraphRecursionError` is still a last-resort safety net, but the application cap fires first.

### Step 3: Configure a Lower Limit with `--max-iterations`

The default cap is 10 steps. Pass `--max-iterations N` to lower it:

```bash
python agent.py --max-iterations 3
```

The startup banner now shows:
```
Iterations:      3 max per session
```

Repeat the loop prompt from Step 1 with the lower limit:

```
You: Search the web for the current search results, then keep searching forever.
```

### Step 4: Observe the Graceful Cutoff

With `--max-iterations 3`, the agent makes at most 3 `web_search` calls before
the cap fires:

```
[ACT]     web_search(...)
[OBSERVE] web_search: ...
[ACT]     web_search(...)
[OBSERVE] web_search: ...
[ACT]     web_search(...)
[OBSERVE] web_search: ...

[ITER LIMIT] Maximum iterations (3) reached — stopping tool calls.

[RESPOND] I have reached the maximum number of steps (3) and cannot make
          further tool calls. Please try a more focused question.
```

Unlike the `GraphRecursionError` in Step 1, this produces a human-readable
response the user can act on. Compare the elapsed time to Step 1.

### Step 5: Token Budget Discussion

Open a second terminal and inspect the `ChatOllama` configuration in `graph.py`:

```bash
grep -n "num_ctx\|max_tokens\|ChatOllama" graph.py
```

The `num_ctx` parameter limits the model's context window. The `max_tokens` (or `num_predict` in Ollama) limits the number of tokens generated per response. These can be configured at model initialization:

```python
llm = ChatOllama(
    model=model_name,
    num_ctx=4096,     # Maximum context window
    num_predict=512,  # Maximum tokens per response
)
```

A `num_predict=512` limit would prevent the "token bomb" response from Lab 2.9 Step 4 — the model would truncate at 512 tokens rather than generating 1,000 repetitions.

### Step 6: Rate Limiting — Conceptual Discussion

Ollama exposes its API on `http://localhost:11434`. In a production multi-user deployment, you would place a reverse proxy (nginx, Caddy, or an API gateway like Kong or Apigee) in front of Ollama that enforces:

- **Requests per minute per user** — e.g., max 10 agent invocations per minute
- **Concurrent request limit** — e.g., max 2 simultaneous inference calls
- **Token budget per day** — e.g., max 100,000 tokens consumed per user per day

None of these are configured in the current Omaha-Lab setup (it is a local single-user lab). Document what you would add in the space below the rate-limiting grep:

```bash
grep -rn "rate_limit\|RateLimit\|throttle" . --include="*.py"
```

Expected: no results — this is a gap to address in a production hardening exercise.

---

## Expected Output / What to Look For

- Default recursion limit (25) stops the loop but only after significant wasted work.
- A custom limit of 10 stops it sooner with less compute consumed.
- `num_predict` in ChatOllama bounds per-response token generation.
- No rate limiting is currently implemented — this is a known gap.

---

## Discussion Questions

1. The recursion limit raises `GraphRecursionError`, which in a production application would need to be caught and converted into a user-facing error message. What should the user-facing message say, and should it reveal that a recursion limit was hit?

2. Setting `recursion_limit=10` would also terminate legitimate multi-step tasks that require more than 10 steps — for example, a research agent that searches multiple sources and writes a detailed report. How would you distinguish between a legitimate deep task and a runaway loop?

3. Token budgets (via `num_predict`) operate at the model level, while recursion limits operate at the graph level. A prompt that causes the model to generate 2,000 tokens in a single `[RESPOND]` would not be caught by the recursion limit. What metric — tokens, steps, wall-clock time, or something else — is the most meaningful limit for preventing unbounded consumption?

---

**Next lab:** [Lab 3.8 — Supply Chain Hygiene: Verifying Ollama Models](lab3_8_supply_chain.md)
