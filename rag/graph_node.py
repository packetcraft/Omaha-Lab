from langchain_core.messages import HumanMessage


def make_rag_node(retriever, guard=None):
    """Return a LangGraph node function that retrieves context for the latest human message.

    If a LlamaGuard instance is passed, each retrieved chunk is scanned before
    being injected into the context window. Blocked chunks are dropped and logged.
    """

    def rag_node(state: dict) -> dict:
        last_human = next(
            (m for m in reversed(state["messages"]) if isinstance(m, HumanMessage)),
            None,
        )
        if last_human is None:
            return {"rag_context": "", "retrieved_chunks": []}

        chunks = retriever.retrieve(last_human.content)
        if not chunks:
            return {"rag_context": "", "retrieved_chunks": []}

        if guard is not None:
            safe_chunks = []
            for chunk in chunks:
                result = guard.check_input(chunk["text"])
                if result.safe:
                    safe_chunks.append(chunk)
                else:
                    guard.log_blocked(chunk["text"], result)
                    print(
                        f"[GUARD]   RAG chunk from '{chunk['source']}' blocked "
                        f"({result.category or 'policy violation'})"
                    )
            chunks = safe_chunks

        if not chunks:
            return {"rag_context": "", "retrieved_chunks": []}

        sections = [f"[Source: {c['source']}]\n{c['text']}" for c in chunks]
        context = (
            "RETRIEVED CONTEXT — use the information below to inform your response:\n\n"
            + "\n\n---\n\n".join(sections)
        )

        return {"rag_context": context, "retrieved_chunks": chunks}

    return rag_node
