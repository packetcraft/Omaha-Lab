"""Chainlit-compatible HITL node — uses a callback instead of input()."""
import json
from datetime import datetime, timezone
from pathlib import Path

from langchain_core.messages import AIMessage, ToolMessage

from tools.risk_registry import RISK_LEVEL

_LOG_PATH = Path(__file__).parent.parent / "workspace" / "logs" / "hitl_log.jsonl"


def _log_decision(tool_name: str, args: dict, decision: str) -> None:
    _LOG_PATH.parent.mkdir(exist_ok=True)
    entry = {
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "tool":      tool_name,
        "args":      args,
        "decision":  decision,
    }
    with open(_LOG_PATH, "a", encoding="utf-8") as fh:
        fh.write(json.dumps(entry) + "\n")


def make_ui_hitl_node(approval_fn):
    """
    Return a LangGraph HITL node that calls approval_fn(tool_name, args) -> bool
    instead of input(). approval_fn must be thread-safe — it is called from the
    background graph thread and should block until the UI delivers a decision.
    """

    def hitl_node(state) -> dict:
        msgs = state["messages"]
        last = msgs[-1] if msgs else None

        if not isinstance(last, AIMessage) or not last.tool_calls:
            return {}

        approved: list    = []
        denied_msgs: list = []

        for tc in last.tool_calls:
            name = tc["name"]
            args = tc.get("args", {})
            risk = RISK_LEVEL.get(name, "low")

            if risk == "high":
                decision_ok = approval_fn(name, args)
                decision    = "approved" if decision_ok else "denied"
                _log_decision(name, args, decision)

                if decision_ok:
                    approved.append(tc)
                else:
                    denied_msgs.append(
                        ToolMessage(
                            content=(
                                "Action blocked: the user denied this operation "
                                "during HITL review."
                            ),
                            tool_call_id=tc["id"],
                            name=name,
                        )
                    )
            else:
                approved.append(tc)

        if not denied_msgs:
            return {}

        updated_ai = AIMessage(
            content=last.content or "",
            tool_calls=approved,
            id=last.id,
        )
        return {"messages": [updated_ai, *denied_msgs]}

    return hitl_node
