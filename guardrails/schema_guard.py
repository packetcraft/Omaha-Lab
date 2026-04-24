"""Tool result schema validation — flags empty, non-string, or malformed JSON results."""
import json
import logging
from typing import Any

logger = logging.getLogger(__name__)


def validate_tool_result(tool_name: str, result: Any) -> tuple[bool, str | None]:
    """
    Validate a tool's return value.  Returns (ok, error_message | None).

    Rules:
    - Result must be a non-empty string.
    - If tool_name is 'http_get' and result starts with '{', it must be valid JSON.
    """
    if not isinstance(result, str):
        msg = f"{tool_name} returned {type(result).__name__}, expected str"
        logger.warning("Schema validation failed: %s", msg)
        return False, msg

    if not result.strip():
        msg = f"{tool_name} returned empty string"
        logger.warning("Schema validation failed: %s", msg)
        return False, msg

    if tool_name == "http_get" and result.strip().startswith("{"):
        try:
            json.loads(result)
        except json.JSONDecodeError as exc:
            msg = f"http_get returned malformed JSON: {exc}"
            logger.warning("Schema validation failed: %s", msg)
            return False, msg

    return True, None
