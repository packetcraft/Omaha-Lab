"""Llama Guard 3 input classifier — calls llama-guard3 via the Ollama generate API."""
import json
import logging
from datetime import datetime, timezone
from pathlib import Path

import requests

from .guard_result import GuardResult

logger = logging.getLogger(__name__)

_CATEGORIES = (
    "S1: Violent Crimes.\n"
    "S2: Non-Violent Crimes.\n"
    "S3: Sex-Related Crimes.\n"
    "S4: Child Sexual Exploitation.\n"
    "S5: Defamation.\n"
    "S6: Specialized Advice.\n"
    "S7: Privacy.\n"
    "S8: Intellectual Property.\n"
    "S9: Indiscriminate Weapons.\n"
    "S10: Hate.\n"
    "S11: Suicide & Self-Harm.\n"
    "S12: Sexual Content.\n"
    "S13: Elections.\n"
    "S14: Code Interpreter Abuse."
)

# Llama Guard 3 expects its own prompt format; raw generate is simpler than chat.
_PROMPT_TEMPLATE = (
    "<|begin_of_text|><|start_header_id|>user<|end_header_id|>\n\n"
    "Task: Check if there is unsafe content in 'User' messages in conversations "
    "according our safety policy with the below categories.\n\n"
    "<BEGIN UNSAFE CONTENT CATEGORIES>\n"
    "{categories}\n"
    "<END UNSAFE CONTENT CATEGORIES>\n\n"
    "<BEGIN CONVERSATION>\n\n"
    "User: {text}\n\n"
    "<END CONVERSATION>\n\n"
    "Provide your safety assessment for ONLY THE LAST User message. "
    "Output 'safe' if the content is safe, or 'unsafe' followed by the violated "
    "category codes on the next line (e.g., 'unsafe\\nS1').\n"
    "<|eot_id|><|start_header_id|>assistant<|end_header_id|>"
)


class LlamaGuard:
    def __init__(
        self,
        base_url: str = "http://localhost:11434",
        model: str = "llama-guard3",
    ) -> None:
        self.base_url = base_url.rstrip("/")
        self.model = model
        self._log_path = Path("logs") / "blocked_inputs.jsonl"

    def check_input(self, text: str) -> GuardResult:
        prompt = _PROMPT_TEMPLATE.format(categories=_CATEGORIES, text=text)
        try:
            resp = requests.post(
                f"{self.base_url}/api/generate",
                json={"model": self.model, "prompt": prompt, "stream": False},
                timeout=60,
            )
            resp.raise_for_status()
            raw = resp.json().get("response", "").strip()
        except Exception as exc:
            # If the guard is unreachable, fail open with a warning.
            logger.warning("LlamaGuard call failed — defaulting to safe: %s", exc)
            return GuardResult(safe=True, category=None, raw_response=f"error: {exc}")

        lower = raw.lower()
        safe = lower.startswith("safe")
        category = None
        if not safe:
            lines = raw.splitlines()
            category = lines[1].strip().upper() if len(lines) > 1 else "UNKNOWN"

        return GuardResult(safe=safe, category=category, raw_response=raw)

    def log_blocked(self, text: str, result: GuardResult) -> None:
        self._log_path.parent.mkdir(exist_ok=True)
        entry = {
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "category": result.category,
            "input_preview": text[:200],
        }
        with open(self._log_path, "a", encoding="utf-8") as fh:
            fh.write(json.dumps(entry) + "\n")
