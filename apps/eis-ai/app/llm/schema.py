"""The single classification contract shared by the Gemini and offline classifiers."""
from __future__ import annotations

from typing import Any, Literal, TypedDict

CLASSIFY_FUNCTION_NAME = "classify_intent"


class Classification(TypedDict, total=False):
    intent: Literal[
        "view_attendance", "mark_attendance", "view_analytics", "escalate", "general_chat"
    ]
    student_name: str | None
    date_phrase: str | None
    status: Literal["present", "absent", "late"] | None
    target_role: Literal["teacher", "management"] | None
    reason: str | None
    is_affirmation: bool
    detected_language: str | None


CLASSIFY_FUNCTION_DECLARATION: dict[str, Any] = {
    "name": CLASSIFY_FUNCTION_NAME,
    "description": (
        "Classify the user's latest message in a school-assistant conversation and "
        "extract any slots it mentions. Use the conversation history to resolve "
        "follow-ups such as 'what about yesterday?' — inherit the student and the "
        "intent from the previous turn when the new message only changes the date."
    ),
    "parameters": {
        "type": "OBJECT",
        "properties": {
            "intent": {
                "type": "STRING",
                "enum": [
                    "view_attendance",
                    "mark_attendance",
                    "view_analytics",
                    "escalate",
                    "general_chat",
                ],
                "description": (
                    "view_attendance: reading any individual's attendance record. "
                    "mark_attendance: recording a student as present/absent/late. "
                    "view_analytics: school-wide or class-wide aggregate figures. "
                    "escalate: the user is dissatisfied, or wants a human teacher or "
                    "school management. general_chat: greetings, thanks, small talk, "
                    "anything else."
                ),
            },
            "student_name": {
                "type": "STRING",
                "description": (
                    "The student the message is about, as written, or a roll number. "
                    "Omit when the user means themselves or their own child."
                ),
            },
            "date_phrase": {
                "type": "STRING",
                "description": (
                    "Any date the message refers to, copied verbatim "
                    "('today', 'yesterday', 'last Monday', '12 August')."
                ),
            },
            "status": {
                "type": "STRING",
                "enum": ["present", "absent", "late"],
                "description": "Only for mark_attendance.",
            },
            "target_role": {
                "type": "STRING",
                "enum": ["teacher", "management"],
                "description": "Only for escalate: who the user wants to reach.",
            },
            "reason": {
                "type": "STRING",
                "description": "Only for escalate: a short phrase describing why.",
            },
            "is_affirmation": {
                "type": "BOOLEAN",
                "description": (
                    "True when the message is a bare yes/confirmation of what the "
                    "assistant just offered ('yes', 'please do', 'go ahead', 'haan')."
                ),
            },
            "detected_language": {
                "type": "STRING",
                "description": (
                    "ISO-639-1 code of the language the user wrote in: one of "
                    "en, hi, ta, te, mr, bn, gu, pa, kn, ml, ur."
                ),
            },
        },
        "required": ["intent"],
    },
}
