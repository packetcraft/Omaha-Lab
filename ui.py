#!/usr/bin/env python3
"""Omaha-Lab Chainlit web UI — optional browser interface for the LangGraph agent.

Usage:
    chainlit run ui.py          # http://localhost:8000
    chainlit run ui.py -w       # with auto-reload

The CLI (agent.py) is unchanged and continues to work independently.
"""
from __future__ import annotations
import asyncio
import json
import os
import queue
import re
import sys
import threading
import uuid
from pathlib import Path

# Ensure the project root is on sys.path when Chainlit launches ui.py
sys.path.insert(0, str(Path(__file__).parent))

import chainlit as cl
from chainlit.input_widget import MultiSelect, Select, Switch
from dotenv import load_dotenv
from langchain_core.messages import AIMessage, HumanMessage, ToolMessage

load_dotenv()

# ---------------------------------------------------------------------------
# Phoenix observability — wire automatically if the server is already running.
# Silent no-op if Phoenix never comes up (observability is optional).
# Start Phoenix separately, or together via `make dev`:
#   venv/Scripts/python -m phoenix.server.main serve   (Windows)
#   venv/bin/python -m phoenix.server.main serve       (macOS)
# ---------------------------------------------------------------------------

def _connect_phoenix() -> bool:
    try:
        from phoenix.otel import register
        from openinference.instrumentation.langchain import LangChainInstrumentor
        import requests as _req
        _req.get("http://127.0.0.1:6006", timeout=2)
        register(project_name="omaha-lab")
        LangChainInstrumentor().instrument()
        return True
    except Exception:
        return False


def _try_phoenix() -> None:
    if _connect_phoenix():
        return
    # Phoenix wasn't up yet — e.g. `make dev` starts Chainlit and Phoenix in
    # parallel via honcho, and Phoenix's migrations + uvicorn startup take a
    # few seconds. Retry in the background instead of giving up permanently.
    def _retry() -> None:
        import time
        for _ in range(14):
            time.sleep(1)
            if _connect_phoenix():
                return

    threading.Thread(target=_retry, daemon=True).start()


_try_phoenix()

_BASE_URL = os.getenv("OLLAMA_BASE_URL", "http://localhost:11434")
_MODEL    = os.getenv("OLLAMA_MODEL",    "llama3.2:3b")


def _list_models(base_url: str) -> list[str]:
    """Query Ollama for locally pulled models that support tool-calling.
    Falls back to just the configured default if Ollama is unreachable
    or nothing tool-capable is found (e.g. `--rag on`-only setups)."""
    try:
        import requests as _req
        resp = _req.get(f"{base_url}/api/tags", timeout=3)
        resp.raise_for_status()
        names = [
            m["name"] for m in resp.json().get("models", [])
            if "tools" in (m.get("capabilities") or [])
        ]
        if _MODEL not in names:
            names.append(_MODEL)
        return sorted(names) if names else [_MODEL]
    except Exception:
        return [_MODEL]

_GUARD_LABELS: dict[str, str] = {
    "S1": "Violent Crimes",       "S2": "Non-Violent Crimes",
    "S3": "Sex-Related Crimes",   "S4": "Child Sexual Exploitation",
    "S5": "Defamation",           "S6": "Specialized Advice",
    "S7": "Privacy",              "S8": "Intellectual Property",
    "S9": "Indiscriminate Weapons", "S10": "Hate",
    "S11": "Suicide & Self-Harm", "S12": "Sexual Content",
    "S13": "Elections",           "S14": "Code Interpreter Abuse",
    "S15": "Prompt Injection",
}

# ---------------------------------------------------------------------------
# Lab Mode profiles  — (default_persona, rag, guard, hitl)
# Persona is the default for the profile; participants can override via Chat Settings.
# ---------------------------------------------------------------------------

_PROFILES: dict[str, tuple] = {
    # Bare/Guarded need the full tool set available — Bare to demonstrate an
    # open attack surface, Guarded so HITL/guard layers have risky tool calls
    # to actually intercept. "admin" (not None) keeps that intent explicit.
    "Bare":         ("admin",            False, False, False),
    "Guarded":      ("admin",            False, True,  True),
    "RAG Analyst":  ("security_analyst", True,  False, False),
    "Full Defense": ("hr_assistant",     True,  True,  True),
}

# Persona options available in Chat Settings
_PERSONA_OPTIONS: dict[str, str | None] = {
    "simple-chat":       "simple_chat",
    "customer_service":  "customer_service",
    "hr_assistant":      "hr_assistant",
    "security_analyst":  "security_analyst",
    "code_assistant":    "code_assistant",
    "devops_assistant":  "devops_assistant",
    "admin":             "admin",
}

# Persona -> [(display name, path relative to labs/), ...], sourced from each
# persona YAML's "Used in: Lab X.Y" description text.
_PERSONA_LABS: dict[str, list[tuple[str, str]]] = {
    "customer_service": [
        ("Lab 2.1 — Direct Injection",          "module2/lab2_1_direct_injection.md"),
        ("Lab 2.5 — System Prompt Leakage",     "module2/lab2_5_system_prompt_leakage.md"),
    ],
    "hr_assistant": [
        ("Lab 2.4 — PII Extraction",            "module2/lab2_4_pii_extraction.md"),
        ("Lab 2.6 — Excessive Agency",          "module2/lab2_6_excessive_agency.md"),
    ],
    "security_analyst": [
        ("Lab 2.2 — Indirect Injection (Tool)", "module2/lab2_2_indirect_injection_tool.md"),
        ("Lab 2.3 — Indirect Injection (RAG)",  "module2/lab2_3_indirect_injection_rag.md"),
        ("Lab 2.8 — RAG Poisoning",             "module2/lab2_8_rag_poisoning.md"),
    ],
    "code_assistant": [
        ("Lab 2.7 — Improper Output Handling",  "module2/lab2_7_improper_output.md"),
        ("Lab 3.8 — Supply Chain Hygiene",      "module3/lab3_8_supply_chain.md"),
    ],
    "devops_assistant": [
        ("Lab 2.10 — Unconstrained Shell Tool", "module2/lab2_10_unconstrained_shell.md"),
    ],
}

_LABS_DIR = Path(__file__).parent / "labs"


def _persona_tool_names(persona_slug: str) -> list[str]:
    """The tool-name ceiling for a persona — what _filter_tools would
    actually bind, not the raw allowed_tools list (which may reference a
    typo'd/unknown tool name that _filter_tools silently drops)."""
    from tools import TOOLS
    from agent import _filter_tools
    from personas import PersonaLoader

    persona = PersonaLoader.load(persona_slug)
    return [t.name for t in _filter_tools(TOOLS, persona)]


def _load_lab_docs(persona_slug: str | None) -> list[cl.Text]:
    """Return cl.Text side-panel elements for every lab referenced by this persona.
    Missing files are skipped rather than raised — a typo here shouldn't break
    session setup."""
    elements: list[cl.Text] = []
    for title, rel_path in _PERSONA_LABS.get(persona_slug or "", []):
        path = _LABS_DIR / rel_path
        try:
            content = path.read_text(encoding="utf-8")
        except OSError:
            continue
        elements.append(cl.Text(name=title, content=content, display="side"))
    return elements


# ---------------------------------------------------------------------------
# General Lab Guide browser — every lab, not just the current persona's
# ---------------------------------------------------------------------------

_MODULE_NAMES: dict[int, str] = {
    1: "Module 1 — Foundations",
    2: "Module 2 — Offensive Security",
    3: "Module 3 — Defensive Architecture",
    4: "Module 4 — Architecture Deep Dive",
}

_LAB_FILENAME_RE = re.compile(r"^lab(\d+)_(\d+)_")


def _discover_labs() -> list[dict]:
    """Glob every lab doc under labs/module*/ and pull its title from the
    first line ("# Lab X.Y — Title"). Computed once at import time — the
    lab set doesn't change while the app is running."""
    labs = []
    for path in sorted(_LABS_DIR.glob("module*/*.md")):
        m = _LAB_FILENAME_RE.match(path.name)
        if not m:
            continue
        try:
            first_line = path.read_text(encoding="utf-8").splitlines()[0]
        except (OSError, IndexError):
            continue
        labs.append({
            "module": int(m.group(1)),
            "number": int(m.group(2)),
            "title":  first_line.lstrip("#").strip(),
            "path":   str(path.relative_to(_LABS_DIR)),
        })
    labs.sort(key=lambda d: (d["module"], d["number"]))
    return labs


_ALL_LABS = _discover_labs()


def _labs_by_module() -> dict[int, list[dict]]:
    grouped: dict[int, list[dict]] = {}
    for lab in _ALL_LABS:
        grouped.setdefault(lab["module"], []).append(lab)
    return grouped


@cl.action_callback("browse_labs")
async def on_browse_labs(action: cl.Action) -> None:
    """One flat index of every lab, grouped by module for readability — no
    drill-down, no intermediate screen to lose track of."""
    grouped = _labs_by_module()
    lines = ["**Lab Guide** — click a number below to open that lab.\n"]
    actions = []
    for m in sorted(grouped):
        lines.append(f"\n**{_MODULE_NAMES.get(m, f'Module {m}')}**")
        for lab in grouped[m]:
            lines.append(f"- {lab['module']}.{lab['number']} — {lab['title'].split('—', 1)[-1].strip()}")
            actions.append(cl.Action(
                name="open_lab",
                label=f"{lab['module']}.{lab['number']}",
                payload={"path": lab["path"]},
            ))
    await cl.Message(content="\n".join(lines), author="System", actions=actions).send()


@cl.action_callback("open_lab")
async def on_open_lab(action: cl.Action) -> None:
    rel_path = action.payload["path"]
    path = _LABS_DIR / rel_path
    try:
        content = path.read_text(encoding="utf-8")
    except OSError:
        await cl.Message(content=f"Could not open `{rel_path}`.", author="System").send()
        return

    title = next((lab["title"] for lab in _ALL_LABS if lab["path"] == rel_path), rel_path)
    await cl.Message(
        content=f"Opened **{title}** — click the panel below to read it.",
        author="System",
        elements=[cl.Text(name=title, content=content, display="side")],
    ).send()


_PROFILE_DESC: dict[str, str] = {
    "Bare": (
        "Raw agent — no guardrails, no RAG. Attack surface fully open. "
        "Use for **Module 2** offensive labs."
    ),
    "Guarded": (
        "Llama Guard 3 input filtering · Presidio PII redaction · HITL authorization. "
        "No RAG. Use for **Module 3** single-layer labs."
    ),
    "RAG Analyst": (
        "Security Analyst persona with RAG retrieval from `context_docs/`. "
        "No guardrails — ideal for RAG poisoning and indirect injection labs."
    ),
    "Full Defense": (
        "All defensive layers active: RAG · Llama Guard 3 · Presidio · HITL. "
        "HR Assistant persona. Use for **Module 3** full-stack labs."
    ),
}


# ---------------------------------------------------------------------------
# Lab Mode selector
# ---------------------------------------------------------------------------

@cl.set_chat_profiles
async def chat_profiles(current_user=None, current_chat_profile=None):
    return [
        cl.ChatProfile(name=name, markdown_description=_PROFILE_DESC[name])
        for name in _PROFILES
    ]


# ---------------------------------------------------------------------------
# Session initialisation
# ---------------------------------------------------------------------------

@cl.on_chat_start
async def on_chat_start():
    profile = cl.user_session.get("chat_profile") or "Bare"
    default_persona, use_rag, use_guard, use_hitl = _PROFILES.get(profile, _PROFILES["Bare"])

    available_models = await asyncio.to_thread(_list_models, _BASE_URL)
    cl.user_session.set("available_models", available_models)

    tool_ceiling = _persona_tool_names(default_persona)
    cl.user_session.set("persona_slug", default_persona)

    # Chat Settings — profile presets populate all four controls; each is individually overridable.
    settings = await cl.ChatSettings([
        Select(
            id="persona",
            label="Persona",
            values=list(_PERSONA_OPTIONS.keys()),
            initial_value=default_persona or "simple-chat",
        ),
        Select(
            id="model",
            label="Model",
            values=available_models,
            initial_value=_MODEL if _MODEL in available_models else available_models[0],
        ),
        MultiSelect(
            id="tools",
            label="Active Tools (subset of what the persona allows)",
            values=tool_ceiling,
            initial=tool_ceiling,
        ),
        Switch(id="guard", label="Guard (Llama Guard 3 + Presidio)", initial=use_guard),
        Switch(id="rag",   label="RAG",                              initial=use_rag),
        Switch(id="hitl",  label="HITL (Human-in-the-Loop)",         initial=use_hitl),
    ]).send()

    persona_slug   = _PERSONA_OPTIONS.get(settings.get("persona", "simple-chat"))
    model          = settings.get("model", _MODEL)
    selected_tools = [t for t in settings.get("tools", tool_ceiling) if t in tool_ceiling]
    use_rag        = settings.get("rag",   use_rag)
    use_guard      = settings.get("guard", use_guard)
    use_hitl       = settings.get("hitl",  use_hitl)

    await cl.Message(
        content=f"**Lab Mode: {profile}** — initialising agent…",
        author="System",
        actions=[cl.Action(name="browse_labs", label="📖 Browse All Labs", payload={})],
    ).send()

    await _init_session(persona_slug, use_rag, use_guard, use_hitl, model, selected_tools)


async def _init_session(persona_slug, use_rag, use_guard, use_hitl, model=None, selected_tools=None):
    """Build the agent session and store it. Called at start and on settings change."""
    model = model or _MODEL
    try:
        session = await asyncio.to_thread(
            _build_session, persona_slug, use_rag, use_guard, use_hitl, model, selected_tools
        )
    except Exception as exc:
        await cl.Message(
            content=f"Setup failed: `{exc}`\n\nIs Ollama running? (`ollama serve`)",
            author="System",
        ).send()
        return

    cl.user_session.set("session", session)

    parts = [f"persona: **{persona_slug.replace('_', ' ').title() if persona_slug else 'simple-chat'}**"]
    parts.append(f"model: **{model}**")
    if selected_tools is not None:
        parts.append(f"tools: **{', '.join(selected_tools) or 'none'}**")
    parts.append(f"rag: **{'on' if use_rag else 'off'}**")
    parts.append(f"guard: **{'on' if use_guard else 'off'}**")
    parts.append(f"hitl: **{'on' if use_hitl else 'off'}**")

    lab_docs = _load_lab_docs(persona_slug)
    ready_content = "Ready — " + " · ".join(parts)
    if lab_docs:
        ready_content += f"\n\nRelated lab(s) attached below — click to open. ({len(lab_docs)})"
    await cl.Message(content=ready_content, author="System", elements=lab_docs).send()

    diagram = _pipeline_mermaid(use_rag, use_guard, use_hitl)
    await cl.Message(content=f"**Pipeline topology**\n\n{diagram}", author="System").send()


@cl.on_settings_update
async def on_settings_update(settings):
    """Rebuild the agent when any Chat Setting changes. All values come from the widgets."""
    persona_slug = _PERSONA_OPTIONS.get(settings.get("persona", "simple-chat"))
    model        = settings.get("model", _MODEL)
    use_rag      = settings.get("rag",   False)
    use_guard    = settings.get("guard", False)
    use_hitl     = settings.get("hitl",  False)

    tool_ceiling  = _persona_tool_names(persona_slug)
    prev_persona  = cl.user_session.get("persona_slug")
    persona_changed = persona_slug != prev_persona
    cl.user_session.set("persona_slug", persona_slug)

    if persona_changed:
        # The tool ceiling just changed — reset the selector to "everything
        # this persona allows" and refresh the panel so its values= (the
        # checkbox list itself) reflects the new ceiling, not the old one.
        selected_tools = tool_ceiling
        available_models = cl.user_session.get("available_models") or [model]
        await cl.ChatSettings([
            Select(id="persona", label="Persona", values=list(_PERSONA_OPTIONS.keys()),
                   initial_value=settings.get("persona", "simple-chat")),
            Select(id="model", label="Model", values=available_models, initial_value=model),
            MultiSelect(id="tools", label="Active Tools (subset of what the persona allows)",
                        values=tool_ceiling, initial=tool_ceiling),
            Switch(id="guard", label="Guard (Llama Guard 3 + Presidio)", initial=use_guard),
            Switch(id="rag",   label="RAG",                              initial=use_rag),
            Switch(id="hitl",  label="HITL (Human-in-the-Loop)",         initial=use_hitl),
        ]).send()
    else:
        # Clamp defensively — never trust a selection outside the current
        # ceiling, even though the widget itself shouldn't allow it.
        selected_tools = [t for t in settings.get("tools", tool_ceiling) if t in tool_ceiling]

    label = persona_slug.replace("_", " ").title() if persona_slug else "simple-chat"
    await cl.Message(
        content=f"Settings changed (persona: **{label}**, model: **{model}**) — rebuilding agent…",
        author="System",
    ).send()

    await _init_session(persona_slug, use_rag, use_guard, use_hitl, model, selected_tools)


def _build_session(persona_slug, use_rag, use_guard, use_hitl, model=None, selected_tools=None):
    """Synchronous setup — runs in a background thread via asyncio.to_thread."""
    model = model or _MODEL
    from graph import build_graph
    from tools import TOOLS
    from agent import _filter_tools, _setup_rag, _setup_guard
    from personas import PersonaLoader

    persona      = PersonaLoader.load(persona_slug) if persona_slug else None
    active_tools = _filter_tools(TOOLS, persona)
    if selected_tools is not None:
        # Subtract-only: never grant a tool the persona doesn't already
        # allow, only narrow further within what _filter_tools returned.
        active_tools = [t for t in active_tools if t.name in selected_tools]
    retriever    = _setup_rag(_BASE_URL) if use_rag else None

    llama_guard = presidio_guard = None
    if use_guard:
        llama_guard, presidio_guard = _setup_guard(_BASE_URL)

    # For HITL: two queues bridge the graph thread and the async UI loop.
    #   hitl_req_q: graph thread → UI  (tool_name, args)
    #   hitl_res_q: UI → graph thread  (bool: approved)
    hitl_req_q = hitl_res_q = None
    hitl_factory = None
    if use_hitl:
        hitl_req_q = queue.Queue()
        hitl_res_q = queue.Queue()

        def _approval_fn(tool_name, args):
            hitl_req_q.put((tool_name, args))
            return hitl_res_q.get(timeout=300)  # blocks graph thread until UI responds

        from graph_nodes.hitl_ui import make_ui_hitl_node
        hitl_factory = lambda: make_ui_hitl_node(_approval_fn)

    graph = build_graph(
        model=model,
        base_url=_BASE_URL,
        tools=active_tools,
        system_prompt=persona.system_prompt if persona else None,
        retriever=retriever,
        guard=llama_guard,
        presidio_guard=presidio_guard,
        hitl=use_hitl,
        hitl_node_factory=hitl_factory,
    )

    return {
        "graph":      graph,
        "use_rag":    use_rag,
        "use_guard":  use_guard,
        "use_hitl":   use_hitl,
        "hitl_req_q": hitl_req_q,
        "hitl_res_q": hitl_res_q,
        "thread_id":  str(uuid.uuid4()),
    }


# ---------------------------------------------------------------------------
# Message handler
# ---------------------------------------------------------------------------

@cl.on_message
async def on_message(user_msg: cl.Message):
    session = cl.user_session.get("session")
    if not session:
        await cl.Message(
            content="Session not initialised — reload the page.", author="System"
        ).send()
        return

    graph      = session["graph"]
    lc_config  = {"configurable": {"thread_id": session["thread_id"]}}
    use_rag    = session["use_rag"]
    use_guard  = session["use_guard"]
    use_hitl   = session["use_hitl"]
    hitl_req_q = session.get("hitl_req_q")
    hitl_res_q = session.get("hitl_res_q")

    event_q: queue.Queue = queue.Queue()

    def _run_graph():
        try:
            for ev in graph.stream(
                {"messages": [HumanMessage(content=user_msg.content)]},
                config=lc_config,
                stream_mode="updates",
            ):
                event_q.put(("event", ev))
        except Exception as exc:
            event_q.put(("error", str(exc)))
        finally:
            event_q.put(("done", None))

    threading.Thread(target=_run_graph, daemon=True).start()

    final_text: str | None = None
    fired_nodes: set[str] = set()
    guard_blocked = False

    while True:
        # Service pending HITL approval requests before draining new events.
        # The graph thread blocks inside the HITL node until we respond here.
        if use_hitl and hitl_req_q and not hitl_req_q.empty():
            tool_name, args = hitl_req_q.get_nowait()
            action = await cl.AskActionMessage(
                content=(
                    f"**HITL — High-risk action requested**\n\n"
                    f"**Tool:** `{tool_name}`\n"
                    f"```json\n{json.dumps(args, indent=2)}\n```"
                ),
                actions=[
                    cl.Action(name="approve", label="Approve", payload={"value": "approved"}),
                    cl.Action(name="deny",    label="Deny",    payload={"value": "denied"}),
                ],
            ).send()
            approved = action is not None and action.get("name") == "approve"
            hitl_res_q.put(approved)
            status = "Approved" if approved else "Denied"
            await cl.Message(content=f"HITL decision: **{status}**", author="System").send()

        try:
            kind, payload = event_q.get_nowait()
        except queue.Empty:
            await asyncio.sleep(0.05)
            continue

        if kind == "done":
            break

        if kind == "error":
            await cl.Message(content=f"Agent error: `{payload}`", author="System").send()
            break

        for node_name, update in payload.items():
            if not node_name.startswith("__") and isinstance(update, dict):
                fired_nodes.add(node_name)
                if node_name == "guard_input" and update.get("guard_blocked"):
                    guard_blocked = True

        final_text = await _handle_event(payload, use_guard) or final_text

    # HITL returns {} for low-risk pass-throughs so LangGraph emits no stream event.
    # If tools ran, HITL must have executed (it's the only route to the tools node).
    if use_hitl and "tools" in fired_nodes:
        fired_nodes.add("hitl")

    # Per-turn pipeline path diagram
    diagram = _pipeline_mermaid(use_rag, use_guard, use_hitl, fired=fired_nodes, guard_blocked=guard_blocked)
    async with cl.Step(name="Pipeline path", type="tool") as step:
        step.output = diagram

    if final_text:
        await cl.Message(content=final_text).send()


# ---------------------------------------------------------------------------
# Pipeline diagram  (Option D — D-02)
# ---------------------------------------------------------------------------

def _pipeline_mermaid(
    use_rag: bool,
    use_guard: bool,
    use_hitl: bool,
    fired: set[str] | None = None,
    guard_blocked: bool = False,
) -> str:
    """Return a markdown inline-chain showing pipeline topology and per-turn path.

    Node badges:
        🟢  fired this turn
        🔵  configured but did not fire
        🔴  guard blocked the input
    """
    is_topology = fired is None
    fired = fired or set()

    def badge(key: str, label: str) -> str:
        if key == "guard_input" and guard_blocked:
            return f"🔴 **{label}**"
        return f"{'🟢' if key in fired else '🔵'} **{label}**"

    if guard_blocked:
        return (
            f"Input → {badge('guard_input', 'Input Guard')} → 🔴 **Blocked**\n\n"
            "_🟢 fired  ·  🔵 configured  ·  🔴 blocked_"
        )

    if is_topology:
        # Branching diagram in a code block so alignment is preserved
        main_parts = ["Input"]
        if use_guard:
            main_parts.append("Input Guard")
        if use_rag:
            main_parts.append("RAG")
        main_parts.append("Reason")
        main_parts.append("Agent")
        main_line = " → ".join(main_parts)

        # Indent branch lines so they start under "Agent"
        indent = " " * (len(main_line) - len("Agent"))

        tool_parts = []
        if use_hitl:
            tool_parts.append("HITL")
        tool_parts.append("Tools")
        tool_line = indent + "Agent ──[tool call]──→ " + " → ".join(tool_parts)

        done_parts = []
        if use_guard:
            done_parts.append("Output Guard")
        done_parts.append("Response")
        done_line = indent + "Agent ──[done]──→ " + " → ".join(done_parts)

        return f"```\n{main_line}\n{tool_line}\n{done_line}\n```"

    # Per-turn path: flat chain showing what actually fired vs what was configured
    chain = ["Input"]
    if use_guard:
        chain.append(badge("guard_input", "Input Guard"))
    if use_rag:
        chain.append(badge("rag", "RAG"))
    chain.append(badge("reason", "Reason"))
    chain.append(badge("agent", "Agent"))
    if use_hitl:
        chain.append(badge("hitl", "HITL"))
    chain.append(badge("tools", "Tools"))
    if use_guard:
        chain.append(badge("output_guard", "Output Guard"))
    chain.append("Response")

    return " → ".join(chain) + "\n\n_🟢 fired  ·  🔵 configured_"


# ---------------------------------------------------------------------------
# Event renderer
# ---------------------------------------------------------------------------

async def _handle_event(event: dict, use_guard: bool) -> str | None:
    """Render one LangGraph stream event as Chainlit steps. Returns response text or None."""
    final_text = None

    for node_name, update in event.items():
        if node_name.startswith("__") or node_name == "hitl" or not isinstance(update, dict):
            continue

        # Dedicated reasoning node — true pre-tool thought
        if node_name == "reason":
            thought = update.get("reasoning") or ""
            if thought:
                async with cl.Step(name="Reasoning", type="llm") as step:
                    step.output = thought

        # RAG retrieval -------------------------------------------------------
        chunks = update.get("retrieved_chunks", [])
        if chunks:
            sources: dict[str, int] = {}
            for c in chunks:
                src = c.get("source", "?")
                sources[src] = sources.get(src, 0) + 1
            src_str   = ", ".join(f"{s}({n})" if n > 1 else s for s, n in sources.items())
            dist_vals = [c["distance"] for c in chunks if c.get("distance")]
            dist_str  = f" · dist {min(dist_vals):.3f}–{max(dist_vals):.3f}" if dist_vals else ""

            async with cl.Step(name="RAG Retrieval", type="retrieval") as step:
                lines = [f"{len(chunks)} chunk(s) from {src_str}{dist_str}\n"]
                for c in chunks:
                    lines.append(f"**{c.get('source', '?')}:** {c.get('text', '')[:200]}…")
                step.output = "\n".join(lines)

        # Guard input — pass (no messages in update) --------------------------
        if (
            node_name == "guard_input"
            and "guard_blocked" in update
            and not update["guard_blocked"]
            and not update.get("messages")
        ):
            async with cl.Step(name="Input Guard — passed", type="tool") as step:
                step.output = "Input cleared (regex pre-filter + Llama Guard 3)"

        # Messages from each node ---------------------------------------------
        for msg in update.get("messages", []):
            if isinstance(msg, AIMessage):
                if msg.tool_calls:
                    if msg.content:
                        async with cl.Step(name="Reasoning", type="llm") as step:
                            step.output = msg.content if isinstance(msg.content, str) else str(msg.content)
                    for tc in msg.tool_calls:
                        async with cl.Step(name=f"Tool call: {tc['name']}", type="tool") as step:
                            step.input = json.dumps(tc.get("args", {}), indent=2)

                elif node_name == "guard_input":
                    layer = msg.additional_kwargs.get("guard_layer", "guard")
                    cat   = msg.additional_kwargs.get("guard_category", "")
                    label = _GUARD_LABELS.get(cat, cat) if cat else "policy violation"
                    async with cl.Step(name="Input Guard — BLOCKED", type="tool") as step:
                        step.output = f"Layer: {layer} | {cat}: {label}"
                    content = msg.content
                    final_text = content if isinstance(content, str) else str(content or "")

                elif node_name == "output_guard":
                    redacted   = msg.additional_kwargs.get("presidio_redacted", False)
                    canary     = msg.additional_kwargs.get("canary_triggered",  False)
                    violations = msg.additional_kwargs.get("schema_violations",  [])
                    schema_str = f"{len(violations)} violation(s)" if violations else "clean"
                    async with cl.Step(name="Output Guard", type="tool") as step:
                        step.output = (
                            f"Presidio PII: {'redacted' if redacted else 'clean'} · "
                            f"Canary: {'ALERT' if canary else 'clean'} · "
                            f"Schema: {schema_str}"
                        )
                    content = msg.content
                    final_text = content if isinstance(content, str) else ""

                elif node_name == "agent" and not use_guard:
                    content = msg.content
                    final_text = content if isinstance(content, str) else ""

            elif isinstance(msg, ToolMessage):
                tool_name = getattr(msg, "name", "tool")
                async with cl.Step(name=f"Tool result: {tool_name}", type="tool") as step:
                    step.output = msg.content if isinstance(msg.content, str) else str(msg.content)

    return final_text
