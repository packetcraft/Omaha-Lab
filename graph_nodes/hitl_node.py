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
        "tool": tool_name,
        "args": args,
        "decision": decision,
    }
    with open(_LOG_PATH, "a", encoding="utf-8") as fh:
        fh.write(json.dumps(entry) + "\n")


def make_hitl_node():
    """Return a LangGraph node that prompts the user before executing high-risk tools.

    High-risk calls are intercepted; the user is shown the tool name and arguments
    and prompted yes/no.  Denied calls produce a ToolMessage explaining the block so
    the agent can respond gracefully.  All decisions are appended to hitl_log.jsonl.
    """

    def hitl_node(state) -> dict:
        msgs = state["messages"]
        last = msgs[-1] if msgs else None

        if not isinstance(last, AIMessage) or not last.tool_calls:
            return {}

        approved: list = []
        denied_msgs: list = []

        for tc in last.tool_calls:
            name = tc["name"]
            args = tc.get("args", {})
            risk = RISK_LEVEL.get(name, "low")

            if risk == "high":
                print(f"\n[HITL] High-risk action requested")
                print(f"  Tool : {name}")
                print(f"  Args : {json.dumps(args, indent=4)}")
                try:
                    answer = input("[HITL] Approve this action? (yes/no): ").strip().lower()
                except (EOFError, KeyboardInterrupt):
                    answer = "no"

                decision = "approved" if answer in ("yes", "y") else "denied"
                _log_decision(name, args, decision)

                if decision == "approved":
                    print(f"[HITL] Approved — proceeding with {name}.")
                    approved.append(tc)
                else:
                    print(f"[HITL] Denied — {name} will not execute.")
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

        # Replace the AIMessage so ToolNode only sees the approved subset.
        # add_messages deduplicates by id, so sending the same id overwrites it.
        updated_ai = AIMessage(
            content=last.content or "",
            tool_calls=approved,
            id=last.id,
        )
        return {"messages": [updated_ai, *denied_msgs]}

    return hitl_node
