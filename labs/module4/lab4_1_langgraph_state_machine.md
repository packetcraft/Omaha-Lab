# Lab 4.1 — Reading the LangGraph State Machine

**Module:** 4 — Architecture & Framework Deep Dive
**Estimated time:** 35 minutes
**Prerequisite:** [Lab 1.3 — Reading the ReAct Trace](../module1/lab1_3_react_trace.md) completed.
No prior LangGraph knowledge required.

> **This lab is read + modify.** You will make small, safe changes to the code,
> run the agent, observe the effect, then restore the original. Each change is
> one or two lines — no architecture knowledge needed to follow along.

> **Before you start — back up `graph.py`.**
> Steps 4 and 6 both modify `graph.py`. Take a backup now so you can restore
> with a single command instead of manually reverting edits:
> ```bash
> cp graph.py graph.py.bak        # macOS / Git Bash
> copy graph.py graph.py.bak      # Windows cmd
> ```
> `git status` will show `graph.py.bak` as untracked during the lab — ignore it.

---

## Objective

Open `graph.py` and `state.py` and trace exactly how a user message travels
from entry point to response. By the end you will be able to: name every node
in the graph, explain what triggers each routing decision, and predict which
path a message will take before running the agent.

---

## Background: State Machines in One Paragraph

LangGraph models an agent as a **directed graph**: boxes (nodes) connected by
arrows (edges). Each node is a Python function that reads from a shared
dictionary — `AgentState` — and writes updates back to it. LangGraph merges
those updates and decides which node runs next. The agent is not a loop in the
traditional sense; it is a graph that LangGraph *walks* one node at a time
until it reaches `END`.

This is the same mental model as FOUNDATIONS.md's harness layer, made concrete
in code.

---

## Step 1: Read the State — `state.py`

Open `state.py`. It is short — 17 lines. Every field is a slot in the shared
dictionary that all nodes read from and write to.

```python
class AgentState(TypedDict):
    messages: Annotated[list[BaseMessage], add_messages]
    rag_context: str
    retrieved_chunks: list
    guard_blocked: bool
    reasoning: str
```

**Questions to answer before moving on:**

1. `messages` uses `Annotated[list[BaseMessage], add_messages]`. The
   `add_messages` annotation means LangGraph *appends* new messages rather than
   replacing the list. Why does that matter for a multi-turn conversation?

2. `guard_blocked` is a plain `bool`. Find where it is set to `True` in
   `graph.py`. Which node sets it, and what happens immediately after?

3. `reasoning` is set by `reason_node` and cleared by `agent_node`
   (`"reasoning": ""`). Why clear it after the agent node consumes it?

---

## Step 2: Find the Entry Point — `graph.py` lines 213–222

Scroll to the bottom of `graph.py`. The entry point is not fixed — it shifts
based on which components are active:

```python
if guard is not None:
    graph.set_entry_point("guard_input")
elif retriever is not None:
    graph.set_entry_point("rag")
elif tools:
    graph.set_entry_point("reason")
else:
    graph.set_entry_point("agent")
```

**Exercise:** For each CLI command below, write down which node will be the
entry point *before running the agent*:

| Command | Entry point |
|---|---|
| `python agent.py` | ? |
| `python agent.py --guard on` | ? |
| `python agent.py --rag on` | ? |
| `python agent.py --guard on --rag on` | ? |

Run each command, send a single message ("hi"), then check your answers against
the `[REASON]` / `[Guard]` lines in the CLI output.

---

## Step 3: Find the Routing Function — `graph.py` lines 92–98

The `should_continue` function is a **conditional edge** — it runs after every
`agent_node` call and returns a string that tells LangGraph which node to visit
next:

```python
def should_continue(state: AgentState) -> str:
    last = state["messages"][-1]
    if hasattr(last, "tool_calls") and last.tool_calls:
        return "hitl" if hitl else "tools"
    if presidio_guard is not None:
        return "output_guard"
    return END
```

Three possible outcomes:

| Return value | When | What happens next |
|---|---|---|
| `"hitl"` | Tool call requested + `--hitl on` | HITL node asks for human approval |
| `"tools"` | Tool call requested, no HITL | Tool executes immediately |
| `"output_guard"` | No tool call + guard active | Presidio scans the response |
| `END` | No tool call, no guard | Response delivered directly |

**Question:** What would happen if `should_continue` returned `"reason"`
instead of `"tools"`? Would that cause an infinite loop, or would the graph
terminate? Why?

---

## Step 4: Modify + Observe — Watch the Router Fire

Add a `print` before each `return` in `should_continue`. The structure stays
identical to Step 3 — only the first branch needs a variable because the route
value is computed inline:

```python
def should_continue(state: AgentState) -> str:
    last = state["messages"][-1]
    if hasattr(last, "tool_calls") and last.tool_calls:
        print(f"\n[ROUTER] → {'hitl' if hitl else 'tools'}")  # ← add this line
        return "hitl" if hitl else "tools"
    if presidio_guard is not None:
        print("\n[ROUTER] → output_guard")                     # ← add this line
        return "output_guard"
    print("\n[ROUTER] → END")                                  # ← add this line
    return END
```

Run the agent with two different messages:

```bash
python agent.py
```

```
You: What is 12 × 14?
You: What is the weather in Denver?
```

**What to look for:**

- The arithmetic question has no tool call — `[ROUTER]` should print `END`.
- The weather question triggers `get_weather` — `[ROUTER]` should print
  `tools`, then fire again after the tool result with `END` or `output_guard`.

Notice that `[ROUTER]` fires *twice* for the weather question — once to route
to `tools`, and once after `tools` returns and `agent_node` runs the synthesis
turn.

**Restore:** Copy the backup back before moving on to Step 5:
```bash
cp graph.py.bak graph.py        # macOS / Git Bash
copy graph.py.bak graph.py      # Windows cmd
```

---

## Step 5: Draw the Graph

Using what you have read, draw the node graph for the **Full Defense**
configuration (`--guard on --rag on --hitl on`). Use boxes for nodes and
arrows for edges. Label conditional edges with their return values.

Expected nodes: `guard_input`, `rag`, `reason`, `agent`, `hitl`, `tools`,
`output_guard`, `END`.

Compare your drawing against the Chainlit topology card for the Full Defense
profile (`chainlit run ui.py` → select Full Defense). They should match.

---

## Step 6: Modify + Observe — Add a Node

Add a minimal logging node between `reason` and `agent` that prints the
reasoning text to the terminal. This is a safe, additive change — it does not
alter any state, only prints.

In `graph.py`, inside `build_graph`, add after the `reason_node` definition:

```python
def log_reasoning_node(state: AgentState) -> dict:
    print(f"\n[LAB4] reason_node produced: {state.get('reasoning', '')[:120]}")
    return {}   # return empty dict — no state changes
```

Wire it into the graph. In the **Graph assembly** block (around line 205),
find this section:

```python
    if tools:
        graph.add_node("reason", reason_node)
        graph.add_edge("reason", "agent")        # ← remove this line
        graph.add_node("tools", ToolNode(tools))
        graph.add_edge("tools", "agent")
```

Remove the one marked line and put three lines in its place:

```python
    if tools:
        graph.add_node("reason", reason_node)
        graph.add_node("log_reasoning", log_reasoning_node)  # ← add
        graph.add_edge("reason", "log_reasoning")            # ← add
        graph.add_edge("log_reasoning", "agent")             # ← add
        graph.add_node("tools", ToolNode(tools))
        graph.add_edge("tools", "agent")
```

Run the agent and send a tool-calling question:

```
You: What is the weather in Denver?
```

You should see `[LAB4]` output the reasoning text between `[REASON]` and `[ACT]`.

**Restore:** Copy the backup back and delete it:
```bash
cp graph.py.bak graph.py && rm graph.py.bak        # macOS / Git Bash
copy graph.py.bak graph.py && del graph.py.bak     # Windows cmd
```

---

## Discussion Questions

1. `MemorySaver` (line 224) is the checkpointer passed to `graph.compile()`.
   It keeps conversation history in memory across turns using `thread_id`. What
   would happen to conversation history if you restarted `agent.py`? What would
   you need to change to make history persist across restarts?

2. `reason_node` is only defined when `tools` is non-empty (line 56:
   `if tools:`). If you ran the agent with an empty tool list, which node would
   be the entry point and what would the graph look like?

3. In Step 4 you saw `should_continue` fire twice for a tool-calling turn. If
   a tool call triggered another tool call (a chain of tools), how many times
   would `should_continue` fire? Trace it on the graph you drew in Step 5.

4. The `after_guard` routing function (lines 137–144) checks three conditions
   in order: `guard_blocked → END`, `retriever → rag`, `tools → reason`. What
   would happen if you swapped the `retriever` and `tools` checks? Would the
   graph still work correctly?

---

**Next:** [Lab 4.2 — LangChain Tools: The `@tool` Decorator](lab4_2_tool_decorator.md)
— now that you can read the graph, Lab 4.2 opens the tool registry and shows
how tools are defined, selected, and called via the Ollama tools API.
