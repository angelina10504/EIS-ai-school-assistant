"""Escalation to a real human. Two-step by construction: offer, then confirm."""
from __future__ import annotations

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.db.models import Class, EscalationRequest, Student, User
from app.mock_services.call_service import dispatch_call_request
from app.tools.scope import resolve_student


def resolve_escalation_target(
    session: Session, *, target_role: str, student_id: str | None
) -> dict:
    """Who the request would actually go to — used to make the offer concrete."""
    if target_role == "management":
        principal = session.scalar(select(User).where(User.role == "principal"))
        return {
            "target_role": "management",
            "target_name": principal.name if principal else "School Management",
            "target_id": principal.id if principal else None,
        }

    teacher = None
    if student_id:
        student = session.get(Student, student_id)
        if student and student.class_id:
            klass = session.get(Class, student.class_id)
            if klass and klass.teacher_id:
                teacher = session.get(User, klass.teacher_id)
    return {
        "target_role": "teacher",
        "target_name": teacher.name if teacher else "the class teacher",
        "target_id": teacher.id if teacher else None,
    }


def request_escalation(
    session: Session,
    *,
    requester_id: str,
    requester_role: str,
    target_role: str,
    student_id: str | None,
    reason: str | None,
) -> dict:
    """Create the escalation row and fire the mock call service.

    Returns ok=False when the mock service fails — the caller must not claim
    anyone was contacted in that case.
    """
    if target_role not in ("teacher", "management"):
        return {"ok": False, "error": "invalid_target_role"}

    # A parent escalating "about my child" must still only reference their own child.
    if student_id is not None:
        resolution = resolve_student(
            session,
            requester_id=requester_id,
            requester_role=requester_role,
            student_id=student_id,
        )
        if resolution.student is None:
            return {"ok": False, "error": "not_permitted"}

    record = EscalationRequest(
        requester_id=requester_id,
        target_role=target_role,
        student_id=student_id,
        reason=reason,
        status="pending",
    )
    session.add(record)
    session.flush()

    target = resolve_escalation_target(session, target_role=target_role, student_id=student_id)
    dispatch = dispatch_call_request(
        target_role=target_role, target_name=target["target_name"], reference=record.id
    )

    if not dispatch.ok:
        # Row stays 'pending' so a human can pick it up; the user is told plainly.
        return {
            "ok": False,
            "error": dispatch.error,
            "escalation_id": record.id,
            "target_name": target["target_name"],
        }

    record.status = "confirmed"
    session.flush()
    return {
        "ok": True,
        "escalation_id": record.id,
        "ticket_ref": dispatch.ticket_ref,
        "target_role": target_role,
        "target_name": target["target_name"],
        "status": record.status,
    }
