from dataclasses import dataclass


@dataclass
class GuardResult:
    safe: bool
    category: str | None  # e.g. "S1", "S14"
    raw_response: str
