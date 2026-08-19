"""Node 4 — Gemini function call that classifies intent and pulls out slots.

Also runs the injection scanner. A flagged message is still classified and still
goes through the permission gate, so the attempt lands in audit_log.
"""
from __future__ import annotations

import logging
from datetime import date

from app.auth.guardrails import scan_input
from app.graph import pending
from app.graph.state import ConversationState
from app.i18n.languages import LANGUAGES
from app.llm import get_llm
from app.tools.scope import visible_students

logger = logging.getLogger(__name__)


def intent_classifier(state: ConversationState) -> ConversationState:
    state["trace"].append("intent_classifier")
    message = state.get("message", "")

    state["security_flags"] = scan_input(message)

    roster = [v.name for v in visible_students(state["db"], state["user_id"], state["role"])]
    llm = get_llm()
    try:
        result = llm.classify(
            message=message,
            role=state["role"],
            history=state["history"],
            today=state.get("today") or date.today().isoformat(),
            roster_hint=roster or None,
        )
    except Exception as exc:  # pragma: no cover - network/quota failures
        logger.warning("Gemini classification failed (%s); using the offline classifier", exc.__class__.__name__)
        from app.llm.offline import OfflineProvider

        result = OfflineProvider().classify(
            message=message,
            role=state["role"],
            history=state["history"],
            today=state.get("today") or date.today().isoformat(),
            roster_hint=roster or None,
        )

    # The classifier sees the whole message, so it beats script detection at telling
    # English from romanised Hindi — and it stops a session sticking in one language.
    detected = (result.get("detected_language") or "").split("-")[0].lower()
    if detected in LANGUAGES:
        state["language"] = detected

    intent = result.get("intent") or "general_chat"
    slots = {
        "student_name": result.get("student_name"),
        "date_phrase": result.get("date_phrase"),
        "status": result.get("status"),
        "target_role": result.get("target_role"),
        "reason": result.get("reason"),
    }

    # A bare "yes" only means something when an offer is actually outstanding.
    outstanding = pending.get(state["session_id"])
    if result.get("is_affirmation") and outstanding is not None:
        intent = "escalate"
        state["confirming"] = True

    state["intent"] = intent
    state["slots"] = slots
    return state
