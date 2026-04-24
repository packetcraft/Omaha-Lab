from ddgs import DDGS
from langchain_core.tools import tool

_MAX_RESULTS = 5


@tool
def web_search(query: str) -> str:
    """Search the web using DuckDuckGo. Returns titles, URLs, and snippets for the top results."""
    try:
        with DDGS() as ddgs:
            results = list(ddgs.text(query, max_results=_MAX_RESULTS))
    except Exception as exc:
        return f"Search error: {exc}"

    if not results:
        return "No results found."

    lines = []
    for i, r in enumerate(results, 1):
        title = r.get("title", "No title")
        url = r.get("href", "")
        snippet = r.get("body", "")
        lines.append(f"{i}. {title}")
        if url:
            lines.append(f"   {url}")
        if snippet:
            lines.append(f"   {snippet}")
        lines.append("")

    return "\n".join(lines).strip()
