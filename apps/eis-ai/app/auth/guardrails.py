"""Input/output guards for the classes of attack listed in the assessment §6.

These are a defence-in-depth layer. They are *not* the authorization boundary —
that is `permissions.check_permission` plus the relationship re-checks inside
each tool. Even if every guard here were bypassed, a student still could not
read another student's attendance.
"""
from __future__ import annotations

import re

INJECTION_PATTERNS: list[tuple[str, re.Pattern[str]]] = [
    (
        "instruction_override",
        re.compile(
            r"\b(ignore|disregard|forget|override|bypass)\b.{0,40}?"
            r"\b(previous|prior|earlier|above|all|your)\b.{0,20}?"
            r"\b(instruction|instructions|prompt|prompts|rule|rules|guardrail|guardrails)\b",
            re.I | re.S,
        ),
    ),
    (
        "system_prompt_extraction",
        re.compile(
            r"\b(show|reveal|print|repeat|output|display|tell me|what (is|are))\b.{0,40}?"
            r"\b(system prompt|system instruction|your prompt|your instruction|"
            r"initial prompt|persona prompt|configuration|configured)s?\b",
            re.I | re.S,
        ),
    ),
    (
        "credential_extraction",
        re.compile(
            # ".env" has no leading word boundary, so it lives outside the \b group.
            r"\.env\b|\b(api[_ -]?key|apikey|secret key|service[_ -]?role|access token|"
            r"jwt[_ -]?secret|password hash|env(ironment)? vars?|credentials?)\b",
            re.I,
        ),
    ),
    (
        "role_claim",
        re.compile(
            r"\b(i am|i'm|as the|acting as|treat me as|pretend (i am|to be)|"
            r"switch me to|log me in as)\b\s+(the\s+)?"
            r"(principal|headmaster|teacher|admin|administrator|developer|system)\b",
            re.I,
        ),
    ),
    (
        "developer_mode",
        re.compile(
            r"\b(developer mode|debug mode|jailbreak|dan mode|no restrictions|"
            r"unrestricted mode|you are now)\b",
            re.I,
        ),
    ),
]

# Anything matching these must never reach the client, whatever the model emits.
_SECRET_SHAPES = [
    re.compile(r"AIza[0-9A-Za-z_\-]{20,}"),            # Google API keys
    re.compile(r"eyJ[A-Za-z0-9_\-]{10,}\.[A-Za-z0-9_\-]{10,}\.[A-Za-z0-9_\-]{10,}"),  # JWTs
    re.compile(r"sb[ps]_[0-9a-zA-Z]{20,}"),            # Supabase keys
    re.compile(r"pbkdf2_sha256\$[^\s]+"),              # our password hashes
    re.compile(r"postgres(ql)?(\+\w+)?://[^\s]+"),     # DB URLs
]

_PROMPT_LEAK_MARKERS = [
    "you are eis ai",
    "system prompt:",
    "system instruction",
    "persona prompt",
    "### rules",
]

REFUSAL_BY_FLAG = {
    "system_prompt_extraction": (
        "I can't share my internal instructions, but I'm happy to help with your "
        "school questions — attendance, records, or connecting you with a teacher."
    ),
    "credential_extraction": (
        "I don't have access to any keys or credentials, and I couldn't share them "
        "if I did. What can I help you with at school?"
    ),
    "instruction_override": (
        "I'll stick to how I normally work here. What would you like to know about "
        "your school records?"
    ),
    "developer_mode": (
        "I only operate in one mode — the regular school assistant one. How can I help?"
    ),
    "role_claim": (
        "I can only act on the role you're signed in with, which I check on the server "
        "rather than in chat. Happy to help within that."
    ),
}


def scan_input(message: str) -> list[str]:
    """Return the names of attack patterns present in the user's message."""
    return [name for name, pattern in INJECTION_PATTERNS if pattern.search(message)]


def refusal_for(flags: list[str]) -> str:
    for flag in flags:
        if flag in REFUSAL_BY_FLAG:
            return REFUSAL_BY_FLAG[flag]
    return "I can't help with that, but I'm here for anything about school."


def sanitize_output(text: str, persona_prompt: str = "") -> str:
    """Last line of defence before a model response reaches the client."""
    cleaned = text
    for shape in _SECRET_SHAPES:
        cleaned = shape.sub("[redacted]", cleaned)

    lowered = cleaned.lower()
    if any(marker in lowered for marker in _PROMPT_LEAK_MARKERS):
        return REFUSAL_BY_FLAG["system_prompt_extraction"]

    # Verbatim regurgitation of the persona prompt (a long distinctive slice of it).
    if persona_prompt:
        for line in persona_prompt.splitlines():
            probe = line.strip()
            if len(probe) > 40 and probe.lower() in lowered:
                return REFUSAL_BY_FLAG["system_prompt_extraction"]
    return cleaned
