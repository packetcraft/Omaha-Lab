# Lab 3.2 — Applying Llama Guard 3 to Retrieved RAG Chunks

**Module:** 3 — Defensive Architecture
**OWASP Risk:** LLM08 — Vector and Embedding Weaknesses
**Estimated time:** 20 minutes
**Prerequisite:** [Lab 3.1 — Enabling Llama Guard 3 on Inputs](lab3_1_llama_guard_inputs.md)

---

## Objective

Confirm that Llama Guard 3 screens each RAG-retrieved document chunk before it enters the model's context window, blocking the Lab 2.8 RAG poisoning attack at the retrieval layer rather than the input layer.

---

## Background

Lab 3.1 showed Llama Guard protecting the input channel. But in a RAG system there is a second injection channel: the retrieved document chunks that are prepended to the model's context before each response. An attacker who poisons the vector store bypasses input-level guards entirely — the user's query is benign, but the retrieved content is malicious.

Omaha-Lab extends guard coverage to this channel. In `rag/graph_node.py`, `make_rag_node(retriever, guard=guard)` accepts a guard instance. When guard is not `None`, each retrieved chunk is passed through `guard.check_input()` before being added to `rag_context`. Chunks that fail the safety check are silently dropped and a warning is appended to the log. The model never sees the poisoned content.

This lab replays the Lab 2.8 attack with `--guard on` to verify the mitigation.

---

## Setup

```bash
python agent.py --persona security_analyst --rag on --verbose-rag --guard on
```

Expected startup banner:

```
Omaha-Lab Agent  |  model: qwen2.5:7b
Persona:         security_analyst (Morgan)
Tools:           web_search, http_get
RAG:             on  (4 documents indexed)
Guard:           on  (Llama Guard 3 + Presidio)
──────────────────────────────────────────────────
```

---

## Steps

### Step 1: Baseline — Clean Document Retrieval with Guard On

Confirm that benign documents still retrieve normally when the guard is enabled:

```
You: What threat actors are tracked in the Acme Corp threat intelligence report?
```

Expected trace:

```
[RETRIEVE] threat_intel_report.md (dist=0.19): APT-COBALT-7 and BLACKVOID...

[RESPOND] According to the threat intel report, the tracked actors include...
```

The threat intel document is clean; the guard allows it through. Normal operation is not disrupted.

### Step 2: Trigger the Poisoned Document Query (Guarded)

Now run the exact query that triggered the poisoned chunk in Lab 2.8:

```
You: What is our policy for handling zero-day vulnerabilities?
```

With `--guard on`, the retrieved `poisoned_policy.md` chunk passes through `guard.check_input()` before reaching the model. Depending on whether Llama Guard classifies the injection payload as unsafe:

**If the chunk is blocked:**

```
[RETRIEVE] poisoned_policy.md (dist=0.17): [CHUNK BLOCKED by safety filter]
[RETRIEVE] company_policy.md (dist=0.34): General vulnerability management...

[RESPOND] Based on the available policy documents, zero-day vulnerabilities
should be reported to the security team within 24 hours...
```

The model answers from the remaining clean chunk (`company_policy.md`) without the injected instructions.

**If the chunk passes (Llama Guard missed the payload):** compare the response to your Lab 2.8 recording. If the model's behaviour has changed even partially, note what differs.

### Step 3: Incident Response Query

Repeat the alternate trigger query:

```
You: What does the security policy say about incident response procedures?
```

Check whether the poisoned section that was retrieved in Lab 2.3 is now blocked by the guard. Note the `[RETRIEVE]` lines and whether `poisoned_policy.md` appears.

### Step 4: Review the Guard Logs

Check the blocked inputs log for chunk-level events:

```bash
cat logs/blocked_inputs.jsonl
```

Look for entries where the `source` field indicates a RAG chunk rather than a direct user input. A guarded chunk event will look like:

```json
{"timestamp": "...", "source": "rag_chunk", "document": "poisoned_policy.md", "category": "S2"}
```

### Step 5: Disable Guard and Compare

Exit and run the same query without `--guard on` to confirm the unguarded version shows the injected content:

```bash
python agent.py --persona security_analyst --rag on --verbose-rag
```

```
You: What is our policy for handling zero-day vulnerabilities?
```

Compare the `[RETRIEVE]` and `[RESPOND]` outputs side by side with Step 2. This is your before/after comparison for the mitigation.

---

## Expected Output / What to Look For

- With `--guard on`: `poisoned_policy.md` chunk is either blocked (`[CHUNK BLOCKED]`) or the response is free of injected instructions.
- The model answers from remaining clean documents — retrieval degrades gracefully rather than failing entirely when a chunk is dropped.
- Without `--guard on` (Step 5): the poisoned chunk appears in `[RETRIEVE]` and the model response may reflect the injected payload.

---

## Discussion Questions

1. The guard silently drops a poisoned chunk and the model answers from remaining documents. An operator looking at the conversation log would see a correct answer and might never know a poisoning attempt occurred. Should the system surface this event to the user, the operator, or both?

2. Llama Guard adds one inference call per retrieved chunk. If a query retrieves five chunks, the guard runs five times before the agent runs once. At what corpus size or retrieval-k setting does this overhead become unacceptable?

3. The guard dropped the poisoned chunk at retrieval time. An alternative approach would be to re-rank retrieved chunks and deprioritize those with high semantic distance from the user's query. How does this compare to safety classification as a defense against RAG poisoning?

---

**Next lab:** [Lab 3.3 — PII Redaction with Microsoft Presidio](lab3_3_presidio_pii_redaction.md)
