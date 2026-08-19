"""The Python matrix and packages/shared-types/permissions.json must agree."""
from __future__ import annotations

import json
from pathlib import Path

from app.auth.permissions import INTENTS, PERMISSION_MATRIX
from app.i18n.languages import LANGUAGES

CONTRACT = json.loads(
    (Path(__file__).resolve().parents[3] / "packages/shared-types/permissions.json").read_text()
)


def test_roles_and_intents_match():
    assert sorted(CONTRACT["roles"]) == sorted(PERMISSION_MATRIX)
    assert sorted(CONTRACT["intents"]) == sorted(INTENTS)


def test_matrix_matches():
    for role, row in CONTRACT["matrix"].items():
        for intent, scope in row.items():
            assert PERMISSION_MATRIX[role][intent].value == scope, f"{role}/{intent}"


def test_languages_match():
    assert CONTRACT["languages"] == list(LANGUAGES)
