"""Language handling and the voice helpers that do not need Google credentials."""
from __future__ import annotations

from datetime import date, timedelta

import pytest

from app.graph.dates import resolve_date
from app.graph.nodes.language_detector import detect_script
from app.graph import run_turn
from app.i18n.languages import LANGUAGES, bcp47, get_language
from app.voice.tts import build_ssml, estimate_marks


@pytest.mark.parametrize(
    ("text", "expected"),
    [
        ("मेरी उपस्थिति क्या है?", "hi"),
        ("என் வருகை என்ன?", "ta"),
        ("నా హాజరు ఎంత?", "te"),
        ("મારી હાજરી કેટલી છે?", "gu"),
        ("What is my attendance?", None),
    ],
)
def test_script_detection(text, expected):
    assert detect_script(text) == expected


def test_all_eleven_languages_have_bcp47_codes():
    assert len(LANGUAGES) == 11
    for code, language in LANGUAGES.items():
        assert language.bcp47.endswith("-IN")
        assert bcp47(code) == language.bcp47
        assert language.native_name


def test_unknown_language_falls_back_to_english():
    assert get_language("fr").code == "en"
    assert get_language(None).code == "en"


def test_hindi_message_switches_the_session_language(db, users, conversation):
    rahul = users["Rahul Verma"]
    state = run_turn(
        db=db,
        user_id=rahul.id,
        session_id=conversation(rahul),
        message="मेरी उपस्थिति कितनी है?",
    )
    assert state["language"] == "hi"
    assert state["intent"] == "view_attendance"
    assert state["tool_result"]["ok"] is True


def test_tamil_message_switches_the_session_language(db, users, conversation):
    priya = users["Priya Nair"]
    state = run_turn(
        db=db, user_id=priya.id, session_id=conversation(priya), message="என் வருகை என்ன?"
    )
    assert state["language"] == "ta"
    assert state["intent"] == "view_attendance"


@pytest.mark.parametrize(
    ("phrase", "delta"),
    [("today", 0), ("yesterday", 1), ("day before yesterday", 2), ("3 days ago", 3)],
)
def test_relative_dates(phrase, delta):
    assert resolve_date(phrase) == date.today() - timedelta(days=delta)


def test_absolute_dates():
    assert resolve_date("2026-03-14") == date(2026, 3, 14)
    assert resolve_date(None) is None
    assert resolve_date("sometime soon") is None


def test_last_weekday_is_in_the_past():
    resolved = resolve_date("last Monday")
    assert resolved is not None and resolved < date.today() and resolved.weekday() == 0


def test_ssml_marks_every_word():
    ssml, words = build_ssml("Rahul has 91.2% attendance")
    assert words == ["Rahul", "has", "91.2%", "attendance"]
    assert ssml.count("<mark ") == 4
    assert ssml.startswith("<speak>") and ssml.endswith("</speak>")


def test_ssml_escapes_markup():
    ssml, _ = build_ssml("A & B <tag>")
    assert "&amp;" in ssml and "&lt;tag&gt;" in ssml


def test_estimated_marks_are_monotonic():
    marks = estimate_marks(["one", "two", "three", "four"])
    times = [m.seconds for m in marks]
    assert times == sorted(times)
    assert marks[0].seconds == 0.0
    assert marks[-1].seconds > 0
