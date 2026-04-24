# Lab 3.8 — Supply Chain Hygiene: Verifying Ollama Models

**Module:** 3 — Defensive Architecture
**OWASP Risk:** LLM03 — Supply Chain Vulnerabilities
**Estimated time:** 20 minutes
**Prerequisite:** [Lab 3.7 — Iteration Limits and Rate Control](lab3_7_iteration_limits.md)

---

## Objective

Investigate the supply chain risks of pulling LLM weights from a public registry, use Ollama's built-in inspection tools to examine model metadata and digest hashes, and build a practical mitigation checklist for production deployments.

---

## Background

Pulling a model from Ollama's registry is analogous to installing a software package from PyPI or npm. The same supply chain risks apply: a model could be a malicious fine-tune with a poisoned system prompt baked into its Modelfile, a backdoored variant that behaves differently on specific inputs, or a legitimate model whose weights have been subtly modified to leak information or trigger on specific commands.

Unlike software packages, LLM weights are opaque binary blobs — you cannot read the "source code" and audit what they will do. The available mitigations are: verify digest hashes against known-good values, inspect Modelfiles for embedded system prompts, pin model versions by digest rather than by tag, and test model behaviour against a known baseline.

This lab is investigation-focused rather than attack-focused. The goal is to build the habit of model provenance checking before deploying any new model.

---

## Setup

No agent invocation needed for this lab. All steps use the Ollama CLI directly. Ensure Ollama is running:

```bash
ollama list
```

---

## Steps

### Step 1: List Installed Models with Digest Hashes

```bash
ollama list
```

Expected output:

```
NAME                  ID              SIZE    MODIFIED
qwen2.5:7b            845dbda0ea48    4.7 GB  3 days ago
nomic-embed-text      0a109f422b47    274 MB  5 days ago
llama-guard3          36a04e2bff6b    6.0 GB  5 days ago
```

The `ID` column is a short version of the model's SHA256 digest. This is your fingerprint for the model binary. If two installations of the same model have different IDs, the weights differ — this is a supply chain red flag.

### Step 2: Inspect a Model's Modelfile

```bash
ollama show qwen2.5:7b
```

Expected output includes the Modelfile:

```
  Model
    architecture        qwen2
    parameters          7.6B
    context length      32768
    ...

  Modelfile
    FROM qwen2.5:7b
    PARAMETER temperature 0.7
    ...
```

Look for a `SYSTEM` instruction in the Modelfile. A legitimate general-purpose model should have no baked-in system prompt. A `SYSTEM` instruction in a Modelfile that you did not write could indicate a poisoned fine-tune.

### Step 3: Verbose Model Inspection

```bash
ollama show --verbose qwen2.5:7b 2>&1 | head -30
```

The verbose output includes the full SHA256 digest, layer checksums, and parameter counts. Record the digest:

```
sha256:845dbda0ea48c9a4c8d39309ae3d5b48a4cdf74ac7...
```

### Step 4: Verify the Digest Against the Official Registry

Navigate to the Ollama model page for the model you are checking:

```
https://ollama.com/library/qwen2.5/tags
```

Find the entry for `qwen2.5:7b` and compare the displayed digest to the one from Step 3. A mismatch means you do not have the official model.

For scripted verification in CI/CD, you can capture and compare the digest programmatically:

```bash
ollama show --verbose qwen2.5:7b 2>&1 | grep "sha256"
```

Compare this output to the expected hash stored in a pinned manifest file in your repository.

### Step 5: Check llama-guard3 for Embedded System Prompts

```bash
ollama show llama-guard3
```

Examine the Modelfile for any `SYSTEM` instruction. Since Llama Guard 3 is a safety classifier that outputs "safe" or "unsafe" category codes, any baked-in system prompt that altered this behaviour would be especially dangerous — it could silently classify all inputs as safe regardless of content.

### Step 6: Build a Mitigation Checklist

Based on the above inspection, document the following checks in `workspace/model_verification_checklist.txt`:

```
You: Write a file called model_verification_checklist.txt with a numbered list
of five supply chain checks to run before deploying a new Ollama model in production.
```

After the agent creates the file, review and augment it:

```bash
cat workspace/model_verification_checklist.txt
```

A complete checklist should include: digest verification, Modelfile inspection, embedded SYSTEM prompt check, known-good baseline behaviour test, and source registry confirmation.

---

## Expected Output / What to Look For

- `ollama list` shows digest IDs — the fingerprints of your installed models.
- `ollama show --verbose` reveals the full SHA256 for hash-pinning.
- The Modelfile should have no `SYSTEM` instruction for a general-purpose model.
- Any mismatch between your local digest and the official registry digest is a supply chain indicator.

---

## Discussion Questions

1. Digest verification confirms you have the exact binary that was published to the Ollama registry. But the registry itself could be compromised. What additional verification layer would you add — for example, if Ollama published signed checksums via a separate channel?

2. A malicious fine-tune might behave identically to the original model on all standard benchmarks but trigger on a specific adversarial input (a "sleeper agent" backdoor). How would you design a behavioural test suite to detect this kind of supply chain attack?

3. Ollama uses tag names like `qwen2.5:7b` that can be moved to point at different digest values (analogous to Docker's `latest` tag). What is the security argument for pinning by digest (e.g., `qwen2.5@sha256:845dbda...`) rather than by tag in a production deployment?

---

**Next lab:** [Lab 3.9 — Grounding with RAG and Search: Reducing Misinformation](lab3_9_rag_grounding.md)
