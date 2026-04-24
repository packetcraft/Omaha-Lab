# Lab 3.5 — Output Validation and Canary Tokens

**Module:** 3 — Defensive Architecture
**OWASP Risk:** LLM05 — Improper Output Handling
**Estimated time:** 20 minutes
**Prerequisite:** [Lab 3.4 — HITL Authorization Breakpoint](lab3_4_hitl.md)

---

## Objective

Demonstrate two output-layer defences: canary token detection (alerting when tracked strings appear in responses) and tool-call schema validation (rejecting malformed JSON arguments before execution).

---

## Background

Two mechanisms run inside `output_guard_node` when `--guard on` is active:

**Canary tokens** are unique, trackable strings embedded in sensitive documents or data. If a canary token appears in an agent's response, it means the agent retrieved and reproduced content from a tracked source — a potential exfiltration indicator. The scanner reads `guardrails/canary_tokens.txt` (one token per line), checks every agent response for matches, and logs any hits to `logs/canary_alerts.jsonl`.

**Schema validation** runs in the agent node before tool execution. When the model generates a tool call, `guardrails/schema_guard.py` validates the JSON arguments against the expected schema for that tool. Arguments that do not match the schema (wrong types, missing required fields, null where a string is expected) are rejected and the tool is not called.

In a real deployment, canary tokens would be embedded in sensitive database records, policy documents, or API responses. If a canary appears in a chat output, that is evidence of data leakage from a specific source.

---

## Setup

```bash
python agent.py --guard on
```

Expected startup banner:

```
Omaha-Lab Agent  |  model: qwen2.5:7b
Persona:         (none)
Tools:           get_weather, web_search, http_get, read_file, write_file
RAG:             off
Guard:           on  (Llama Guard 3 + Presidio + Canary)
──────────────────────────────────────────────────
```

---

## Steps

### Step 1: Inspect the Canary Token File

In a second terminal, view the canary token list:

```bash
cat guardrails/canary_tokens.txt
```

You should see tokens like:

```
CANARY-OMAHA-001
CANARY-OMAHA-002
CANARY-HR-SSN-2026
```

These are the tracked strings. Any of these appearing in an agent response will trigger an alert.

### Step 2: Trigger a Canary Alert

Ask the agent to include a known canary token in its output:

```
You: Write a message that includes the text CANARY-OMAHA-001 as part of an example output.
```

Expected response with guard-appended alert:

```
[RESPOND] Here is an example output message: CANARY-OMAHA-001
⚠️  [CANARY ALERT: token 'CANARY-OMAHA-001' detected in response]
```

The alert is appended to the response before printing. The agent answered normally — canary detection is an alerting mechanism, not a blocking one.

### Step 3: Review the Canary Alert Log

```bash
cat logs/canary_alerts.jsonl
```

Expected log entry:

```json
{"timestamp": "2026-04-24T...", "token": "CANARY-OMAHA-001", "response_preview": "...CANARY-OMAHA-001..."}
```

### Step 4: Add a Canary Token to a Context Document

To see canary detection working as a real data-leakage indicator, add a token to one of the context documents:

```bash
echo "\n\nCANARY-HR-SSN-2026" >> context_docs/employee_handbook.md
```

Now run with RAG enabled and ask the model to reproduce handbook content:

```bash
python agent.py --persona hr_assistant --rag on --guard on
```

```
You: What does the employee handbook say about the onboarding process?
```

If the model reproduces a section that includes the canary token, the alert fires. This is the real-world use case — the canary proves the model retrieved and output content from that specific document.

After the lab, remove the added token:

```bash
# Remove the last line added above (the canary token line)
# Edit context_docs/employee_handbook.md and remove the CANARY-HR-SSN-2026 line
```

### Step 5: Schema Validation — Invalid Tool Arguments

Schema validation runs before tool execution. To observe it, you need to get the model to generate a malformed tool call. One way is to directly describe the invalid call:

```
You: Call the write_file tool with filename set to null and content set to "test".
```

If the model generates `write_file({"filename": null, "content": "test"})`, the schema guard rejects it before the tool runs:

```
[ACT]     write_file({'filename': null, 'content': 'test'})
Schema validation error: 'filename' must be a non-null string. Tool call rejected.

[RESPOND] I was unable to write the file because the filename argument was invalid.
```

The tool was never invoked. The schema guard is a last-resort check before any tool execution occurs.

---

## Expected Output / What to Look For

- Canary tokens in responses trigger `[CANARY ALERT: ...]` appended to the `[RESPOND]` output.
- All canary hits are logged to `logs/canary_alerts.jsonl` with timestamps.
- Schema validation rejects tool calls with invalid argument types before execution occurs.
- Neither mechanism blocks the response entirely — they alert (canary) or reject (schema) at the specific point of concern.

---

## Discussion Questions

1. Canary token detection alerts after the response is generated — the sensitive string was already in the agent's context when the alert fires. What additional step would you take to convert this from a detection mechanism into a prevention mechanism?

2. In Step 4, you embedded a canary token in `context_docs/employee_handbook.md`. In a real production RAG system, at what granularity would you place canary tokens — one per document, one per section, or one per data field? What are the tradeoffs?

3. Schema validation rejects tool calls with malformed arguments. However, a `write_file` call with a valid filename and dangerous content (e.g., a shell script) would pass schema validation. What additional layer would you add to validate the *content* of tool calls, not just the structure?

---

**Next lab:** [Lab 3.6 — Scoping Tool Permissions per Persona](lab3_6_tool_scoping.md)
