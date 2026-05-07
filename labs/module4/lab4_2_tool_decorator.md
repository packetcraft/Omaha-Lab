# Lab 4.2 — LangChain Tools: The `@tool` Decorator

**Module:** 4 — Architecture & Framework Deep Dive
**Estimated time:** 30 minutes
**Prerequisite:** [Lab 4.1 — Reading the LangGraph State Machine](lab4_1_langgraph_state_machine.md) completed.

> **This lab is read + modify.** You will add a new tool to the registry,
> assign it a risk level, and watch HITL intercept it. Each change is small
> and fully reversible. Back up the files you will edit before starting.

> **Before you start — back up the files you will modify.**
> ```bash
> cp tools/file_ops.py tools/file_ops.py.bak     # macOS / Git Bash
> copy tools\file_ops.py tools\file_ops.py.bak   # Windows cmd
> ```

---

## Objective

Open the `tools/` directory and trace how a Python function becomes a
LangChain tool, how its JSON schema is generated automatically, how the agent
selects it, and how HITL uses the risk registry to decide whether to pause
execution. By the end you will be able to add a new tool from scratch and
control its authorization tier.

---

## Background: How the Agent Calls Tools

When the agent node runs, it calls the LLM with tools *bound* to the model
via `llm.bind_tools(tools)`. The LLM does not execute code — it returns a
structured `tool_calls` field on the `AIMessage` that names the tool and
supplies JSON arguments. LangGraph routes that message to `ToolNode`, which
looks up the function by name and calls it.

The `@tool` decorator is the bridge. It wraps a plain Python function in a
`StructuredTool` that carries:

- **name** — the function name (what the LLM uses to select it)
- **description** — the docstring (what the LLM reads to decide *when* to use it)
- **args_schema** — a Pydantic model auto-generated from the function signature

The agent never sees the Python source. It only sees the name, description,
and parameter schema — the same JSON the LLM receives at inference time.

---

## Step 1: Read a Tool Definition — `tools/weather.py`

Open `tools/weather.py`. The entire tool is 47 lines. Focus on three things:

1. **The decorator** — `@tool` on line 8 is the only annotation needed. The
   function name (`get_weather`) becomes the tool name. The docstring becomes
   the description the LLM reads.

2. **The signature** — `def get_weather(city: str) -> str`. One parameter,
   type-annotated. LangChain generates the args schema from this signature.
   If you added a second parameter `units: str = "imperial"`, it would appear
   in the schema automatically.

3. **The return value** — plain string. Every tool must return a string. That
   string becomes the `ToolMessage.content` the agent reads in its next turn.

**Question:** The docstring says "Returns temperature (°F), conditions,
humidity, and wind speed." The LLM reads this to decide when to call the tool.
What would happen if the docstring said "Returns stock prices"? Would the agent
still call it for weather questions?

---

## Step 2: Read the Allow-list Tool — `tools/http_request.py`

Open `tools/http_request.py`. This tool demonstrates two security patterns you
will encounter in production agents:

**Pattern A — Domain allow-list (lines 7–19):**
```python
_ALLOWED_DOMAINS: set[str] = {
    "api.openweathermap.org",
    "wttr.in",
    "httpbin.org",
    ...
}
```
The tool rejects any URL whose domain is not in this set. The LLM cannot call
arbitrary URLs — only the pre-approved list. An extra environment variable
(`HTTP_ALLOWED_DOMAINS`) extends the list at runtime without code changes.

**Pattern B — Response truncation (line 52):**
```python
if len(body) > _RESPONSE_LIMIT:
    body = body[:_RESPONSE_LIMIT] + "\n... (truncated)"
```
Large responses are cut off before reaching the agent's context window. This
limits both token costs and data exfiltration surface.

**Question:** `http_get` is marked `"low"` risk in `tools/risk_registry.py`
because it is GET-only with no side effects. If you added an `http_post` tool,
what risk level would you assign and why?

---

## Step 3: Read the Risk Registry — `tools/risk_registry.py`

Open `tools/risk_registry.py`. It is 11 lines:

```python
RISK_LEVEL: dict[str, str] = {
    "get_weather": "low",
    "web_search":  "low",
    "http_get":    "low",
    "read_file":   "low",
    "write_file":  "high",
}
```

This dictionary is the sole input to the HITL decision. Open
`graph_nodes/hitl_node.py` and find line 45:

```python
risk = RISK_LEVEL.get(name, "low")
```

The `.get(name, "low")` default means any tool *not in the registry* is
treated as low-risk. That is intentional — new tools are assumed safe until
explicitly elevated. The alternative (default-to-high) would cause HITL to
intercept every new tool until its entry is added.

**Question:** Which default is safer for a production system — `"low"` or
`"high"`? What is the operational cost of each choice?

---

## Step 4: Inspect the Generated Schema

Run this one-liner to print the schema the LLM receives for each tool:

```bash
python - <<'EOF'
from tools import TOOLS
for t in TOOLS:
    print(f"\n=== {t.name} ===")
    print(t.description)
    if hasattr(t, 'args_schema') and t.args_schema:
        print("Parameters:", t.args_schema.schema())
EOF
```

Expected output for `write_file`:
```
=== write_file ===
Write content to a file in the workspace sandbox directory. ...
Parameters: {'properties': {'filename': {'title': 'Filename', 'type': 'string'},
 'content': {'title': 'Content', 'type': 'string'}}, 'required': ['filename', 'content'], ...}
```

This is the JSON the LLM model sees at inference time. The model uses
`"required"` to know which arguments it must supply before calling the tool.

---

## Step 5: Add a New Tool

Add a `list_files` tool that lists the filenames in the workspace sandbox.
Open `tools/file_ops.py` and add after the existing `write_file` function:

```python
@tool
def list_files() -> str:
    """List the names of all files currently in the workspace sandbox directory."""
    try:
        files = [p.name for p in WORKSPACE.iterdir() if p.is_file()]
        if not files:
            return "workspace/ is empty."
        return "\n".join(sorted(files))
    except OSError as exc:
        return f"Error listing workspace: {exc}"
```

Then register it in `tools/__init__.py`. Open that file and add `list_files`
to the import and to the `TOOLS` list:

```python
from tools.file_ops import read_file, write_file, list_files   # ← add list_files

TOOLS = [get_weather, web_search, http_get, read_file, write_file, list_files]
```

Also add it to `tools/risk_registry.py`:

```python
"list_files":  "low",
```

Run the agent and ask it to list the workspace contents:

```bash
python agent.py
```
```
You: What files are in the workspace?
```

You should see `[ACT] list_files({})` in the trace followed by an `[OBSERVE]`
line with the file listing (or "workspace/ is empty.").

---

## Step 6: Elevate to High-Risk and Test HITL

Change `list_files` to `"high"` in `tools/risk_registry.py`:

```python
"list_files":  "high",
```

Run the agent with HITL enabled:

```bash
python agent.py --hitl on
```
```
You: What files are in the workspace?
```

You should see the HITL prompt intercept before execution:
```
[HITL] High-risk action requested
  Tool : list_files
  Args : {}
[HITL] Approve this action? (yes/no):
```

Type `no`. The agent should respond that it was unable to list the files.
Type `yes` on a second attempt and confirm the listing arrives.

**Restore:** Revert to `"low"` in `risk_registry.py`. Restore `file_ops.py`:
```bash
cp tools/file_ops.py.bak tools/file_ops.py && rm tools/file_ops.py.bak
```
Remove the `list_files` import and entry from `tools/__init__.py` and
`risk_registry.py` manually (or restore those from the backup if you made one).

---

## Discussion Questions

1. In Step 4 you saw the schema that the LLM receives. The `description` field
   (from the docstring) is the primary signal the LLM uses to decide which tool
   to call. What is the security implication if an attacker can influence the
   tool registry (e.g., via a supply-chain compromise of a dependency that
   registers tools)?

2. `RISK_LEVEL.get(name, "low")` means unknown tools default to low-risk.
   Describe a specific attack scenario where an agent with this default would
   be exploited. How would you change the default to close that gap?

3. The `write_file` sandbox uses `Path.resolve()` and `.relative_to()` to
   prevent path traversal. Would the same protection work for `list_files` as
   written? Could a caller escape the sandbox using `list_files`? Why or why not?

---

**Next:** [Lab 4.3 — RAG Pipeline Internals](lab4_3_rag_pipeline.md) — now
that you understand the tool layer, Lab 4.3 opens the vector store and traces
a document from ingest to retrieval.
