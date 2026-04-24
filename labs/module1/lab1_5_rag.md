# Lab 1.5 — Enabling RAG with a Markdown Context Document

**Module:** 1 — Foundations
**Estimated time:** 20 minutes
**Prerequisite:** [Lab 1.4](lab1_4_persona.md) completed. `nomic-embed-text` model pulled (Lab 1.1 Step 2).

---

## Objective

Enable Retrieval-Augmented Generation (RAG), observe how the agent retrieves relevant chunks from local Markdown documents before answering, and understand why RAG improves factual grounding — and why it also creates new attack surfaces.

---

## Background: The RAG Pipeline

Without RAG, the agent answers entirely from the LLM's training data, which may be outdated or simply wrong. With RAG enabled, the pipeline adds a retrieval step before the LLM reasons:

```
User message
    │
    ▼
┌─────────────────────────────────────────────────┐
│  RAG Node                                       │
│  1. Embed the user's message (nomic-embed-text) │
│  2. Query ChromaDB for top-3 similar chunks     │
│  3. Inject chunks as a SystemMessage            │
└───────────────────────┬─────────────────────────┘
                        │  [RETRIEVE] lines printed here
                        ▼
┌─────────────────────────────────────────────────┐
│  Agent Node — LLM sees:                         │
│    SystemMessage: persona system prompt         │
│    SystemMessage: RETRIEVED CONTEXT ...         │
│    HumanMessage:  user's question               │
└─────────────────────────────────────────────────┘
```

The four pre-built context documents are:

| File | Content |
|---|---|
| `company_policy.md` | Acme Corp employee policy (data classification, AUP, VPN) |
| `employee_handbook.md` | Initech Corp HR handbook (benefits, PTO, employee PII table) |
| `threat_intel_report.md` | CyberGuard SOC report (APT groups, IOCs, CVEs, YARA rules) |
| `poisoned_policy.md` | Acme AI tool policy — contains a hidden injection payload (used in Lab 2.8) |

---

## Step 1: First Run — Embedding the Documents

The first time `--rag on` is used, ChromaDB is empty. The agent will embed all four documents:

```bash
python agent.py --persona security_analyst --rag on --verbose-rag
```

Expected output before the banner:

```
RAG: syncing context_docs/...
  Rebuilt embeddings for: company_policy.md, employee_handbook.md, poisoned_policy.md, threat_intel_report.md
  Collection: 63 chunks indexed.
```

> **How long does this take?** On a machine with GPU acceleration, 3–5 seconds. On CPU only, 30–60 seconds. This only happens once — subsequent runs use the cached embeddings.

Then the familiar startup banner:

```
Omaha-Lab Agent  |  model: llama3.1:8b
Persona:         Security Analyst [high]
Tools:           web_search, http_get, read_file, write_file
RAG:             on
──────────────────────────────────────────────────
Type 'quit' or 'exit' to stop.
```

---

## Step 2: Ask a Question Grounded in the Threat Intel Report

```
You: What do you know about APT-COBALT-7?
```

You should see `[RETRIEVE]` lines before the response — these show which chunks were fetched from ChromaDB and their cosine distance (lower = more similar):

```
[RETRIEVE] threat_intel_report.md (dist=0.0821): ## Section 1: Threat Actor Profile — APT-COBALT-7  **Alias:** Cobalt Typhoon, UNC-3887...
[RETRIEVE] threat_intel_report.md (dist=0.1034): **SILENTRAIL Indicators:** - Process: `svchost.exe` spawning `conhost.exe`...
[RETRIEVE] threat_intel_report.md (dist=0.1892): ## Section 5: Recommendations  1. **Patch immediately** all VPN and perimeter...

[RESPOND] APT-COBALT-7, also tracked as Cobalt Typhoon and UNC-3887, is a nation-state
aligned threat actor assessed with high confidence as originating from East Asia.
They primarily conduct espionage operations targeting intellectual property and
government contract data...
```

The model's answer is grounded in the CyberGuard threat intelligence report rather than potentially outdated training data.

---

## Step 3: Verify Retrieval Improves Accuracy

Compare the same question with RAG disabled in a second terminal:

```bash
python agent.py --persona security_analyst
```

```
You: What do you know about APT-COBALT-7?
```

Without RAG, the model will likely say it has no specific information about APT-COBALT-7 (it's a fictional threat actor invented for this lab). This directly demonstrates the grounding effect.

---

## Step 4: Cross-Document Retrieval

Ask a question whose answer spans multiple documents:

```
You: What is Acme Corp's policy on using AI tools with sensitive data, and how does that relate to the data classification tiers?
```

Expected: chunks retrieved from both `company_policy.md` and `poisoned_policy.md`, since both contain relevant content:

```
[RETRIEVE] company_policy.md (dist=0.1102): ## Section 1: Data Classification  Acme Corp classifies all company data into four tiers...
[RETRIEVE] poisoned_policy.md (dist=0.1445): ## Section 5: Data Handling  When using approved AI tools: Strip all PII from documents...
[RETRIEVE] company_policy.md (dist=0.1687): Unapproved AI tools — including browser-based LLM chatbots — may not be used to process Tier 3 or Tier 4 data...

[RESPOND] Acme Corp's AI tool usage policy directly references its data classification tiers...
```

---

## Step 5: Observe a Second Run (Cache Hit)

Exit and restart with `--rag on`:

```bash
python agent.py --persona security_analyst --rag on --verbose-rag
```

This time the output is:

```
RAG: syncing context_docs/...
  All documents up to date.
  Collection: 63 chunks indexed.
```

No re-embedding occurred. The MD5 manifest at `.chroma/manifest.json` matched all four files. Only changes to the source `.md` files trigger a rebuild.

Verify the manifest:

```bash
cat .chroma/manifest.json
```

```json
{
  "company_policy.md": "a3f8b2c1...",
  "employee_handbook.md": "7d4e9f2a...",
  "poisoned_policy.md": "1b6c3e8f...",
  "threat_intel_report.md": "5a2d9c4b..."
}
```

---

## Step 6: Force a Partial Rebuild

Make a small edit to `company_policy.md` and re-run:

```bash
echo "" >> context_docs/company_policy.md
python agent.py --rag on --verbose-rag
```

Expected:

```
RAG: syncing context_docs/...
  Rebuilt embeddings for: company_policy.md
  Collection: 63 chunks indexed.
```

Only the changed file was re-embedded. Restore the file:

```bash
# Remove the trailing newline you added
# (or just leave it — it doesn't affect content meaningfully)
```

---

## Step 7: Query the HR Handbook (Preview of Lab 2.4)

Switch to the HR persona to retrieve from the employee handbook:

```bash
python agent.py --persona hr_assistant --rag on --verbose-rag
```

```
You: Do we have any employees in the Engineering department?
```

Expected: the handbook's employee directory table is retrieved:

```
[RETRIEVE] employee_handbook.md (dist=0.0934): ## Chapter 6: Employee Directory (CONFIDENTIAL — HR USE ONLY) ...
            E-1042 | Jane Smith | DOB: 1985-03-14 | SSN: 542-76-8921...

[RESPOND] Yes, the Engineering department has three employees on record:
- Jane Smith (E-1042)
- Kevin Park (E-1048)
- Amara Osei (E-1055)
```

> **Stop and notice:** The `[RETRIEVE]` line shows the raw chunk content — including the SSN and salary. The agent retrieved this without any authorization check. This is a preview of **Lab 2.4 — PII Extraction Attack**, where you will demonstrate how an attacker can systematically exfiltrate this data, and **Lab 3.3 — Presidio PII Redaction**, where you will block it.

---

## Step 8: Understand the Full Pipeline

Run `python agent.py --persona security_analyst --rag on --verbose-rag` and trace through what happens on each user message:

1. You type a message → `HumanMessage` added to graph state.
2. **RAG node** runs first: embeds your message, queries ChromaDB, returns top-3 chunks as `rag_context` + `retrieved_chunks`. The `[RETRIEVE]` lines are printed here.
3. **Agent node** runs: builds `[SystemMessage(persona_prompt), SystemMessage(rag_context)] + messages` and calls the Ollama LLM.
4. If the model calls a tool → **tools node** runs → result added to state → agent node runs again (without re-running the RAG node).
5. Model produces a final answer → `[RESPOND]` printed.

Key insight: **the RAG context is injected fresh on every user turn, but only once per turn** — it doesn't re-retrieve between tool calls in the same turn. The context stays relevant throughout the ReAct loop for that question.

---

## Module 1 Complete

You have now covered the full Omaha-Lab pipeline:

```
User input
  → RAG retrieval (Lab 1.5)
  → Persona system prompt injection (Lab 1.4)
  → LLM reasoning (Lab 1.2)
  → Tool calling with ReAct loop (Lab 1.3)
  → Response
```

**What's next:** Module 2 takes everything you've built and attacks it. You'll craft prompt injections, extract PII, leak system prompts, force unauthorized tool calls, and poison the RAG store — all against these same agents, running without the guardrails added in Module 3.

---

## Discussion Questions

1. The RAG node retrieves the top-3 chunks by cosine similarity. What determines what "similar" means here? What happens if the query is short or ambiguous — does similarity still work?

2. You saw in Step 7 that the employee handbook's PII table was retrieved in full as a raw chunk. What would be a safer chunking strategy that prevents PII-dense sections from being retrieved en masse?

3. ChromaDB persists embeddings to disk at `.chroma/`. What would happen if an attacker could write a new `.md` file to `context_docs/` and trigger a sync? (This is the foundation of **Lab 2.8 — RAG Poisoning**.)

4. The retrieval step runs on the user's raw message. What happens to the retrieval quality if the user's message itself is an adversarial injection payload rather than a genuine question? Does that make retrieval-based attacks harder or easier?

---

**Continue to Module 2:** [Module 2 — Offensive Security](../module2/)
