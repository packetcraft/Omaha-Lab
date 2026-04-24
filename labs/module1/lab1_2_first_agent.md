# Lab 1.2 — Your First Tool-Calling Agent

**Module:** 1 — Foundations
**Estimated time:** 15 minutes
**Prerequisite:** [Lab 1.1 — Environment Setup](lab1_1_environment_setup.md) complete and virtual environment active.

---

## Objective

Run the Omaha-Lab agent, send it a message that triggers a live tool call, and observe the full Reason → Act → Observe → Respond cycle in the terminal output.

---

## Background

The agent is a **LangGraph ReAct loop** connected to a local Ollama LLM. When you send it a message, the model can choose to call one of five registered tools before responding:

| Tool | What it does |
|---|---|
| `get_weather` | Fetches current weather from OpenWeatherMap by city name |
| `web_search` | Runs a DuckDuckGo search and returns the top 5 results |
| `http_get` | Makes a GET request to an allow-listed domain |
| `read_file` | Reads a file from the `workspace/` sandbox |
| `write_file` | Writes a file to the `workspace/` sandbox |

---

## Step 1: Start the Agent

Make sure your virtual environment is active, then run:

```bash
python agent.py
```

You should see the startup banner:

```
Omaha-Lab Agent  |  model: llama3.1:8b
Persona:         (none)
Tools:           get_weather, web_search, http_get, read_file, write_file
RAG:             off
──────────────────────────────────────────────────
Type 'quit' or 'exit' to stop.

You:
```

> **Using the fallback model?** Run `python agent.py --model phi3:mini` if you set `OLLAMA_MODEL=phi3:mini` in `.env`.

---

## Step 2: A Conversational (No Tool) Response

Start with a simple greeting or a question the model can answer from its training data:

```
You: hi
```

```
[RESPOND] Hi! How can I help you today?
```

Or a general knowledge question:

```
You: What is LangGraph?
```

```
[RESPOND] LangGraph is a Python library built on top of LangChain for creating
stateful, multi-step agentic workflows as directed graphs...
```

No `[ACT]` or `[OBSERVE]` lines appear — the model answered without calling any tool.

---

## Step 3: Trigger a Weather Tool Call

Now ask something that requires live data:

```
You: What is the weather like in Omaha right now?
```

If your `WEATHER_API_KEY` is configured, you will see the full ReAct trace:

```
[ACT]     get_weather({'city': 'Omaha'})
[OBSERVE] get_weather: Location:    Omaha, US
Temperature: 62°F (feels like 59°F)
Condition:   Overcast clouds
Humidity:    71%
Wind:        12 mph

[RESPOND] The current weather in Omaha is 62°F with overcast clouds.
The humidity is 71% and winds are around 12 mph — a cool, cloudy day.
```

> **No API key?** You will see `[OBSERVE] get_weather: Error: WEATHER_API_KEY is not set.` The agent will acknowledge the error and explain it cannot retrieve weather data. This is expected — move on to the next step.

---

## Step 4: Trigger a Web Search

Ask a question that benefits from a current web search:

```
You: Search the web for the latest Ollama release notes.
```

Expected trace:

```
[ACT]     web_search({'query': 'Ollama latest release notes'})
[OBSERVE] web_search: 1. Ollama v0.3.x Release Notes
   https://github.com/ollama/ollama/releases
   Ollama v0.3.12 adds support for...

[RESPOND] According to the latest release notes, Ollama v0.3.x includes...
```

---

## Step 5: Trigger a File Write + Read

Ask the agent to save and retrieve something:

```
You: Write a file called hello.txt in the workspace with the content "Hello from Omaha-Lab"
```

Expected trace:

```
[ACT]     write_file({'filename': 'hello.txt', 'content': 'Hello from Omaha-Lab'})
[OBSERVE] write_file: Wrote 20 characters to workspace/hello.txt

[RESPOND] Done! I've written "Hello from Omaha-Lab" to workspace/hello.txt.
```

Verify the file was created:

```bash
cat workspace/hello.txt
```

Output: `Hello from Omaha-Lab`

Now read it back through the agent:

```
You: Read the file hello.txt from the workspace.
```

```
[ACT]     read_file({'filename': 'hello.txt'})
[OBSERVE] read_file: Hello from Omaha-Lab

[RESPOND] The file workspace/hello.txt contains: "Hello from Omaha-Lab"
```

---

## Step 6: Test the Sandbox (Path Traversal Block)

Try to read a file outside the sandbox:

```
You: Read the file ../agent.py from the workspace.
```

Expected:

```
[ACT]     read_file({'filename': '../agent.py'})
[OBSERVE] read_file: Error: '../agent.py' escapes the workspace sandbox.

[RESPOND] I'm unable to read that file — it's outside the allowed workspace directory.
```

The path traversal is blocked at the tool level before any file system access occurs.

### How the sandbox works

Open `tools/file_ops.py` and find `_safe_path()` — the entire guard is three lines:

```python
target = (WORKSPACE / filename).resolve()   # 1. join and fully resolve
target.relative_to(WORKSPACE)               # 2. boundary check — raises ValueError if outside
return target                               # 3. safe to use
```

**What happens with `filename = "../agent.py"`:**

```
WORKSPACE           = C:\...\Omaha-Lab\workspace   (set at import time)
WORKSPACE / "../agent.py"  →  C:\...\workspace\..\agent.py
.resolve()          →  C:\...\Omaha-Lab\agent.py   (OS flattens the ..)
relative_to(WORKSPACE)  →  ValueError  ← agent.py is NOT inside workspace\
_safe_path returns None  →  tool returns the error string
```

**Why `.resolve()` is the critical step:**
Without it, a naive check like `filename.startswith("workspace/")` is trivially bypassed.
`.resolve()` asks the OS to flatten all `..` sequences and symlinks into a real absolute
path *before* the boundary check runs. After that, `relative_to()` is a simple
"is this path inside that directory?" test that can't be fooled.

**Inputs that are all blocked by the same three lines:**

| Input | Resolved path | Result |
|---|---|---|
| `../agent.py` | `Omaha-Lab\agent.py` | Blocked |
| `../../etc/passwd` | `C:\etc\passwd` | Blocked |
| `/etc/passwd` | `C:\etc\passwd` | Blocked |
| `sub/../../secret` | `Omaha-Lab\secret` | Blocked |
| `notes.txt` | `workspace\notes.txt` | Allowed |
| `sub/notes.txt` | `workspace\sub\notes.txt` | Allowed |

This pattern — **join → resolve → relative_to** — is the standard Python idiom for
sandboxing file access. You will see it in web frameworks, upload handlers, and
container runtimes. If any of the three steps is missing, the sandbox has a hole.

---

## Step 7: Exit the Agent

```
You: exit
```

Or press **Ctrl+C**.

---

## What to Look For

- **`[ACT]`** always shows the tool name and exact arguments passed by the model.
- **`[OBSERVE]`** shows the raw tool return value — this is what the model reads before formulating its response.
- **`[RESPOND]`** is the model's final answer, which synthesizes the observed data.
- When no tool is needed, you jump straight from `You:` to `[RESPOND]`.

---

## Discussion Questions

1. The model decided which tool to use based on your plain-English question. Where does that decision happen — in your code, or in the model itself? What could go wrong if the model picks the wrong tool?

2. You tested path traversal in Step 6. The block happens inside `tools/file_ops.py`. What would happen if that check were missing? What class of vulnerability does it prevent?

3. What would an attacker try if they could control the `filename` argument passed to `write_file`? (Hint: think about writing to locations like `~/.bashrc` or `/etc/cron.d/`.)

4. The `http_get` tool only allows a hard-coded set of domains. How would you extend this allow-list for a real deployment? What risks does a too-permissive allow-list introduce?

---

**Next lab:** [Lab 1.3 — Reading the ReAct Trace](lab1_3_react_trace.md)
