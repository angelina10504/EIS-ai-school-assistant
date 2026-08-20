"""Node 2 — settle on the language for this turn.

The stored preference wins; a message clearly written in another supported script
switches the session over (and is persisted by the chat layer).
"""
from __future__ import annotations

from app.graph.state import ConversationState
from app.i18n.languages import LANGUAGES, get_language

_SCRIPT_HINT = {
    "hi": range(0x0900, 0x0980),
    "bn": range(0x0980, 0x0A00),
    "pa": range(0x0A00, 0x0A80),
    "gu": range(0x0A80, 0x0B00),
    "ta": range(0x0B80, 0x0C00),
    "te": range(0x0C00, 0x0C80),
    "kn": range(0x0C80, 0x0D00),
    "ml": range(0x0D00, 0x0D80),
    "ur": range(0x0600, 0x0700),
}


def detect_script(text: str) -> str | None:
    counts: dict[str, int] = {}
    for char in text:
        point = ord(char)
        for code, span in _SCRIPT_HINT.items():
            if point in span:
                counts[code] = counts.get(code, 0) + 1
    if not counts:
        return None
    best = max(counts, key=counts.get)  # type: ignore[arg-type]
    return best if counts[best] >= 2 else None


def language_detector(state: ConversationState) -> ConversationState:
    state["trace"].append("language_detector")
    detected = detect_script(state.get("message", ""))
    if detected and detected in LANGUAGES:
        state["language"] = detected
    else:
        state["language"] = get_language(state.get("language")).code
    return state
