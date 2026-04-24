import os
import requests
from urllib.parse import urlparse
from langchain_core.tools import tool

# Hard-coded trusted domains for the lab environment.
_ALLOWED_DOMAINS: set[str] = {
    "api.openweathermap.org",
    "wttr.in",
    "httpbin.org",
    "jsonplaceholder.typicode.com",
    "api.github.com",
    "api.coindesk.com",
}

# Extend the allow-list at runtime via HTTP_ALLOWED_DOMAINS=domain1,domain2
_extra = os.getenv("HTTP_ALLOWED_DOMAINS", "")
if _extra:
    _ALLOWED_DOMAINS.update(d.strip().lower() for d in _extra.split(",") if d.strip())

_RESPONSE_LIMIT = 2000


@tool
def http_get(url: str) -> str:
    """Make an HTTP GET request to an allow-listed URL and return the response body.
    Only domains in the allow-list are permitted: httpbin.org, jsonplaceholder.typicode.com,
    api.openweathermap.org, api.github.com, wttr.in, api.coindesk.com."""
    parsed = urlparse(url)
    domain = parsed.netloc.lower().lstrip("www.")

    if domain not in _ALLOWED_DOMAINS:
        allowed = ", ".join(sorted(_ALLOWED_DOMAINS))
        return (
            f"Blocked: '{domain}' is not in the allowed domain list.\n"
            f"Allowed domains: {allowed}"
        )

    try:
        resp = requests.get(
            url,
            timeout=10,
            headers={"User-Agent": "Omaha-Lab/1.0"},
        )
        resp.raise_for_status()
    except requests.HTTPError as exc:
        return f"HTTP {exc.response.status_code} error: {exc}"
    except requests.RequestException as exc:
        return f"Request failed: {exc}"

    body = resp.text
    if len(body) > _RESPONSE_LIMIT:
        body = body[:_RESPONSE_LIMIT] + "\n... (truncated)"
    return body
