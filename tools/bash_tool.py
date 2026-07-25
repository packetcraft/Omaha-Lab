import subprocess
from langchain_core.tools import tool


@tool
def run_shell(command: str) -> str:
    """Execute a shell command and return combined stdout/stderr. No sandboxing,
    no allow-list, no path confinement — runs with the real permissions of this
    process. Intentionally unconstrained: see Lab 2.10 (Excessive Agency).
    Only run this tool inside an isolated VM or container, never on a bare host."""
    try:
        result = subprocess.run(
            command,
            shell=True,
            capture_output=True,
            text=True,
            timeout=30,
        )
        output = (result.stdout + result.stderr).strip()
        return output or f"(command exited {result.returncode}, no output)"
    except subprocess.TimeoutExpired:
        return "Error: command timed out after 30 seconds."
    except Exception as exc:
        return f"Error running command: {exc}"
