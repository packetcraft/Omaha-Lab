"""Canary token detection — scans LLM output for registered tracking strings."""
import json
import logging
from datetime import datetime, timezone
from pathlib import Path

logger = logging.getLogger(__name__)

_TOKENS_FILE = Path(__file__).parent / "canary_tokens.txt"
_LOG_PATH = Path("logs") / "canary_alerts.jsonl"


def _load_tokens() -> list[str]:
    if not _TOKENS_FILE.exists():
        return []
    return [ln.strip() for ln in _TOKENS_FILE.read_text(encoding="utf-8").splitlines() if ln.strip()]


def scan(text: str) -> list[str]:
    """Return canary tokens found in text (empty list if clean)."""
    return [t for t in _load_tokens() if t in text]


def log_alert(found: list[str], response_preview: str) -> None:
    _LOG_PATH.parent.mkdir(exist_ok=True)
    entry = {
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "tokens_found": found,
        "response_preview": response_preview[:200],
    }
    with open(_LOG_PATH, "a", encoding="utf-8") as fh:
        fh.write(json.dumps(entry) + "\n")
    logger.warning("Canary tokens detected in output: %s", found)
