"""The matrix itself — pure logic, no database, no model."""
from __future__ import annotations

import pytest

from app.auth.permissions import INTENTS, PERMISSION_MATRIX, Scope, check_permission

ROLES = ("student", "parent", "teacher", "principal")

EXPECTED = {
    ("student", "view_attendance"): Scope.SELF,
    ("student", "mark_attendance"): Scope.NONE,
    ("student", "view_analytics"): Scope.NONE,
    ("student", "escalate"): Scope.ANY,
    ("parent", "view_attendance"): Scope.LINKED_CHILD,
    ("parent", "mark_attendance"): Scope.NONE,
    ("parent", "view_analytics"): Scope.NONE,
    ("parent", "escalate"): Scope.ANY,
    ("teacher", "view_attendance"): Scope.OWN_CLASS,
    ("teacher", "mark_attendance"): Scope.OWN_CLASS,
    ("teacher", "view_analytics"): Scope.NONE,
    ("teacher", "escalate"): Scope.NONE,
    ("principal", "view_attendance"): Scope.NONE,
    ("principal", "mark_attendance"): Scope.NONE,
    ("principal", "view_analytics"): Scope.SCHOOL,
    ("principal", "escalate"): Scope.NONE,
}


@pytest.mark.parametrize(("pair", "scope"), EXPECTED.items(), ids=lambda v: str(v))
def test_matrix_matches_spec(pair, scope):
    role, intent = pair
    assert PERMISSION_MATRIX[role][intent] is scope
    assert check_permission(role, intent).allowed is (scope is not Scope.NONE)


def test_every_role_covers_every_intent():
    for role in ROLES:
        assert set(PERMISSION_MATRIX[role]) == set(INTENTS)


def test_denials_always_carry_a_reason():
    for role in ROLES:
        for intent in INTENTS:
            decision = check_permission(role, intent)
            if not decision.allowed:
                assert decision.reason


def test_unknown_role_is_denied():
    assert check_permission("hacker", "view_analytics").allowed is False
