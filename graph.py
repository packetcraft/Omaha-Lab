import os
from langchain_core.messages import AIMessage, HumanMessage, SystemMessage
from langchain_ollama import ChatOllama
from langgraph.graph import StateGraph, END
from langgraph.prebuilt import ToolNode
from langgraph.checkpoint.memory import MemorySaver

from state import AgentState
from tools import TOOLS as _DEFAULT_TOOLS

_TOOL_DISCIPLINE = SystemMessage(content=(
    "Tool-use rules: only call a tool when the request genuinely requires live or "
    "external data (weather, web search, HTTP) or file access. "
    "For greetings, casual conversation, math, definitions, and general knowledge "
    "questions you can answer from training, respond directly — do NOT call any tool."
))


def build_graph(
    model: str | None = None,
    base_url: str | None = None,
    tools: list | None = None,
    system_prompt: str | None = None,
    retriever=None,
    guard=None,           # LlamaGuard instance; enables input filtering + RAG chunk scanning
    presidio_guard=None,  # PresidioGuard instance; enables PII redaction on output
    hitl: bool = False,   # Enable HITL authorization for high-risk tool calls
):
    model = model or os.getenv("OLLAMA_MODEL", "llama3.1:8b")
    base_url = base_url or os.getenv("OLLAMA_BASE_URL", "http://localhost:11434")
    tools = tools if tools is not None else list(_DEFAULT_TOOLS)

    llm = ChatOllama(model=model, base_url=base_url)
    llm_with_tools = llm.bind_tools(tools) if tools else llm

    # ------------------------------------------------------------------
    # Core agent node
    # ------------------------------------------------------------------

    def agent_node(state: AgentState) -> dict:
        messages = list(state["messages"])
        prefix: list = []
        if tools:
            prefix.append(_TOOL_DISCIPLINE)
        if system_prompt:
            prefix.append(SystemMessage(content=system_prompt))
        rag_ctx = state.get("rag_context") or ""
        if rag_ctx:
            prefix.append(SystemMessage(content=rag_ctx))
        response = llm_with_tools.invoke(prefix + messages)
        return {"messages": [response]}

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
        def guard_input_node(state: AgentState) -> dict:
            last_human = next(
                (m for m in reversed(state["messages"]) if isinstance(m, HumanMessage)),
                None,
            )
            if last_human is None:
                return {"guard_blocked": False}

            result = guard.check_input(last_human.content)
            if not result.safe:
                guard.log_blocked(last_human.content, result)
                blocked_msg = AIMessage(
                    content="I'm unable to respond to that request.",
                    additional_kwargs={
                        "guard_layer":    "llama-guard3",
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
            return "agent"

    # ------------------------------------------------------------------
    # Output guard node (Presidio PII + canary detection)
    # ------------------------------------------------------------------

    if presidio_guard is not None:
        from guardrails import canary as _canary

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

            # Always return the message so _print_event can display [RESPOND]
            # and carry redaction signals for the guard receipt.
            # same id → add_messages deduplicates cleanly when nothing changed.
            return {"messages": [AIMessage(
                content=redacted,
                id=last.id,
                additional_kwargs={
                    "presidio_redacted": presidio_changed,
                    "canary_triggered":  bool(found),
                },
            )]}

    # ------------------------------------------------------------------
    # Graph assembly
    # ------------------------------------------------------------------

    graph = StateGraph(AgentState)
    graph.add_node("agent", agent_node)

    if tools:
        graph.add_node("tools", ToolNode(tools))
        graph.add_edge("tools", "agent")

    if hitl and tools:
        from graph_nodes.hitl_node import make_hitl_node
        graph.add_node("hitl", make_hitl_node())
        graph.add_conditional_edges("hitl", after_hitl)

    graph.add_conditional_edges("agent", should_continue)

    if presidio_guard is not None:
        graph.add_node("output_guard", output_guard_node)
        graph.add_edge("output_guard", END)

    if retriever is not None:
        from rag.graph_node import make_rag_node
        graph.add_node("rag", make_rag_node(retriever, guard=guard))
        graph.add_edge("rag", "agent")

    if guard is not None:
        graph.add_node("guard_input", guard_input_node)
        graph.add_conditional_edges("guard_input", after_guard)
        graph.set_entry_point("guard_input")
    elif retriever is not None:
        graph.set_entry_point("rag")
    else:
        graph.set_entry_point("agent")

    return graph.compile(checkpointer=MemorySaver())
