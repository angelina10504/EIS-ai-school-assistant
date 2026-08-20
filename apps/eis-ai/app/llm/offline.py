"""Deterministic offline provider.

Used when GEMINI_API_KEY is unset and by the whole test suite. It keeps the graph,
permissions, tools and escalation flow exercisable with no network and no cost.
Responses are templated rather than generated, so they are noticeably less natural
than Gemini's — this is a development fallback, not the product.
"""
from __future__ import annotations

import json
import re

from app.llm.base import LLMProvider
from app.llm.schema import Classification

_MARK_WORDS = re.compile(
    r"\b(mark|record|set|register|update)\b|\bhaazir\b|\bगैरहाजिर\b|\bउपस्थिति दर्ज\b", re.I
)
_STATUS_WORDS = [
    ("absent", re.compile(r"\babsent\b|\bnot (here|present|in)\b|\bmissing\b|अनुपस्थित|गैरहाज़िर", re.I)),
    ("late", re.compile(r"\blate\b|\btardy\b|देर से|लेट", re.I)),
    ("present", re.compile(r"\bpresent\b|\bhere\b|\bin class\b|उपस्थित|हाज़िर", re.I)),
]
_ROSTER_WORDS = re.compile(
    r"\b(who(?:'s| is| are)?\s+(in|on)\s+my\s+(class|classes|roster)|class list|"
    r"my (students|class list|roster)|roster)\b",
    re.I,
)
_ATTENDANCE_WORDS = re.compile(
    r"\battendance\b|\babsent\b|\bpresent\b|\bdays? (off|missed)\b|\brecords?\b"
    r"|उपस्थिति|हाजिरी|வருகை|హాజరు|હાજરી|ਹਾਜ਼ਰੀ|ಹಾಜರಾತಿ|ഹാജർ|উপস্থিতি|حاضری",
    re.I,
)
_ANALYTICS_WORDS = re.compile(
    r"\b(overall|school[- ]wide|average|aggregate|analytics?|reports?|trends?|statistics|stats|breakdowns?|insights?)\b",
    re.I,
)
_ESCALATE_WORDS = re.compile(
    r"\b(talk|speak|connect|call|contact|complain|complaint|escalate|human|"
    r"not satisfied|unsatisfied|dissatisfied|unhappy|useless|real person)\b"
    r"|बात करनी|शिकायत|पेच",
    re.I,
)
_MANAGEMENT_WORDS = re.compile(
    r"\b(management|principal|head ?master|head ?mistress|school office|admin)\b", re.I
)
_AFFIRM_HEAD = (
    r"(?:yes|yeah|yep|yup|sure|ok(?:ay)?|haan|haa|ji|ji haan|confirm(?:ed)?|please|"
    r"go ahead|do it|proceed|हाँ|हां|जी|சரி|అవును|હા|ਹਾਂ|ಹೌದು|ശരി|হ্যাঁ|جی)"
)
_AFFIRM_TAIL = (
    r"(?:[\s,!.]+(?:please|do it|go ahead|thanks|thank you|now|sure|kindly|"
    r"karo|kar do|kijiye))*"
)
_AFFIRMATIONS = re.compile(rf"^\s*{_AFFIRM_HEAD}{_AFFIRM_TAIL}[\s!.,]*$", re.I)
_DATE_PHRASE = re.compile(
    r"\b(today|yesterday|day before yesterday|this week|last week|this month|last month|"
    r"last \w+day|on \d{1,2}(st|nd|rd|th)? \w+|\d{4}-\d{2}-\d{2}|\d{1,2}/\d{1,2}(/\d{2,4})?)\b",
    re.I,
)
_SCRIPTS = [
    ("hi", re.compile(r"[ऀ-ॿ]")),
    ("bn", re.compile(r"[ঀ-৿]")),
    ("pa", re.compile(r"[਀-੿]")),
    ("gu", re.compile(r"[઀-૿]")),
    ("ta", re.compile(r"[஀-௿]")),
    ("te", re.compile(r"[ఀ-౿]")),
    ("kn", re.compile(r"[ಀ-೿]")),
    ("ml", re.compile(r"[ഀ-ൿ]")),
    ("ur", re.compile(r"[؀-ۿ]")),
]
# Case-insensitive keyword, case-sensitive name — "Mark Divya" is a name, "mark me" is not.
_NAME_AFTER = re.compile(
    r"\b(?i:mark|for|about|is|of)\s+([A-Z][a-z]+(?:\s+[A-Z][a-z]+)?)\b"
)
_SELF_WORDS = re.compile(r"\b(my|mine|i|me|my child|my son|my daughter|our)\b", re.I)


class OfflineProvider(LLMProvider):
    name = "offline"
    is_live = False

    def classify(
        self,
        *,
        message: str,
        role: str,
        history: list[dict],
        today: str,
        roster_hint: list[str] | None = None,
    ) -> Classification:
        text = message.strip()
        out: Classification = {"intent": "general_chat", "is_affirmation": False}

        for code, pattern in _SCRIPTS:
            if pattern.search(text):
                out["detected_language"] = code
                break
        else:
            out["detected_language"] = "en"

        if _AFFIRMATIONS.match(text):
            out["is_affirmation"] = True

        status = next((s for s, p in _STATUS_WORDS if p.search(text)), None)
        looks_like_marking = bool(_MARK_WORDS.search(text)) and status is not None

        if looks_like_marking:
            out["intent"] = "mark_attendance"
            out["status"] = status
        elif _ESCALATE_WORDS.search(text) and not _ATTENDANCE_WORDS.search(text):
            out["intent"] = "escalate"
            out["target_role"] = "management" if _MANAGEMENT_WORDS.search(text) else "teacher"
            out["reason"] = text[:200]
        elif _ANALYTICS_WORDS.search(text) and (
            role == "principal" or not _SELF_WORDS.search(text)
        ):
            out["intent"] = "view_analytics" if role == "principal" else "view_attendance"
        elif _ATTENDANCE_WORDS.search(text) or _ROSTER_WORDS.search(text):
            out["intent"] = "view_attendance"

        date_match = _DATE_PHRASE.search(text)
        if date_match:
            out["date_phrase"] = date_match.group(0)

        # Bare follow-ups ("what about yesterday?") inherit the previous intent.
        if out["intent"] == "general_chat" and date_match and history:
            previous = next(
                (turn.get("intent") for turn in reversed(history) if turn.get("intent")), None
            )
            if previous in ("view_attendance", "view_analytics", "mark_attendance"):
                out["intent"] = previous  # type: ignore[typeddict-item]

        name = _match_roster_name(text, roster_hint)
        if name:
            out["student_name"] = name
        elif out["intent"] in ("view_attendance", "mark_attendance"):
            guess = _NAME_AFTER.search(text)
            if guess and not _SELF_WORDS.match(guess.group(1)):
                out["student_name"] = guess.group(1)
        return out

    def respond(
        self, *, system_prompt: str, history: list[dict], message: str, data_block: str
    ) -> str:
        try:
            data = json.loads(data_block)
        except (ValueError, TypeError):
            data = {}
        return render_offline_reply(data)


def _match_roster_name(text: str, roster: list[str] | None) -> str | None:
    if not roster:
        return None
    lowered = text.lower()
    hits = [
        full
        for full in roster
        if full.lower() in lowered
        or any(len(part) > 2 and re.search(rf"\b{re.escape(part.lower())}\b", lowered)
               for part in full.split())
    ]
    return hits[0] if len(hits) == 1 else None


def render_offline_reply(data: dict) -> str:
    """Templated stand-in for a generated reply. Mirrors what the DATA block says."""
    kind = data.get("kind")

    if kind == "attendance":
        if not data.get("ok"):
            return _attendance_error(data, kind)
        recent = ", ".join(f"{r['date']} {r['status']}" for r in data.get("recent", [])[:3])
        on_date = data.get("on_date")
        if on_date:
            if on_date.get("recorded"):
                return (
                    f"On {on_date['date']}, {data['student_name']} was marked "
                    f"{on_date['status']}."
                )
            return f"There's no attendance recorded for {data['student_name']} on {on_date['date']}."
        return (
            f"{data['student_name']} has {data['percentage']}% attendance over the last "
            f"{data['window_days']} days — {data['present_days']} present, "
            f"{data['absent_days']} absent, {data['late_days']} late. Recent: {recent}."
        )

    if kind == "roster":
        classes = data.get("classes", [])
        if not classes:
            return "You don't have a class assigned yet."
        parts = [
            f"{c['class_name']}: {', '.join(c['students'])}" for c in classes if c["students"]
        ]
        return "Here's your roster — " + "; ".join(parts) + "."

    if kind == "mark_attendance":
        if not data.get("ok"):
            return _attendance_error(data, kind)
        changed = (
            f" (changed from {data['previous_status']})"
            if data.get("previous_status") and data["previous_status"] != data["status"]
            else ""
        )
        return (
            f"Done — {data['student_name']} is marked {data['status']} for "
            f"{data['date']}{changed}."
        )

    if kind == "analytics":
        if not data.get("ok"):
            return "I couldn't pull the school analytics just now."
        today = data.get("today", {})
        trend_note = f" (trend is {data['trend_direction']})" if data.get("trend_direction") else ""
        return (
            f"School-wide attendance is {data['overall_percentage']}% over the last "
            f"{data['window_days']} days across {data['total_students']} students{trend_note}. "
            f"Today {today.get('present', 0)} present, {today.get('absent', 0)} absent. "
            f"Lowest class: {data.get('lowest_class')}."
        )

    if kind == "escalation_offer":
        target = data.get("target_name", "the teacher")
        return f"Of course. I can connect you with {target}. Would you like me to request a call now?"

    if kind == "escalation_result":
        if data.get("ok"):
            return (
                f"Your call request has been submitted to {data.get('target_name')} "
                f"(reference {data.get('ticket_ref')})."
            )
        return (
            "I wasn't able to submit the call request — the school's call service didn't "
            "accept it just now, so nobody has been contacted yet. Shall I try again?"
        )

    if kind == "permission_denied":
        return data.get("reason") or "That isn't something I can do for your role."

    if kind == "security_refusal":
        return data.get("reason", "I can't help with that.")

    if kind == "clarification":
        return data.get("question", "Could you tell me a little more?")

    return data.get("fallback", "I'm here to help with school questions — attendance, records, or reaching a teacher.")


def _attendance_error(data: dict, kind: str = "attendance") -> str:
    error = data.get("error")
    asked = data.get("asked_about")
    if error == "not_permitted":
        if kind == "mark_attendance":
            who = asked or "That student"
            return (
                f"{who} isn't in one of your classes, so I can't record attendance for them."
            )
        return (
            "I can only look up records for the student(s) linked to your account, so I "
            "can't pull that one up."
        )
    if error == "unknown_student":
        return f"I couldn't find a student called {asked}." if asked else "I couldn't find that student."
    if error == "ambiguous":
        names = ", ".join(data.get("candidates", [])[:6])
        return f"Which student did you mean — {names}?"
    if error == "no_visible_students":
        return "There aren't any student records linked to your account yet."
    if error == "invalid_status":
        return "I can record a student as present, absent or late — which one?"
    return "I couldn't retrieve that attendance record."
