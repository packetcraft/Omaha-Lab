#!/usr/bin/env python3
"""Omaha-Lab CLI agent — entry point for all stages."""
from __future__ import annotations
import json
import os
import sys
import argparse
import threading
import time
import uuid
from datetime import datetime, timezone
from pathlib import Path

from dotenv import load_dotenv
from langchain_core.messages import HumanMessage, AIMessage, ToolMessage

load_dotenv()


# ---------------------------------------------------------------------------
# Terminal colours  (Stage A)
# ---------------------------------------------------------------------------

class C:
    """ANSI colour codes — disabled automatically when stdout is not a tty."""
    _tty   = sys.stdout.isatty()
    RESET  = "\033[0m"  if _tty else ""
    DIM    = "\033[2m"  if _tty else ""
    BOLD   = "\033[1m"  if _tty else ""
    CYAN   = "\033[96m" if _tty else ""
    GREEN  = "\033[92m" if _tty else ""
    YELLOW = "\033[93m" if _tty else ""
    RED    = "\033[91m" if _tty else ""
    BLUE   = "\033[94m" if _tty else ""
    GRAY   = "\033[90m" if _tty else ""


LLAMA_GUARD_LABELS: dict[str, str] = {
    "S1":  "Violent Crimes",
    "S2":  "Non-Violent Crimes",
    "S3":  "Sex-Related Crimes",
    "S4":  "Child Sexual Exploitation",
    "S5":  "Defamation",
    "S6":  "Specialized Advice",
    "S7":  "Privacy",
    "S8":  "Intellectual Property",
    "S9":  "Indiscriminate Weapons",
    "S10": "Hate",
    "S11": "Suicide & Self-Harm",
    "S12": "Sexual Content",
    "S13": "Elections",
    "S14": "Code Interpreter Abuse",
    "S15": "Prompt Injection",
}


# ---------------------------------------------------------------------------
# Spinner  (Stage E)
# ---------------------------------------------------------------------------

def _spinner(msg: str, stop: threading.Event) -> None:
    if not sys.stdout.isatty():
        return
    frames = ["⠋", "⠙", "⠹", "⠸", "⠼", "⠴", "⠦", "⠧", "⠇", "⠏"]
    i = 0
    while not stop.is_set():
        sys.stdout.write(f"\r{C.GRAY}{frames[i % len(frames)]}  {msg}{C.RESET}  ")
        sys.stdout.flush()
        time.sleep(0.1)
        i += 1
    sys.stdout.write(f"\r{' ' * (len(msg) + 6)}\r")
    sys.stdout.flush()


# ---------------------------------------------------------------------------
# Guard receipt  (Stage D3)
# ---------------------------------------------------------------------------

def _print_guard_receipt(signals: dict, guard_enabled: bool) -> None:
    if not guard_enabled or not signals:
        return

    if signals.get("guard_input_blocked"):
        cat    = signals.get("guard_category", "")
        layer  = signals.get("guard_layer", "llama-guard3")
        label  = LLAMA_GUARD_LABELS.get(cat, cat) if cat else "policy violation"
        cat_str = f" — {cat}: {label}" if cat else ""
        print(f"{C.GRAY}[Guard] input: {C.RED}BLOCKED{C.GRAY} ({layer}{cat_str}){C.RESET}")
        return

    parts: list[str] = []
    if "guard_input_blocked" in signals:
        parts.append(f"input: {C.GREEN}pass{C.GRAY}")
    if "presidio_redacted" in signals:
        pstatus = f"{C.YELLOW}redacted{C.GRAY}" if signals["presidio_redacted"] else f"{C.GREEN}clean{C.GRAY}"
        parts.append(f"presidio: {pstatus}")
    if "canary_triggered" in signals:
        cstatus = f"{C.RED}ALERT{C.GRAY}" if signals["canary_triggered"] else f"{C.GREEN}clean{C.GRAY}"
        parts.append(f"canary: {cstatus}")

    if parts:
        print(f"{C.GRAY}[Guard] {' | '.join(parts)}{C.RESET}")


# ---------------------------------------------------------------------------
# Trace display  (Stages A, B, D1, D2)
# ---------------------------------------------------------------------------

def _print_event(event: dict, guard_enabled: bool = False, verbose_rag: bool = False) -> dict:
    """Print one stream event and return guard signals for the turn receipt."""
    signals: dict = {}

    for node_name, update in event.items():
        if node_name.startswith("__") or not isinstance(update, dict):
            continue

        # Stage B — RAG retrievals: collapsed by default, full with --verbose-rag
        chunks = update.get("retrieved_chunks", [])
        if chunks:
            if verbose_rag:
                for chunk in chunks:
                    source  = chunk.get("source", "?")
                    dist    = chunk.get("distance", "")
                    preview = chunk.get("text", "")[:120].replace("\n", " ")
                    print(f"{C.GRAY}[RETRIEVE] {source} (dist={dist}): {preview}...{C.RESET}")
            else:
                dist_vals = [c["distance"] for c in chunks if c.get("distance")]
                dist_str  = (
                    f" · dist {min(dist_vals):.4f}–{max(dist_vals):.4f}"
                    if dist_vals else ""
                )
                sources: dict[str, int] = {}
                for c in chunks:
                    src = c.get("source", "?")
                    sources[src] = sources.get(src, 0) + 1
                src_str = ", ".join(
                    f"{s}({n})" if n > 1 else s for s, n in sources.items()
                )
                n = len(chunks)
                print(f"{C.GRAY}[RAG] {n} chunk{'s' if n != 1 else ''} · {src_str}{dist_str}{C.RESET}")

        # Stage D3 — track guard_input pass (blocked case handled below in messages)
        if node_name == "guard_input" and not update.get("guard_blocked"):
            signals["guard_input_blocked"] = False

        # Messages
        for msg in update.get("messages", []):
            if isinstance(msg, AIMessage):
                if msg.tool_calls:
                    if msg.content:
                        print(f"{C.DIM}{C.YELLOW}[REASON]  {msg.content}{C.RESET}")
                    for tc in msg.tool_calls:
                        print(f"{C.DIM}{C.YELLOW}[ACT]     {tc['name']}({tc['args']}){C.RESET}")

                elif node_name == "guard_input":
                    # Stage D1 + D2 — show layer and human-readable category label
                    layer   = msg.additional_kwargs.get("guard_layer", "guard")
                    cat     = msg.additional_kwargs.get("guard_category", "")
                    label   = LLAMA_GUARD_LABELS.get(cat, cat) if cat else "policy violation"
                    cat_str = f" — {cat}: {label}" if cat else ""
                    print(f"\n{C.RED}{C.BOLD}[BLOCKED by {layer}]{C.RESET}{C.RED}{cat_str}{C.RESET}")
                    print(f"{C.RED}{msg.content}{C.RESET}\n")
                    signals["guard_input_blocked"] = True
                    signals["guard_category"]      = cat
                    signals["guard_layer"]         = layer

                elif node_name == "output_guard":
                    content = msg.content or ""
                    print(f"\n{C.GREEN}{C.BOLD}[RESPOND]{C.RESET} {C.GREEN}{content}{C.RESET}\n")
                    # Stage D3 — signals come from additional_kwargs set by the node
                    signals["presidio_redacted"] = msg.additional_kwargs.get("presidio_redacted", False)
                    signals["canary_triggered"]  = msg.additional_kwargs.get("canary_triggered", False)

                elif node_name == "agent" and not guard_enabled:
                    content = msg.content or ""
                    print(f"\n{C.GREEN}{C.BOLD}[RESPOND]{C.RESET} {C.GREEN}{content}{C.RESET}\n")

            elif isinstance(msg, ToolMessage):
                tool_name = getattr(msg, "name", "tool")
                print(f"{C.GRAY}[OBSERVE] {tool_name}: {msg.content}{C.RESET}")

    return signals


# ---------------------------------------------------------------------------
# REPL  (Stages C, E)
# ---------------------------------------------------------------------------

def run_repl(
    graph,
    model: str,
    tools: list | None = None,
    persona=None,
    rag: bool = False,
    guard: bool = False,
    hitl: bool = False,
    verbose_rag: bool = False,
) -> None:
    thread_id = str(uuid.uuid4())
    config    = {"configurable": {"thread_id": thread_id}}

    persona_display = persona.name if persona else "(none)"
    risk_display    = f" [{persona.risk_level}]" if persona else ""
    tool_names      = ", ".join(t.name for t in tools) if tools else "(none)"
    rag_display     = "on" if rag else "off"
    guard_display   = "on (regex-prefilter + llama-guard3 + presidio + canary)" if guard else "off"
    hitl_display    = "on (high-risk tool calls require approval)" if hitl else "off"

    print(f"\n{C.BOLD}Omaha-Lab Agent{C.RESET}  |  model: {C.CYAN}{model}{C.RESET}")
    print(f"Persona:         {C.YELLOW}{persona_display}{risk_display}{C.RESET}")
    print(f"Tools:           {tool_names}")
    print(f"RAG:             {rag_display}")
    print(f"Guard:           {guard_display}")
    print(f"HITL:            {hitl_display}")
    print(f"{C.GRAY}{'─' * 50}{C.RESET}")
    print(f"Type {C.BOLD}'quit'{C.RESET} or {C.BOLD}'exit'{C.RESET} to stop.\n")

    while True:
        try:
            user_input = input(f"{C.CYAN}{C.BOLD}You > {C.RESET}").strip()
        except (EOFError, KeyboardInterrupt):
            print("\nBye.")
            break

        if not user_input:
            continue
        if user_input.lower() in ("quit", "exit"):
            print("Bye.")
            break

        # Stage E — spinner while waiting for first event
        stop_spin   = threading.Event()
        spin_thread = threading.Thread(
            target=_spinner, args=("Thinking…", stop_spin), daemon=True
        )
        spin_thread.start()

        all_signals: dict = {}
        first      = True
        start_time = time.monotonic()

        for event in graph.stream(
            {"messages": [HumanMessage(content=user_input)]},
            config=config,
            stream_mode="updates",
        ):
            if first:
                stop_spin.set()
                spin_thread.join()
                first = False
            sigs = _print_event(event, guard_enabled=guard, verbose_rag=verbose_rag)
            all_signals.update(sigs)

        if first:  # graph emitted nothing
            stop_spin.set()
            spin_thread.join()

        elapsed = time.monotonic() - start_time

        # Stage D3 — guard scan receipt
        _print_guard_receipt(all_signals, guard)

        # Stage C — turn separator with elapsed time
        print(f"{C.GRAY}{'─' * 60}  ({elapsed:.1f}s){C.RESET}\n")


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _filter_tools(all_tools: list, persona) -> list:
    if persona is None:
        return list(all_tools)
    allowed  = set(persona.allowed_tools)
    filtered = [t for t in all_tools if t.name in allowed]
    unknown  = allowed - {t.name for t in all_tools}
    if unknown:
        print(f"Warning: persona references unknown tools: {', '.join(sorted(unknown))}")
    return filtered


def _log_persona_selection(slug: str, persona_name: str) -> None:
    log_dir = Path("logs")
    log_dir.mkdir(exist_ok=True)
    entry = {
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "event":     "persona_loaded",
        "slug":      slug,
        "name":      persona_name,
    }
    with open(log_dir / "persona_log.jsonl", "a", encoding="utf-8") as fh:
        fh.write(json.dumps(entry) + "\n")


def _setup_rag(base_url: str) -> object:
    from rag.embedder import RagEmbedder
    from rag.retriever import RagRetriever

    print("RAG: syncing context_docs/...")
    embedder = RagEmbedder(base_url=base_url)
    rebuilt  = embedder.sync()
    if rebuilt:
        print(f"  Rebuilt embeddings for: {', '.join(rebuilt)}")
    else:
        print("  All documents up to date.")

    total = embedder.collection.count()
    print(f"  Collection: {total} chunks indexed.\n")
    return RagRetriever(embedder.collection, embedder.embedder)


def _setup_guard(base_url: str):
    """Instantiate LlamaGuard and PresidioGuard; verify llama-guard3 is available."""
    import requests as _requests
    from guardrails.llama_guard import LlamaGuard
    from guardrails.presidio_guard import PresidioGuard

    try:
        resp      = _requests.get(f"{base_url}/api/tags", timeout=5)
        available = [m["name"] for m in resp.json().get("models", [])]
        if not any("llama-guard3" in name for name in available):
            print("Warning: llama-guard3 not found in Ollama.")
            print("  Pull it with:  ollama pull llama-guard3\n")
    except Exception:
        pass

    print("Guard: initialising Presidio (loading spacy model)...")
    llama_guard = LlamaGuard(base_url=base_url)
    presidio    = PresidioGuard()
    presidio.redact("warm-up")
    print("Guard: ready.\n")
    return llama_guard, presidio


# ---------------------------------------------------------------------------
# Startup check
# ---------------------------------------------------------------------------

def _check_ollama(base_url: str, model: str) -> None:
    import requests

    try:
        resp = requests.get(f"{base_url}/api/tags", timeout=5)
        resp.raise_for_status()
    except Exception as exc:
        print(f"\nError: cannot reach Ollama at {base_url}")
        print("  Start Ollama first:  ollama serve")
        print(f"  Detail: {exc}")
        sys.exit(1)

    available = [m["name"] for m in resp.json().get("models", [])]
    if not any(model in name for name in available):
        print(f"Warning: model '{model}' not found in Ollama.")
        print(f"  Pull it with:  ollama pull {model}")
        print(f"  Available:     {', '.join(available) or '(none)'}\n")


# ---------------------------------------------------------------------------
# Entry point
# ---------------------------------------------------------------------------

def main() -> None:
    parser = argparse.ArgumentParser(
        prog="agent.py",
        description="Omaha-Lab ReAct agent — local LLM security sandbox",
    )
    parser.add_argument(
        "--model",
        default=os.getenv("OLLAMA_MODEL", "llama3.1:8b"),
        help="Ollama model name  (default: $OLLAMA_MODEL or llama3.1:8b)",
    )
    parser.add_argument(
        "--base-url",
        dest="base_url",
        default=os.getenv("OLLAMA_BASE_URL", "http://localhost:11434"),
        help="Ollama base URL    (default: $OLLAMA_BASE_URL or http://localhost:11434)",
    )
    parser.add_argument(
        "--persona",
        default=None,
        metavar="NAME",
        help="Persona slug (customer_service | hr_assistant | security_analyst | code_assistant)",
    )
    parser.add_argument(
        "--rag",
        choices=["on", "off"],
        default="off",
        help="Enable RAG retrieval from context_docs/  (default: off)",
    )
    parser.add_argument(
        "--guard",
        choices=["on", "off"],
        default="off",
        help="Enable Llama Guard 3 input filter + Presidio output redaction  (default: off)",
    )
    parser.add_argument(
        "--hitl",
        choices=["on", "off"],
        default="off",
        help="Enable HITL authorization: pause before high-risk tool calls  (default: off)",
    )
    parser.add_argument(
        "--verbose-rag",
        action="store_true",
        default=False,
        help="Show individual [RETRIEVE] lines instead of the collapsed [RAG] summary",
    )
    parser.add_argument(
        "--list-personas",
        action="store_true",
        help="List available persona names and exit",
    )
    args = parser.parse_args()

    from personas import PersonaLoader

    if args.list_personas:
        names = PersonaLoader.list_personas()
        print("Available personas:", ", ".join(names) if names else "(none)")
        return

    persona = None
    if args.persona:
        try:
            persona = PersonaLoader.load(args.persona)
        except (FileNotFoundError, ValueError) as exc:
            print(f"Error loading persona: {exc}")
            sys.exit(1)
        _log_persona_selection(args.persona, persona.name)

    _check_ollama(args.base_url, args.model)

    retriever = _setup_rag(args.base_url) if args.rag == "on" else None

    llama_guard    = None
    presidio_guard = None
    if args.guard == "on":
        llama_guard, presidio_guard = _setup_guard(args.base_url)

    from graph import build_graph
    from tools import TOOLS

    active_tools = _filter_tools(TOOLS, persona)

    graph = build_graph(
        model=args.model,
        base_url=args.base_url,
        tools=active_tools,
        system_prompt=persona.system_prompt if persona else None,
        retriever=retriever,
        guard=llama_guard,
        presidio_guard=presidio_guard,
        hitl=(args.hitl == "on"),
    )
    run_repl(
        graph,
        model=args.model,
        tools=active_tools,
        persona=persona,
        rag=(args.rag == "on"),
        guard=(args.guard == "on"),
        hitl=(args.hitl == "on"),
        verbose_rag=args.verbose_rag,
    )


if __name__ == "__main__":
    main()
