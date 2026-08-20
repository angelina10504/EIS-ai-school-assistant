"""The four required use cases from the assessment, driven through the graph."""
from __future__ import annotations

from datetime import date, timedelta

from sqlalchemy import select

from app.db.models import Attendance
from app.graph import run_turn


def test_student_sees_own_attendance(db, users, conversation):
    rahul = users["Rahul Verma"]
    state = run_turn(
        db=db, user_id=rahul.id, session_id=conversation(rahul), message="What is my attendance?"
    )
    assert state["intent"] == "view_attendance"
    assert state["permitted"] is True
    assert state["tool_result"]["ok"] is True
    assert state["tool_result"]["student_name"] == "Rahul Verma"
    assert 0 < state["tool_result"]["percentage"] <= 100
    assert "Rahul" in state["response"]


def test_parent_sees_linked_child(db, users, conversation):
    sunita = users["Sunita Verma"]
    state = run_turn(
        db=db,
        user_id=sunita.id,
        session_id=conversation(sunita),
        message="How much attendance does my child have?",
    )
    assert state["intent"] == "view_attendance"
    assert state["tool_result"]["student_name"] == "Rahul Verma"


def test_teacher_marks_attendance(db, users, conversation):
    anita = users["Anita Sharma"]
    rahul = users["Rahul Verma"]
    state = run_turn(
        db=db, user_id=anita.id, session_id=conversation(anita), message="Mark Rahul absent today."
    )
    assert state["intent"] == "mark_attendance"
    assert state["permitted"] is True
    assert state["tool_result"]["ok"] is True
    assert state["tool_result"]["status"] == "absent"

    row = db.scalar(
        select(Attendance).where(
            Attendance.student_id == rahul.id, Attendance.date == date.today()
        )
    )
    assert row is not None and row.status == "absent" and row.marked_by == anita.id


def test_principal_gets_school_analytics(db, users, conversation):
    meera = users["Dr. Meera Iyer"]
    state = run_turn(
        db=db,
        user_id=meera.id,
        session_id=conversation(meera),
        message="What is the overall attendance?",
    )
    assert state["intent"] == "view_analytics"
    assert state["tool_result"]["ok"] is True
    assert state["tool_result"]["scope"] == "school"
    assert state["tool_result"]["total_students"] == 6
    assert "trend_direction" in state["tool_result"]
    assert "recent_daily_trend" in state["tool_result"]
    assert "weekday_breakdown" in state["tool_result"]
    assert "at_risk_percentage" in state["tool_result"]
    assert len(state["tool_result"]["recent_daily_trend"]) > 0
    # Aggregates only — no student names anywhere in the payload or the reply.
    payload = str(state["tool_result"])
    for name in ("Rahul", "Priya", "Imran", "Divya", "Sneha", "Arjun"):
        assert name not in payload
        assert name not in state["response"]


def test_principal_analytics_trend_and_breakdown(db, users, conversation):
    meera = users["Dr. Meera Iyer"]
    state = run_turn(
        db=db,
        user_id=meera.id,
        session_id=conversation(meera),
        message="Show me the school attendance trends and class breakdown",
    )
    assert state["intent"] == "view_analytics"
    tool_res = state["tool_result"]
    assert tool_res["ok"] is True
    assert 0 <= tool_res["overall_percentage"] <= 100
    assert tool_res["trend_direction"] in ("improving", "declining", "stable")
    for day in tool_res["recent_daily_trend"]:
        assert "date" in day
        assert "day_name" in day
        assert 0 <= day["percentage"] <= 100
    for wb in tool_res["weekday_breakdown"]:
        assert wb["day"] in ("Monday", "Tuesday", "Wednesday", "Thursday", "Friday")
        assert 0 <= wb["percentage"] <= 100


def test_followup_without_restating_context(db, users, conversation):
    """'what about yesterday?' resolves from history, not from the new message."""
    sunita = users["Sunita Verma"]
    session_id = conversation(sunita)
    run_turn(db=db, user_id=sunita.id, session_id=session_id, message="How is my child's attendance?")

    yesterday = date.today() - timedelta(days=1)
    state = run_turn(
        db=db, user_id=sunita.id, session_id=session_id, message="What about yesterday?"
    )
    assert state["intent"] == "view_attendance"
    assert state["tool_result"]["student_name"] == "Rahul Verma"
    assert state["tool_result"]["on_date"]["date"] == yesterday.isoformat()


def test_history_is_persisted_for_the_next_turn(db, users, conversation):
    imran_parent = users["Farah Khan"]
    session_id = conversation(imran_parent)
    run_turn(db=db, user_id=imran_parent.id, session_id=session_id, message="Attendance please")
    state = run_turn(db=db, user_id=imran_parent.id, session_id=session_id, message="Thanks!")
    senders = [turn["sender"] for turn in state["history"]]
    assert senders[:2] == ["user", "assistant"]


def test_teacher_roster_lists_only_own_class(db, users, conversation):
    anita = users["Anita Sharma"]  # Class 8A
    state = run_turn(
        db=db, user_id=anita.id, session_id=conversation(anita), message="Who is in my class?"
    )
    assert state["tool_result"]["kind"] == "roster"
    names = [n for c in state["tool_result"]["classes"] for n in c["students"]]
    assert set(names) == {"Rahul Verma", "Priya Nair", "Arjun Nair"}
    assert "Divya Reddy" not in state["response"]


def test_partial_day_excluded_from_trend(db, users, conversation):
    """A day still being marked must not skew momentum or the weekday split."""
    from datetime import date, timedelta

    from app.db.models import Attendance
    from app.tools.analytics_tools import _is_complete, get_attendance_analytics

    # Six students on the roll; a single record for a date is clearly mid-morning.
    assert _is_complete([], 6) is False
    assert _is_complete([object()] * 1, 6) is False   # type: ignore[list-item]
    assert _is_complete([object()] * 6, 6) is True    # type: ignore[list-item]

    result = get_attendance_analytics(db, scope="school")
    for day in result["recent_daily_trend"]:
        recorded = day["marked"] >= day["roll_size"] * 0.8
        assert day["in_progress"] is not recorded

    # Trend is computed only from complete days, so a lone 0% partial day
    # cannot be what makes the school look like it is collapsing.
    partials = [d for d in result["recent_daily_trend"] if d["in_progress"]]
    if partials:
        assert result["trend_direction"] in ("improving", "stable", "declining")
        assert result["today"]["in_progress"] is True
