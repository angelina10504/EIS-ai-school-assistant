"""Node 1 — identity comes from the database row for the token subject.

Nothing typed into chat reaches this node's output. "I am the principal" is just
text in `message`; `role` is whatever the users table says.
"""
from __future__ import annotations

from app.db.models import User
from app.graph.state import ConversationState


def auth_resolver(state: ConversationState) -> ConversationState:
    session = state["db"]
    user = session.get(User, state["user_id"])
    if user is None:
        raise ValueError(f"Unknown user_id {state['user_id']}")

    state["trace"].append("auth_resolver")
    state["role"] = user.role  # type: ignore[typeddict-item]
    state["user_name"] = user.name
    state.setdefault("language", user.preferred_language or "en")
    return state
