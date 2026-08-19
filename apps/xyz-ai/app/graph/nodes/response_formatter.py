"""Node 8 — persona + tool_result + history → one natural reply, then sanitised.

Two classes of reply never get composed freely by the model:

* security refusals, which are emitted straight from code;
* the escalation offer and a failed escalation, where the exact meaning is a hard
  requirement of the brief. For those the model is asked to *translate* a fixed
  sentence rather than write its own, and the result is validated before use.
"""
from __future__ import annotations

import json
import logging
import re

from app.auth.guardrails import refusal_for, sanitize_output
from app.graph.state import ConversationState
from app.i18n.languages import english_name
from app.llm import get_llm
from app.llm.offline import render_offline_reply

logger = logging.getLogger(__name__)

# Per-kind grounding notes. These sit next to the data so the model cannot mistake
# "I offered" for "I did it", or answer about the wrong day.
_INSTRUCTIONS = {
    "attendance": (
        "Report these exact figures. If on_date is present, the user asked about that "
        "specific date — answer about that date and no other, and say plainly when "
        "recorded is false."
    ),
    "mark_attendance": "Confirm exactly what was recorded, including the date.",
    "analytics": "Lead with overall_percentage. Never name an individual student.",
    "roster": "List the students in these classes and nothing else.",
    "clarification": "Ask this question and wait. Do not guess an answer.",
    "permission_denied": "Explain this limit warmly in one sentence. Do not offer a workaround.",
    "general_chat": "No data was retrieved. Chat naturally and never state a figure.",
}

# kind -> (canonical sentence template, must the reply be a question?)
_PINNED = {
    "escalation_offer": (
        "Of course. I can connect you with {target_name}. Would you like me to request "
        "a call now?",
        True,
    ),
    "escalation_failed": (
        "I could not submit the call request — the school's call service did not accept "
        "it, so nobody has been contacted yet. Shall I try again?",
        True,
    ),
}


def response_formatter(state: ConversationState) -> ConversationState:
    state["trace"].append("response_formatter")
    tool_result = state.get("tool_result") or {"kind": "general_chat"}
    kind = tool_result.get("kind")

    # A detected extraction attempt is answered from code, never from the model —
    # there is no path where the model gets a chance to comply.
    if kind == "security_refusal":
        state["response"] = tool_result.get("reason") or refusal_for(state.get("security_flags", []))
        return state

    payload = _public_fields(tool_result)
    pin_key = kind
    if kind == "escalation_result" and not tool_result.get("ok"):
        pin_key = "escalation_failed"

    llm = get_llm()
    language = state.get("language", "en")

    if pin_key in _PINNED:
        template, must_ask = _PINNED[pin_key]
        required = template.format(target_name=payload.get("target_name", "the teacher"))
        text = _pinned_reply(llm, state, required, language, must_ask)
    else:
        payload["instruction"] = _INSTRUCTIONS.get(kind or "general_chat", "")
        text = _free_reply(llm, state, payload)

    if not text.strip() or _invents_a_percentage(text, payload):
        text = render_offline_reply(payload)

    state["response"] = sanitize_output(text, state.get("persona_prompt", ""))
    return state


def _free_reply(llm, state: ConversationState, payload: dict) -> str:
    try:
        return llm.respond(
            system_prompt=state["persona_prompt"],
            history=state["history"],
            message=state["message"],
            data_block=json.dumps(payload, ensure_ascii=False, indent=2),
        )
    except Exception as exc:  # pragma: no cover - network/quota failures
        # Never silent: a quota or auth failure looks identical to a bad reply
        # from the outside, and that is exactly what makes it hard to debug.
        detail = str(exc)
        if "RESOURCE_EXHAUSTED" in detail or "429" in detail:
            logger.error(
                "Gemini quota exhausted — falling back to the templated reply. %s",
                detail.split("Please retry")[0][:300],
            )
        else:
            logger.exception("Gemini generation failed; falling back to the templated reply")
        return ""


def _pinned_reply(llm, state: ConversationState, required: str, language: str, must_ask: bool) -> str:
    """Let the model carry the language and the warmth, but not the meaning."""
    if language == "en" and not llm.is_live:
        return required

    payload = {
        "kind": "pinned_message",
        "required_message": required,
        "instruction": (
            f"Say exactly this in {english_name(language)}, in that language's own script. "
            "Keep the meaning identical: you have NOT contacted anyone and nothing has "
            "been submitted — you are asking for permission. Do not add promises, do not "
            "add extra sentences, and keep the question mark."
        ),
    }
    text = _free_reply(llm, state, payload).strip()

    # If the model editorialised its way out of asking, use the fixed sentence.
    if not text or (must_ask and "?" not in text and "？" not in text and "؟" not in text):
        return required
    return text


# A percentage the model made up is the worst possible failure here — a parent acts
# on that number. Anything it states must appear in what the tool actually returned.
_PERCENT_RE = re.compile(r"(\d{1,3}(?:\.\d+)?)\s*(?:%|percent|प्रतिशत|சதவீதம்|శాతం)", re.I)


def _invents_a_percentage(text: str, payload: dict) -> bool:
    stated = {float(m) for m in _PERCENT_RE.findall(text)}
    if not stated:
        return False

    allowed: set[float] = set()
    for key in ("percentage", "overall_percentage", "at_risk_percentage"):
        if isinstance(payload.get(key), (int, float)):
            allowed.add(float(payload[key]))

    # trend_change is a signed delta ("down 1.2%"). The regex captures digits only,
    # so the magnitude is what a grounded reply will quote.
    if isinstance(payload.get("trend_change"), (int, float)):
        allowed.add(abs(float(payload["trend_change"])))

    for row in payload.get("by_class") or []:
        if isinstance(row, dict) and isinstance(row.get("percentage"), (int, float)):
            allowed.add(float(row["percentage"]))

    for row in payload.get("recent_daily_trend") or []:
        if isinstance(row, dict) and isinstance(row.get("percentage"), (int, float)):
            allowed.add(float(row["percentage"]))

    for row in payload.get("weekday_breakdown") or []:
        if isinstance(row, dict) and isinstance(row.get("percentage"), (int, float)):
            allowed.add(float(row["percentage"]))

    today_info = payload.get("today")
    if isinstance(today_info, dict) and isinstance(today_info.get("percentage"), (int, float)):
        allowed.add(float(today_info["percentage"]))

    if not allowed:
        logger.warning("Model stated %s%% with no percentage in the tool result", stated)
        return True

    for value in stated:
        if not any(abs(value - ok) < 0.15 for ok in allowed):
            logger.error(
                "Model stated %s%% but the tool returned %s — discarding the reply",
                value, sorted(allowed),
            )
            return True
    return False


_INTERNAL_KEYS = {"escalation_id", "flags"}


def _public_fields(tool_result: dict) -> dict:
    """Strip internals before the payload reaches the model or the client."""
    return {k: v for k, v in tool_result.items() if k not in _INTERNAL_KEYS}
