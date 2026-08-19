"""The permission matrix — plain Python, no LLM involved.

This module is the single source of truth for "may role R perform intent I?".
It is deliberately data, not prose: no prompt can talk it out of a decision.
"""
from __future__ import annotations

from dataclasses import dataclass
from enum import Enum
from typing import Literal

Role = Literal["student", "parent", "teacher", "principal"]
Intent = Literal[
    "view_attendance", "mark_attendance", "view_analytics", "escalate", "general_chat"
]

INTENTS: tuple[str, ...] = (
    "view_attendance",
    "mark_attendance",
    "view_analytics",
    "escalate",
    "general_chat",
)


class Scope(str, Enum):
    """How wide the role's reach is for a given intent."""

    SELF = "self"                  # student: only their own record
    LINKED_CHILD = "linked_child"  # parent: only children in parent_student_link
    OWN_CLASS = "own_class"        # teacher: only students in a class they teach
    SCHOOL = "school"              # principal: school-wide aggregates only
    ANY = "any"                    # no data scoping needed (chat, escalation)
    NONE = "none"                  # denied


# Implementation Guidelines §6.4
PERMISSION_MATRIX: dict[str, dict[str, Scope]] = {
    "student": {
        "view_attendance": Scope.SELF,
        "mark_attendance": Scope.NONE,
        "view_analytics": Scope.NONE,
        "escalate": Scope.ANY,
        "general_chat": Scope.ANY,
    },
    "parent": {
        "view_attendance": Scope.LINKED_CHILD,
        "mark_attendance": Scope.NONE,
        "view_analytics": Scope.NONE,
        "escalate": Scope.ANY,
        "general_chat": Scope.ANY,
    },
    "teacher": {
        "view_attendance": Scope.OWN_CLASS,
        "mark_attendance": Scope.OWN_CLASS,
        "view_analytics": Scope.NONE,
        "escalate": Scope.NONE,
        "general_chat": Scope.ANY,
    },
    "principal": {
        "view_attendance": Scope.NONE,   # oversight goes through analytics, not raw records
        "mark_attendance": Scope.NONE,
        "view_analytics": Scope.SCHOOL,
        "escalate": Scope.NONE,
        "general_chat": Scope.ANY,
    },
}

DENIAL_REASONS: dict[tuple[str, str], str] = {
    ("student", "mark_attendance"): "Only teachers can mark attendance.",
    ("student", "view_analytics"): "School-wide analytics are available to the principal only.",
    ("parent", "mark_attendance"): "Only teachers can mark attendance.",
    ("parent", "view_analytics"): "School-wide analytics are available to the principal only.",
    ("teacher", "view_analytics"): "School-wide analytics are available to the principal only.",
    ("teacher", "escalate"): "Escalation to a human is offered to students and parents.",
    ("principal", "view_attendance"): (
        "Individual student attendance records are not exposed at the principal level — "
        "school-wide analytics are available instead."
    ),
    ("principal", "mark_attendance"): "Only class teachers can mark attendance.",
    ("principal", "escalate"): "Escalation to a human is offered to students and parents.",
}


@dataclass(frozen=True)
class PermissionDecision:
    allowed: bool
    scope: Scope
    reason: str | None = None


def check_permission(role: str, intent: str) -> PermissionDecision:
    row = PERMISSION_MATRIX.get(role)
    if row is None:
        return PermissionDecision(False, Scope.NONE, f"Unknown role '{role}'.")
    scope = row.get(intent, Scope.NONE)
    if scope is Scope.NONE:
        reason = DENIAL_REASONS.get(
            (role, intent), f"A {role} is not allowed to perform '{intent}'."
        )
        return PermissionDecision(False, Scope.NONE, reason)
    return PermissionDecision(True, scope)
