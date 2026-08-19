"""Node 3 — load the recent turns so follow-ups resolve without restating context."""
from __future__ import annotations

from sqlalchemy import select

from app.config import get_settings
from app.db.models import ConversationMessage
from app.graph.state import ConversationState


def memory_loader(state: ConversationState) -> ConversationState:
    state["trace"].append("memory_loader")
    session = state["db"]
    limit = get_settings().history_turns

    rows = list(
        session.scalars(
            select(ConversationMessage)
            .where(ConversationMessage.session_id == state["session_id"])
            .order_by(ConversationMessage.created_at.desc(), ConversationMessage.id.desc())
            .limit(limit)
        ).all()
    )
    rows.reverse()
    state["history"] = [
        {"sender": r.sender, "content": r.content, "intent": r.intent} for r in rows
    ]
    return state
