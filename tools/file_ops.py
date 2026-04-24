from pathlib import Path
from langchain_core.tools import tool

# Sandbox root — always relative to the project root, regardless of CWD.
_PROJECT_ROOT = Path(__file__).parent.parent
WORKSPACE = (_PROJECT_ROOT / "workspace").resolve()
WORKSPACE.mkdir(parents=True, exist_ok=True)


def _safe_path(filename: str) -> Path | None:
    """Resolve filename inside WORKSPACE. Returns None if the path escapes the sandbox."""
    try:
        target = (WORKSPACE / filename).resolve()
        target.relative_to(WORKSPACE)  # raises ValueError if outside
        return target
    except (ValueError, OSError):
        return None


@tool
def read_file(filename: str) -> str:
    """Read a file from the workspace sandbox directory. Filename is relative to ./workspace/."""
    path = _safe_path(filename)
    if path is None:
        return f"Error: '{filename}' escapes the workspace sandbox."
    if not path.exists():
        return f"File not found: workspace/{filename}"
    if not path.is_file():
        return f"'{filename}' is not a regular file."
    try:
        return path.read_text(encoding="utf-8")
    except OSError as exc:
        return f"Error reading file: {exc}"


@tool
def write_file(filename: str, content: str) -> str:
    """Write content to a file in the workspace sandbox directory. Filename is relative to ./workspace/.
    Creates parent directories as needed. Overwrites existing files."""
    path = _safe_path(filename)
    if path is None:
        return f"Error: '{filename}' escapes the workspace sandbox."
    try:
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(content, encoding="utf-8")
        return f"Wrote {len(content)} characters to workspace/{filename}"
    except OSError as exc:
        return f"Error writing file: {exc}"
