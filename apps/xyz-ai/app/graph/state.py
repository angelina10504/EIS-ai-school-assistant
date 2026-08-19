"""Shared state threaded through every LangGraph node."""
from __future__ import annotations

from typing import Any, Literal, TypedDict


class ConversationState(TypedDict, total=False):
    # --- identity, resolved from the signed token only ---
    user_id: str
    role: Literal["student", "parent", "teacher", "principal"]
    user_name: str
    session_id: str
    language: str

    # --- this turn ---
    message: str
    intent: str | None
    slots: dict[str, Any]
    permitted: bool
    permission_reason: str | None
    persona_prompt: str
    tool_result: dict | None
    response: str | None
    history: list[dict]
    security_flags: list[str]

    # --- escalation handshake ---
    requires_confirmation: bool
    confirming: bool

    # --- plumbing (not persisted) ---
    db: Any            # SQLAlchemy Session for this request
    today: str
    trace: list[str]   # node names, in order — surfaced in the UI's debug panel


def new_state(**kwargs: Any) -> ConversationState:
    base: ConversationState = {
        "intent": None,
        "slots": {},
        "permitted": False,
        "permission_reason": None,
        "persona_prompt": "",
        "tool_result": None,
        "response": None,
        "history": [],
        "security_flags": [],
        "requires_confirmation": False,
        "confirming": False,
        "trace": [],
    }
    base.update(kwargs)  # type: ignore[typeddict-item]
    return base
