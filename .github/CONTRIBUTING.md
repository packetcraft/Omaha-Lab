# Contributing to Omaha-Lab

Thank you for your interest in contributing! This project welcomes pull requests, bug reports, lab feedback, and feature suggestions.

---

## Development Setup

1. **Fork** the repository on GitHub, then clone your fork locally:

   ```bash
   git clone https://github.com/<your-username>/omaha-lab.git
   cd omaha-lab
   ```

2. **Create a virtual environment** and install dependencies:

   ```bash
   # macOS
   python3.11 -m venv venv
   source venv/bin/activate

   # Windows Git Bash
   python -m venv venv
   source venv/Scripts/activate

   pip install -r requirements.txt
   ```

3. **Configure your environment:**

   ```bash
   cp .env.example .env
   # Edit .env — add WEATHER_API_KEY and SEARCH_API_KEY if you have them
   ```

4. **Run the test suite** (if applicable):

   ```bash
   python -m pytest
   ```

   Tests are located in the `tests/` directory. All existing tests must pass before opening a PR.

---

## Branch Naming Convention

| Prefix | Use for |
|---|---|
| `feature/` | New capabilities or agent enhancements |
| `fix/` | Bug fixes |
| `lab/` | New or revised lab content |
| `docs/` | Documentation-only changes |

Example: `lab/module2-indirect-injection`, `fix/rag-retrieval-timeout`

---

## Commit Message Style

We prefer [Conventional Commits](https://www.conventionalcommits.org/):

```
<type>: <short summary>

[optional body]
```

| Type | Use for |
|---|---|
| `feat:` | New feature or capability |
| `fix:` | Bug fix |
| `docs:` | Documentation changes only |
| `lab:` | Lab content additions or corrections |
| `refactor:` | Code restructuring without behavior change |
| `test:` | Adding or updating tests |
| `chore:` | Maintenance (deps, CI config, etc.) |

Keep the subject line under 72 characters. Use the body to explain _why_, not _what_.

---

## Pull Requests

1. Fork the repository and create a branch from `main` using the naming convention above.
2. Make your changes. Keep commits focused and descriptive.
3. Ensure all Python code follows the existing style (PEP 8; no type-annotation removal).
4. If adding a new lab, follow the lab file structure in `labs/module1/lab1_1_environment_setup.md`.
5. Open a pull request against `main` and fill in the PR template.
6. One maintainer review is required before merge.

### What to include in your PR description

- **What changed** — a brief summary of the change and the problem it solves.
- **Which labs or stages are affected** — e.g. "Updates Lab 2.3; no other labs affected."
- **Test steps** — the exact commands a reviewer should run to verify the change works, including any flags, models, or environment variable overrides needed.
- **Screenshots or terminal output** — for agent behavior or lab output changes, include a short capture.

---

## Lab Contribution Guidelines

Labs are the core educational content of this project. To add or revise a lab:

- **File naming:** `lab<module>_<number>_<slug>.md` — e.g. `lab2_4_prompt_injection_rag.md`
- **Location:** Place in the appropriate module directory (`labs/module1/`, `labs/module2/`, or `labs/module3/`).
- **Format:** Follow the structure of existing labs — each lab should have: Overview, Prerequisites, Step-by-step instructions, Expected output, and Discussion questions.
- **Module alignment:**
  - Module 1 — Foundations (setup, first agent, personas, RAG basics)
  - Module 2 — Offensive security exercises (OWASP LLM01–LLM10 attacks)
  - Module 3 — Defensive architecture (enabling and validating guardrail layers)
- **PR label:** Add the `lab` label to your pull request.
- **Cross-references:** If your lab references another lab, link it by relative path.

---

## Issue Triage

Issues are triaged within 7 days (aspiration). Use the provided templates:

- **Bug report** — something is broken
- **Lab feedback** — a lab step is unclear, incorrect, or doesn't reproduce
- **Feature request** — a new capability or lab idea

---

## Code Style

- Python 3.11+
- Format with `black` (88-char line length)
- Lint with `ruff`
- Do not add cloud LLM provider dependencies (OpenAI, Anthropic, Bedrock, etc.)

---

## Out-of-Scope Contributions

The following are explicitly out of scope for this project. PRs in these categories will be closed without merge:

- **Cloud LLM providers** — No OpenAI, Anthropic, AWS Bedrock, Google Vertex, or any other cloud inference endpoint. All inference must stay local via Ollama.
- **Production hardening** — This is a lab/research environment, not a production system. PRs that add authentication layers, rate limiting, secrets management, or deployment configuration are out of scope.
- **Mobile or browser deployments** — No React, mobile apps, browser extensions, or hosted deployments.

If you are unsure whether your idea is in scope, open a feature request issue first and discuss before writing code.

---

## Security

If you discover a security vulnerability, please open a **private security advisory** rather than a public issue. Navigate to the repository's Security tab and select "Report a vulnerability."
