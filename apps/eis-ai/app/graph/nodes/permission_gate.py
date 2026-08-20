"""Node 5 — plain code. The authorization decision, and the audit trail.

This runs on every turn whatever the model decided, and it writes to audit_log on
both outcomes.
"""
from __future__ import annotations

from app.auth.audit import log_permission_check
from app.auth.permissions import check_permission
from app.graph.state import ConversationState


def permission_gate(state: ConversationState) -> ConversationState:
    state["trace"].append("permission_gate")
    session = state["db"]
    role = state["role"]
    intent = state.get("intent") or "general_chat"

    if state.get("security_flags"):
        log_permission_check(
            session,
            user_id=state["user_id"],
            action="security_guard",
            resource=",".join(state["security_flags"]),
            allowed=False,
        )

    decision = check_permission(role, intent)
    log_permission_check(
        session,
        user_id=state["user_id"],
        action=f"intent:{intent}",
        resource=f"role:{role} scope:{decision.scope.value}",
        allowed=decision.allowed,
    )

    state["permitted"] = decision.allowed
    state["permission_reason"] = decision.reason
    state["slots"]["scope"] = decision.scope.value
    return state
