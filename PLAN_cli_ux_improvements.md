# PLAN: CLI UX Improvements for agent.py

## Goal
Improve the readability and debuggability of the `agent.py` interactive chat interface by:
1. Adding visual hierarchy to the wall-of-text output
2. Making guard scan results informative and actionable

---

## Problem Summary

### Problem 1 — Wall of Text
`[RETRIEVE]`, `[RESPOND]`, user input, and system messages all render at the same visual weight with no separation. 

### Problem 2 — Guard Block Provides No Useful Detail
`[BLOCKED] Safety filter: S14` is not human-readable. It does not say which layer fired (llama-guard3, presidio, or canary), the category label, or the confidence score.

### Problem 3 — No Processing Feedback
The agent goes silent while retrieving and generating, then dumps output in a batch.

---

## Implementation Plan

### Stage A — Color Coding by Message Type

**File to edit:** `agent.py` (look for where `[RETRIEVE]`, `[RESPOND]`, `[BLOCKED]` are printed)

Define an ANSI color helper at the top of the file:

```python
class C:
    RESET  = "\033[0m"
    DIM    = "\033[2m"
    BOLD   = "\033[1m"
    CYAN   = "\033[96m"
    GREEN  = "\033[92m"
    YELLOW = "\033[93m"
    RED    = "\033[91m"
    BLUE   = "\033[94m"
    GRAY   = "\033[90m"
```

Apply colors:
| Output type       | Color              |
|-------------------|--------------------|
| User input prompt | `CYAN` bold        |
| `[RETRIEVE]` lines| `GRAY` dim         |
| `[RESPOND]` label | `GREEN` bold       |
| Agent response    | `GREEN`            |
| `[BLOCKED]` label | `RED` bold         |
| System status     | `BLUE`             |

**Acceptance:** Each message type visually distinct at a glance.

---

### Stage B —

---

### Stage C — Turn Separators

**File to edit:** `agent.py` main chat loop

After each complete agent turn (retrieve + respond), print a separator:

```python
print(f"{C.GRAY}{'─' * 60}{C.RESET}")
```

Also align the user/agent prompt labels so they form a consistent left gutter:
```
You   > What is the acceptable use policy?
Agent > Based on the context...
```

**Acceptance:** Each conversation turn is visually bounded.

---

### Stage D — Guard Block Detail

**File to edit:** wherever `[BLOCKED]` is emitted (likely `guardrails/` module)

#### D1 — Expand filter code to human-readable label

Map llama-guard3 category codes to labels. Example mapping:
```python
LLAMA_GUARD_CATEGORIES = {
    "S1":  "Violent Crimes",
    "S2":  "Non-Violent Crimes",
    "S3":  "Sex-Related Crimes",
    "S4":  "Child Sexual Exploitation",
    "S5":  "Defamation",
    "S6":  "Specialized Advice",
    "S7":  "Privacy",
    "S8":  "Intellectual Property",
    "S9":  "Indiscriminate Weapons",
    "S10": "Hate",
    "S11": "Suicide & Self-Harm",
    "S12": "Sexual Content",
    "S13": "Elections",
    "S14": "Code Interpreter Abuse",
}
```

Print as:
```
[BLOCKED by llama-guard3] S14 — Code Interpreter Abuse (score: 0.97)
```

#### D2 — Show which guard layer fired

The guard stack is `llama-guard3 + presidio + canary`. Each layer should tag its own blocks:
```
[BLOCKED by presidio] Entity detected: PERSON (1 hit)
[BLOCKED by canary]   Canary token triggered in output
```

#### D3 — Per-turn guard scan receipt (pass or block)

After every turn, print a one-liner showing what the guard stack checked:
```
[Guard] input: pass | output: pass | presidio: 0 entities | canary: clean
```
On block:
```
[Guard] input: BLOCKED — llama-guard3, S14 — Code Interpreter Abuse (0.97)
```

**Acceptance:** A blocked turn tells you which layer, which category, and what score. A passing turn shows a clean receipt.

---

### Stage E — Processing Feedback (Spinner / Status Line)

**File to edit:** `agent.py` main loop

Use `\r` overwrite to show inline status during retrieval and generation:

```python
import sys, time, threading

def spinner(msg, stop_event):
    frames = ["⠋","⠙","⠹","⠸","⠼","⠴","⠦","⠧","⠇","⠏"]
    i = 0
    while not stop_event.is_set():
        sys.stdout.write(f"\r{C.GRAY}{frames[i % len(frames)]} {msg}{C.RESET}")
        sys.stdout.flush()
        time.sleep(0.1)
        i += 1
    sys.stdout.write("\r" + " " * (len(msg) + 4) + "\r")  # clear line
```

Show:
- `Retrieving...` during RAG lookup
- `Generating...` during LLM call

Also print latency and token count at end of each turn:
```
(3.2s | 187 tokens)
```

**Acceptance:** User sees activity feedback; line clears cleanly before response is printed.

---

## Implementation Order

| Stage | Description                        | Effort  | Impact |
|-------|------------------------------------|---------|--------|
| A     | ANSI color coding                  | Low     | High   |
| C     | Turn separators + label alignment  | Low     | High   |
| D1    | Guard code → label mapping         | Low     | High   |
| D2    | Show which guard layer fired       | Medium  | High   |
| D3    | Per-turn guard scan receipt        | Medium  | Medium |
| E     | Spinner / latency line             | Medium  | Low    |

Start with A + C + D1 — they are pure print-formatting changes with no logic risk.

---

## Files Likely Involved

| File                    | Why                                      |
|-------------------------|------------------------------------------|
| `agent.py`              | Main loop, prompt printing, flag parsing |
| `guardrails/`           | Where `[BLOCKED]` is emitted             |
| `rag/`                  | Where `[RETRIEVE]` lines are printed     |
| `state.py`              | May carry guard result metadata          |
