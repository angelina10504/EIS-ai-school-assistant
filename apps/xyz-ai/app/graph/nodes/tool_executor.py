"""Node 7 — run the tool the intent needs, or produce the reason we didn't.

Everything this node emits is a `tool_result` dict with a `kind`. The formatter
turns that into language; it never invents facts that aren't in here.
"""
from __future__ import annotations

import re
from datetime import date as date_cls

from app.graph import pending
from app.graph.dates import resolve_date
from app.graph.state import ConversationState
from app.tools.analytics_tools import get_attendance_analytics
from app.tools.attendance_tools import get_attendance, list_class_roster, mark_attendance
from app.tools.escalation_tools import request_escalation, resolve_escalation_target
from app.tools.scope import resolve_student

# "who is in my class?" is a scope question, not an attendance lookup.
_ROSTER_RE = re.compile(
    r"\b(who(?:'s| is| are)?\s+(in|on)\s+my\s+(class|classes|roster)|class list|"
    r"my (students|class list|roster)|roster)\b",
    re.I,
)


def tool_executor(state: ConversationState) -> ConversationState:
    state["trace"].append("tool_executor")
    session = state["db"]
    slots = state.get("slots", {})
    intent = state.get("intent")
    today = date_cls.fromisoformat(state["today"]) if state.get("today") else date_cls.today()

    if state.get("security_flags"):
        from app.auth.guardrails import refusal_for

        state["tool_result"] = {
            "kind": "security_refusal",
            "reason": refusal_for(state["security_flags"]),
            "flags": state["security_flags"],
        }
        return state

    if not state.get("permitted"):
        state["tool_result"] = {
            "kind": "permission_denied",
            "reason": state.get("permission_reason"),
            "intent": intent,
        }
        return state

    if intent == "view_attendance":
        if state["role"] == "teacher" and _ROSTER_RE.search(state.get("message", "")):
            state["tool_result"] = {"kind": "roster", **list_class_roster(session, teacher_id=state["user_id"])}
            return state
        result = get_attendance(
            session,
            requester_id=state["user_id"],
            requester_role=state["role"],
            student_name=slots.get("student_name"),
            on_date=resolve_date(slots.get("date_phrase"), today),
        )
        state["tool_result"] = {"kind": "attendance", **result}

    elif intent == "mark_attendance":
        status = slots.get("status")
        if not status:
            state["tool_result"] = {
                "kind": "clarification",
                "question": "Should I mark them present, absent or late?",
                "missing": "status",
            }
            return state
        result = mark_attendance(
            session,
            teacher_id=state["user_id"],
            status=status,
            student_name=slots.get("student_name"),
            on_date=resolve_date(slots.get("date_phrase"), today) or today,
        )
        state["tool_result"] = {"kind": "mark_attendance", **result}

    elif intent == "view_analytics":
        result = get_attendance_analytics(session, scope="school")
        state["tool_result"] = {"kind": "analytics", **result}

    elif intent == "escalate":
        state = _handle_escalation(state, today)

    else:
        state["tool_result"] = {"kind": "general_chat"}

    return state


def _handle_escalation(state: ConversationState, today: date_cls) -> ConversationState:
    session = state["db"]
    slots = state.get("slots", {})
    outstanding = pending.get(state["session_id"])

    # Step 2: the user said yes to an offer we made. Only now do we write anything.
    if state.get("confirming") and outstanding is not None:
        result = request_escalation(
            session,
            requester_id=outstanding.requester_id,
            requester_role=outstanding.requester_role,
            target_role=outstanding.target_role,
            student_id=outstanding.student_id,
            reason=outstanding.reason,
        )
        if result.get("ok"):
            pending.clear(state["session_id"])
        state["tool_result"] = {
            "kind": "escalation_result",
            "target_name": outstanding.target_name,
            **result,
        }
        state["requires_confirmation"] = False
        return state

    # Step 1: make a concrete offer. Nothing is recorded yet.
    target_role = slots.get("target_role") or "teacher"
    student_id = _subject_student_id(state)
    target = resolve_escalation_target(session, target_role=target_role, student_id=student_id)

    pending.put(
        pending.PendingEscalation(
            session_id=state["session_id"],
            requester_id=state["user_id"],
            requester_role=state["role"],
            target_role=target_role,
            target_name=target["target_name"],
            student_id=student_id,
            reason=(slots.get("reason") or state.get("message", ""))[:500],
        )
    )
    # The brief asks for both routes to be offered by name, so resolve the other
    # one too and let the client show a real choice rather than a single yes/no.
    alternative_role = "management" if target_role == "teacher" else "teacher"
    alternative = resolve_escalation_target(
        session, target_role=alternative_role, student_id=student_id
    )

    state["requires_confirmation"] = True
    state["tool_result"] = {
        "kind": "escalation_offer",
        "target_role": target_role,
        "target_name": target["target_name"],
        "options": [
            {
                "target_role": target_role,
                "target_name": target["target_name"],
                "recommended": True,
            },
            {
                "target_role": alternative_role,
                "target_name": alternative["target_name"],
                "recommended": False,
            },
        ],
    }
    return state


def _subject_student_id(state: ConversationState) -> str | None:
    """Who the escalation is about: the student themselves, or a parent's child."""
    if state["role"] == "student":
        return state["user_id"]
    if state["role"] == "parent":
        resolution = resolve_student(
            state["db"],
            requester_id=state["user_id"],
            requester_role="parent",
            student_name=state.get("slots", {}).get("student_name"),
        )
        if resolution.student:
            return resolution.student.student_id
        if resolution.candidates:
            return resolution.candidates[0].student_id
    return None
