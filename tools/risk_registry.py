# Tool risk classification for HITL authorization.
# high-risk tools pause execution and require explicit human approval.
# http_get is GET-only (no side effects) so it is low-risk; an HTTP POST
# tool would be high-risk but is not in scope for this lab.
RISK_LEVEL: dict[str, str] = {
    "get_weather": "low",
    "web_search":  "low",
    "http_get":    "low",
    "read_file":   "low",
    "write_file":  "high",
}
