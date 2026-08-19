"""Node 9 — persist both sides of the turn so the next one has context."""
from __future__ import annotations

from app.db.models import ConversationMessage
from app.graph.state import ConversationState


def memory_writer(state: ConversationState) -> ConversationState:
    state["trace"].append("memory_writer")
    session = state["db"]
    session.add(
        ConversationMessage(
            session_id=state["session_id"],
            sender="user",
            content=state["message"],
            intent=state.get("intent"),
        )
    )
    session.add(
        ConversationMessage(
            session_id=state["session_id"],
            sender="assistant",
            content=state.get("response") or "",
            intent=state.get("intent"),
        )
    )
    session.flush()
    return state
