"""Offer → explicit confirmation → only then a submitted request (§11)."""
from __future__ import annotations

from sqlalchemy import select

from app.db.models import EscalationRequest
from app.graph import pending, run_turn
from app.mock_services import call_service


def test_offer_does_not_write_anything(db, users, conversation):
    sunita = users["Sunita Verma"]
    before = len(db.scalars(select(EscalationRequest)).all())

    state = run_turn(
        db=db,
        user_id=sunita.id,
        session_id=conversation(sunita),
        message="I am not satisfied. I want to talk to my child's teacher.",
    )
    assert state["intent"] == "escalate"
    assert state["requires_confirmation"] is True
    assert state["tool_result"]["kind"] == "escalation_offer"
    assert state["tool_result"]["target_name"] == "Anita Sharma"
    assert "?" in state["response"]  # it asks, it does not announce
    assert len(db.scalars(select(EscalationRequest)).all()) == before


def test_confirmation_creates_the_request(db, users, conversation):
    sunita = users["Sunita Verma"]
    session_id = conversation(sunita)
    run_turn(db=db, user_id=sunita.id, session_id=session_id, message="I want to talk to a teacher")
    state = run_turn(db=db, user_id=sunita.id, session_id=session_id, message="Yes")

    assert state["tool_result"]["kind"] == "escalation_result"
    assert state["tool_result"]["ok"] is True
    assert state["tool_result"]["ticket_ref"].startswith("TCH-")
    assert "submitted" in state["response"].lower()

    row = db.scalar(
        select(EscalationRequest)
        .where(EscalationRequest.requester_id == sunita.id)
        .order_by(EscalationRequest.created_at.desc())
    )
    assert row.status == "confirmed"
    assert row.target_role == "teacher"


def test_failed_dispatch_never_claims_contact(db, users, conversation):
    call_service.FORCE_FAILURE = True
    sunita = users["Sunita Verma"]
    session_id = conversation(sunita)
    run_turn(db=db, user_id=sunita.id, session_id=session_id, message="I want to talk to a teacher")
    state = run_turn(db=db, user_id=sunita.id, session_id=session_id, message="Yes please")

    assert state["tool_result"]["ok"] is False
    lowered = state["response"].lower()
    assert "wasn't able" in lowered or "not" in lowered
    assert "has been submitted" not in lowered

    row = db.scalar(
        select(EscalationRequest)
        .where(EscalationRequest.requester_id == sunita.id)
        .order_by(EscalationRequest.created_at.desc())
    )
    assert row.status == "pending"  # left for a human to pick up


def test_bare_yes_without_an_offer_does_nothing(db, users, conversation):
    rahul = users["Rahul Verma"]
    before = len(db.scalars(select(EscalationRequest)).all())
    state = run_turn(db=db, user_id=rahul.id, session_id=conversation(rahul), message="Yes")
    assert state["intent"] != "escalate" or state["tool_result"]["kind"] != "escalation_result"
    assert len(db.scalars(select(EscalationRequest)).all()) == before


def test_teacher_escalation_is_denied(db, users, conversation):
    anita = users["Anita Sharma"]
    state = run_turn(
        db=db,
        user_id=anita.id,
        session_id=conversation(anita),
        message="I want to speak to school management about this",
    )
    assert state["permitted"] is False
    assert pending.get(state["session_id"]) is None


def test_student_escalates_to_management(db, users, conversation):
    arjun = users["Arjun Nair"]
    session_id = conversation(arjun)
    state = run_turn(
        db=db,
        user_id=arjun.id,
        session_id=session_id,
        message="I want to contact school management, I'm not happy",
    )
    assert state["tool_result"]["target_role"] == "management"
    assert state["tool_result"]["target_name"] == "Dr. Meera Iyer"

    state = run_turn(db=db, user_id=arjun.id, session_id=session_id, message="yes please")
    assert state["tool_result"]["ticket_ref"].startswith("MGM-")
