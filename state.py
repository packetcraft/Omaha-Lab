from typing import Annotated
from typing import TypedDict
from langchain_core.messages import BaseMessage
from langgraph.graph.message import add_messages


class AgentState(TypedDict):
    messages: Annotated[list[BaseMessage], add_messages]
    # Populated by the RAG node each turn; empty string when RAG is disabled.
    rag_context: str
    # List of {text, source, distance} dicts — used for trace display only.
    retrieved_chunks: list
    # Set to True by the guard_input node when a message is blocked; routes graph to END.
    guard_blocked: bool
    # Pre-tool reasoning text produced by reason_node; cleared after agent_node consumes it.
    reasoning: str
    # Number of agent_node invocations in the current session; enforces max_iterations cap.
    iteration_count: int
