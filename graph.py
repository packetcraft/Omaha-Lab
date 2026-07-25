from __future__ import annotations
import json
import os
import re
import uuid
from langchain_core.messages import AIMessage, HumanMessage, SystemMessage, ToolMessage
from langchain_ollama import ChatOllama
from langgraph.graph import StateGraph, END
from langgraph.prebuilt import ToolNode
from langgraph.checkpoint.memory import MemorySaver

from state import AgentState
from tools import TOOLS as _DEFAULT_TOOLS

_TOOL_DISCIPLINE = SystemMessage(content=(
    "Tool-use rules:\n"
    "- Use web_search for any question involving current events, today's news, recent "
    "developments, prices, or scores. Never answer time-sensitive queries from training "
    "data — your knowledge has a cutoff date.\n"
    "- Use get_weather for weather questions.\n"
    "- Use write_file or read_file when asked to save or load content — do not write "
    "file content as text in your response, call the tool.\n"
    "- For multi-step tasks (e.g. search then save), call each required tool in sequence "
    "until every step is complete.\n"
    "- Answer directly (no tool) only for greetings, math, definitions, and stable facts."
))

_REASON_PROMPT = SystemMessage(content=(
    "Before calling any tools, think step-by-step:\n"
    "1. What exactly is the user asking for?\n"
    "2. Is a tool needed? If yes, which one and what arguments?\n"
    "3. If no tool is needed, plan your direct answer.\n"
    "Output your reasoning concisely. Do NOT call any tools yet."
))

_JSON_OBJECT_RE = re.compile(r"\{.*\}", re.DOTALL)


def _parse_fallback_tool_call(content: str, tool_names: set[str]) -> dict | None:
    """Recover a tool call some small models emit as JSON text in the message
    content instead of Ollama's structured tool-calling format. When that
    happens `response.tool_calls` stays empty, should_continue can't see it,
    and the raw JSON gets delivered to the user as if it were the final
    answer instead of the tool ever running."""
    if not content or "{" not in content:
        return None
    candidates = [content.strip()]
    match = _JSON_OBJECT_RE.search(content)
    if match:
        candidates.append(match.group(0))
    for candidate in candidates:
        try:
            data = json.loads(candidate)
        except (json.JSONDecodeError, TypeError):
            continue
        if not isinstance(data, dict):
            continue
        name = data.get("name")
        args = data.get("arguments", data.get("parameters"))
        if name in tool_names and isinstance(args, dict):
            return {"name": name, "args": args}
    return None


def build_graph(
    model: str | None = None,
    base_url: str | None = None,
    tools: list | None = None,
    system_prompt: str | None = None,
    retriever=None,
    guard=None,                # LlamaGuard instance; enables input filtering + RAG chunk scanning
    presidio_guard=None,       # PresidioGuard instance; enables PII redaction on output
    hitl: bool = False,        # Enable HITL authorization for high-risk tool calls
    hitl_node_factory=None,    # Optional override: callable() -> node fn (e.g. for Chainlit UI)
    max_iterations: int = 10,  # Hard cap on agent_node invocations per session
):
    model = model or os.getenv("OLLAMA_MODEL", "llama3.2:3b")
    base_url = base_url or os.getenv("OLLAMA_BASE_URL", "http://localhost:11434")
    tools = tools if tools is not None else list(_DEFAULT_TOOLS)

    llm = ChatOllama(model=model, base_url=base_url)
    llm_with_tools = llm.bind_tools(tools) if tools else llm
    _tool_names = {t.name for t in tools}

    # ------------------------------------------------------------------
    # Reasoning node — text-only LLM call (no tools bound), runs before agent
    # ------------------------------------------------------------------

    if tools:
        _tool_list_msg = SystemMessage(content=(
            "Available tools:\n"
            + "\n".join(f"- {t.name}: {t.description}" for t in tools)
        ))

        def reason_node(state: AgentState) -> dict:
            messages = list(state["messages"])
            prefix: list = [_REASON_PROMPT, _tool_list_msg]
            if system_prompt:
                prefix.append(SystemMessage(content=system_prompt))
            rag_ctx = state.get("rag_context") or ""
            if rag_ctx:
                prefix.append(SystemMessage(content=rag_ctx))
            response = llm.invoke(prefix + messages)
            return {"reasoning": response.content or ""}

    # ------------------------------------------------------------------
    # Core agent node
    # ------------------------------------------------------------------

    def agent_node(state: AgentState) -> dict:
        count = (state.get("iteration_count") or 0) + 1
        messages = list(state["messages"])
        prefix: list = []
        if tools:
            prefix.append(_TOOL_DISCIPLINE)
        if system_prompt:
            prefix.append(SystemMessage(content=system_prompt))
        rag_ctx = state.get("rag_context") or ""
        if rag_ctx:
            prefix.append(SystemMessage(content=rag_ctx))
        reasoning = state.get("reasoning") or ""
        if reasoning:
            prefix.append(SystemMessage(content=f"Your prior reasoning:\n{reasoning}"))
        response = llm_with_tools.invoke(prefix + messages)

        # Fallback: recover a tool call the model emitted as JSON text instead
        # of using structured tool-calling (see _parse_fallback_tool_call).
        if tools and not getattr(response, "tool_calls", None):
            fallback = _parse_fallback_tool_call(response.content or "", _tool_names)
            if fallback:
                response = AIMessage(
                    content="",
                    tool_calls=[{
                        "name": fallback["name"],
                        "args": fallback["args"],
                        "id": f"call_{uuid.uuid4().hex[:8]}",
                        "type": "tool_call",
                    }],
                )

        # Hard cap: if the iteration limit is hit and the model still wants to call
        # tools, replace the response so should_continue routes to END instead of tools.
        if count >= max_iterations and getattr(response, "tool_calls", None):
            print(
                f"\n[ITER LIMIT] Maximum iterations ({max_iterations}) reached"
                " — stopping tool calls."
            )
            response = AIMessage(
                content=(
                    f"I have reached the maximum number of steps ({max_iterations}) "
                    "and cannot make further tool calls. "
                    "Please try a more focused question."
                )
            )

        return {"messages": [response], "reasoning": "", "iteration_count": count}

    # ------------------------------------------------------------------
    # Routing: after agent node
    # ------------------------------------------------------------------

    def should_continue(state: AgentState) -> str:
        last = state["messages"][-1]
        if hasattr(last, "tool_calls") and last.tool_calls:
            return "hitl" if hitl else "tools"
        if presidio_guard is not None:
            return "output_guard"
        return END

    def after_hitl(state: AgentState) -> str:
        for msg in reversed(state["messages"]):
            if isinstance(msg, AIMessage):
                return "tools" if msg.tool_calls else "agent"
        return "agent"

    # ------------------------------------------------------------------
    # Input guard node (Llama Guard 3)
    # ------------------------------------------------------------------

    if guard is not None:
        def guard_input_node(state: AgentState) -> dict:  # noqa: E301
            last_human = next(
                (m for m in reversed(state["messages"]) if isinstance(m, HumanMessage)),
                None,
            )
            if last_human is None:
                return {"guard_blocked": False}

            result = guard.check_input(last_human.content)
            if not result.safe:
                guard.log_blocked(last_human.content, result)
                layer = (
                    "regex-prefilter"
                    if result.raw_response == "injection-prefilter"
                    else "llama-guard3"
                )
                blocked_msg = AIMessage(
                    content="I'm unable to respond to that request.",
                    additional_kwargs={
                        "guard_layer":    layer,
                        "guard_category": result.category or "",
                    },
                )
                return {"messages": [blocked_msg], "guard_blocked": True}
            return {"guard_blocked": False}

        def after_guard(state: AgentState) -> str:
            if state.get("guard_blocked"):
                return END
            if retriever is not None:
                return "rag"
            if tools:
                return "reason"
            return "agent"

    # ------------------------------------------------------------------
    # Output guard node (Presidio PII + canary detection)
    # ------------------------------------------------------------------

    if presidio_guard is not None:
        from guardrails import canary as _canary
        from guardrails.schema_guard import validate_tool_result as _validate_tool

        def output_guard_node(state: AgentState) -> dict:
            msgs = state["messages"]
            last = msgs[-1] if msgs else None
            if not isinstance(last, AIMessage) or (last.tool_calls or []):
                return {}

            text     = last.content or ""
            redacted = presidio_guard.redact(text)
            presidio_changed = redacted != text

            found = _canary.scan(redacted)
            if found:
                _canary.log_alert(found, redacted)
                redacted += (
                    "\n\n⚠️ [CANARY ALERT: one or more tracking tokens were detected "
                    "in this response — possible data exfiltration]"
                )

            # Schema validation: check every ToolMessage in state for malformed results.
            schema_violations: list[str] = []
            for m in msgs:
                if isinstance(m, ToolMessage):
                    ok, err = _validate_tool(getattr(m, "name", "tool"), m.content)
                    if not ok:
                        schema_violations.append(err)

            # Always return the message so _print_event can display [RESPOND]
            # and carry redaction signals for the guard receipt.
            # same id → add_messages deduplicates cleanly when nothing changed.
            return {"messages": [AIMessage(
                content=redacted,
                id=last.id,
                additional_kwargs={
                    "presidio_redacted": presidio_changed,
                    "canary_triggered":  bool(found),
                    "schema_violations": schema_violations,
                },
            )]}

    # ------------------------------------------------------------------
    # Graph assembly
    # ------------------------------------------------------------------

    graph = StateGraph(AgentState)
    graph.add_node("agent", agent_node)

    if tools:
        graph.add_node("reason", reason_node)
        graph.add_edge("reason", "agent")
        graph.add_node("tools", ToolNode(tools))
        graph.add_edge("tools", "agent")

    if hitl and tools:
        from graph_nodes.hitl_node import make_hitl_node as _default_hitl
        _factory = hitl_node_factory if hitl_node_factory is not None else _default_hitl
        graph.add_node("hitl", _factory())
        graph.add_conditional_edges("hitl", after_hitl)

    graph.add_conditional_edges("agent", should_continue)

    if presidio_guard is not None:
        graph.add_node("output_guard", output_guard_node)
        graph.add_edge("output_guard", END)

    if retriever is not None:
        from rag.graph_node import make_rag_node
        graph.add_node("rag", make_rag_node(retriever, guard=guard))
        graph.add_edge("rag", "reason" if tools else "agent")

    if guard is not None:
        graph.add_node("guard_input", guard_input_node)
        graph.add_conditional_edges("guard_input", after_guard)
        graph.set_entry_point("guard_input")
    elif retriever is not None:
        graph.set_entry_point("rag")
    elif tools:
        graph.set_entry_point("reason")
    else:
        graph.set_entry_point("agent")

    return graph.compile(checkpointer=MemorySaver())
