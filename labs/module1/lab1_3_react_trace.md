# Lab 1.3 — Reading the ReAct Trace

**Module:** 1 — Foundations
**Estimated time:** 10 minutes
**Prerequisite:** [Lab 1.2](lab1_2_first_agent.md) — you should have seen at least one tool call in the trace.

---

## Objective

Understand the Reason → Act → Observe → Respond (ReAct) loop by reading the terminal trace, and connect each trace label to the corresponding step in the agent's decision cycle.

---

## Background: What Is a ReAct Loop?

A **ReAct agent** (Reasoning + Action) interleaves two phases:

1. **Reasoning** — the model decides what to do next, given the conversation history and any tool results it has seen so far.
2. **Acting** — the model emits a tool call, the tool runs, and its output is fed back to the model as an observation.

This loop repeats until the model decides it has enough information to respond without another tool call.

```
User message
    │
    ▼
┌───────────────────┐
│  REASON           │  Model reads history + observations
│  → call a tool?   │
└──────┬──────┬─────┘
       │ yes  │ no
       ▼      ▼
  ┌──────┐  [RESPOND] — final answer to user
  │  ACT │  — tool is invoked
  └──┬───┘
     │
     ▼
┌──────────┐
│  OBSERVE │  — tool result returned to model
└──────┬───┘
       │
       └──────────────────────────────────────┐
                                              ▼
                                        REASON again
```

---

## Step 1: Produce a Multi-Step Trace

Start the agent and ask a question that forces two tool calls:

```bash
python agent.py
```

```
You: Search the web for the capital of Nebraska, then write the answer to a file called nebraska.txt in the workspace.
```

This should produce a trace similar to:

```
[ACT]     web_search({'query': 'capital of Nebraska'})
[OBSERVE] web_search: 1. Lincoln, Nebraska — Wikipedia
   https://en.wikipedia.org/wiki/Lincoln,_Nebraska
   Lincoln is the capital and most populous city of Nebraska...

[ACT]     write_file({'filename': 'nebraska.txt', 'content': 'The capital of Nebraska is Lincoln.'})
[OBSERVE] write_file: Wrote 35 characters to workspace/nebraska.txt

[RESPOND] Done! I searched the web and found that the capital of Nebraska is Lincoln.
I've saved that answer to workspace/nebraska.txt.
```

> **Tip:** If your model only calls one tool instead of two, try being more explicit: *"First search the web, then save the result."* Tool-calling behaviour varies between models and temperatures.

---

## Step 2: Annotate the Trace

Here is the same trace with each line explained:

```
[ACT]     web_search({'query': 'capital of Nebraska'})
```
↳ The model issued a tool call. `web_search` is the tool name; `{'query': '...'}` are the arguments the model chose.

```
[OBSERVE] web_search: 1. Lincoln, Nebraska — Wikipedia ...
```
↳ The tool ran and returned this text. The model reads this as its next input — it hasn't spoken to the user yet.

```
[ACT]     write_file({'filename': 'nebraska.txt', 'content': '...'})
```
↳ After reading the search result, the model decided it needed a second action. It's still reasoning — the user hasn't seen a response yet.

```
[OBSERVE] write_file: Wrote 35 characters to workspace/nebraska.txt
```
↳ The second tool confirms success. The model now has all the information it needs.

```
[RESPOND] Done! I searched the web and found that the capital of Nebraska is Lincoln...
```
↳ Only now does the model produce the user-visible answer, synthesising both observations.

---

## Parallel Tool Calling — When Two `[ACT]` Lines Appear Before Any `[OBSERVE]`

You may see a trace like this instead of the sequential one above:

```
[ACT]     web_search({'query': 'capital of Nebraska'})
[ACT]     write_file({'filename': 'nebraska.txt', 'content': 'The capital of Nebraska is Lincoln.'})
[OBSERVE] web_search: 1. Lincoln, Nebraska — Wikipedia ...
[OBSERVE] write_file: Wrote 35 characters to workspace/nebraska.txt

[RESPOND] The capital of Nebraska is Lincoln. I've saved it to nebraska.txt.
```

Both `[ACT]` lines come before either `[OBSERVE]` line. This is **parallel tool calling** — the model packed both tool calls into a single `AIMessage` (as two entries in the `tool_calls` list) rather than waiting to see the search result first.

**Why did it do that?** qwen2.5:7b already knew Nebraska's capital from training data, so it could fill in `write_file`'s `content` argument without waiting for the search. It reasoned that both calls were independent and dispatched them together.

**When does parallel vs. sequential happen?**

| Situation | Expected pattern |
|---|---|
| Second call's arguments depend on the first result | Sequential: `[ACT] → [OBSERVE] → [ACT] → [OBSERVE]` |
| Second call's arguments are known in advance | Parallel: `[ACT] [ACT] → [OBSERVE] [OBSERVE]` |

**How it maps to the code:** `ToolNode` receives the `AIMessage` with multiple `tool_calls`, executes all of them, and appends one `ToolMessage` per call to the state. The next `agent_node` invocation sees all observations at once.

The security implication: when the model pre-fills arguments without observing real data, those arguments come entirely from model weights — not from the live tool result. In this case that's harmless, but if the prompt were asking the model to write *untrusted external content* to a file, pre-filling without observing could bypass an output-validation step. Lab 2.7 explores this pattern.

### Try it: catch the model writing stale data

Ask about a topic where the model's training data is likely outdated:

```
You: Search the web for the Artemis II mission date, then write the answer to a file called test.txt in the workspace.
```

If the trace is parallel, check what actually landed in the file:

```bash
cat workspace/test.txt
```

Compare that to what the `[OBSERVE]` from `web_search` returned and what the `[RESPOND]` said.

**What you will likely find:** the file contains the date from the model's training data (which may be wrong or outdated), while the `[RESPOND]` correctly quotes the live search result. The model updated its answer after seeing the observation — but it never went back to fix the file it had already written.

This is the concrete failure mode: **the response is correct, the side-effect is silently wrong.** From a user's perspective the agent looks like it worked. The bad data is sitting in `workspace/test.txt` without any error or warning.

---

## Step 3: Understand What the Model Actually Sees

Each time the model reasons, it receives the **full conversation history** — every message, tool call, and tool result in sequence. Open `graph.py` and find `agent_node`:

```python
def agent_node(state: AgentState) -> dict:
    messages = list(state["messages"])
    ...
    response = llm_with_tools.invoke(prefix + messages)
    return {"messages": [response]}
```

The `messages` list grows with every step. Before the second `[ACT]` in the trace above, the model received:

1. System prompt (if persona is active)
2. `HumanMessage` — your original question
3. `AIMessage` — the first tool call decision
4. `ToolMessage` — the web search result

That full context is what drove the model to call `write_file` next.

---

## Step 4: Observe a Reasoning Prefix (Optional)

Some models emit visible reasoning before a tool call. Ask a more open-ended question:

```
You: I need to know today's Bitcoin price. Can you help?
```

If the model narrates its reasoning, you will see:

```
[REASON]  I need to look up the current Bitcoin price. I'll use the http_get tool
          to check a public price API.
[ACT]     http_get({'url': 'https://api.coindesk.com/v1/bpi/currentprice.json'})
[OBSERVE] http_get: {"time":{"updated":"..."},"bpi":{"USD":{"rate":"62,145.50",...}}}

[RESPOND] The current Bitcoin price is approximately $62,145 USD according to CoinDesk.
```

The `[REASON]` line appears when `AIMessage.content` is non-empty alongside a tool call. Not all models produce visible reasoning — `llama3.1:8b` does intermittently; `phi3:mini` typically does not.

---

## Step 5: Watch a Short-Circuit (No Tool Needed)

```
You: What is 12 multiplied by 8?
```

```
[RESPOND] 12 multiplied by 8 is 96.
```

No tool calls. The model answered from its own weights. The graph went: `agent_node → END`, skipping the tools node entirely.

---

## The Five Trace Labels — Summary

| Label | Meaning | Emitted by |
|---|---|---|
| `[REASON]` | Model narrated its thinking before a tool call | `agent_node` — when `AIMessage` has both content and tool calls |
| `[ACT]` | A tool was called with these arguments | `agent_node` — when `AIMessage` has tool calls |
| `[OBSERVE]` | The tool returned this result | `tools` node — `ToolMessage` |
| `[RESPOND]` | Final answer to the user | `agent_node` — when `AIMessage` has no tool calls |
| `[RETRIEVE]` | A RAG chunk was fetched (only when `--rag on`) | `rag` node — shown before `[RESPOND]` |

---

## Discussion Questions

1. If the web search returns incorrect information, the model will relay that incorrect answer to the user. Where in the ReAct loop does this hallucination risk live? What does the Observe step change — and what doesn't it fix?

2. The trace shows the model calling `write_file` with arguments it constructed from the `web_search` result. What would happen if the search result contained a malicious file path or content? (This is **OWASP LLM05 — Improper Output Handling**, covered in Lab 2.7.)

3. The `[OBSERVE]` content is truncated to 2,000 characters by `http_get`. Why is that limit important? What could happen without it? (This connects to **OWASP LLM10 — Unbounded Consumption**, covered in Lab 2.9.)

4. Look at the `should_continue` function in `graph.py`. What happens if `tool_calls` is never empty? Does the current code have a loop limit? (Spoiler: it does not — that's added in Stage 8 / Lab 3.7.)

---

**Next lab:** [Lab 1.4 — Loading a Persona](lab1_4_persona.md)
