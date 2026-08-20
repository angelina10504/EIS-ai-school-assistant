"""Mock school-ERP attendance API.

These are the same tools the graph calls, exposed over HTTP. They run the identical
permission gate, so a client that skips the chat interface gains nothing.
"""
from __future__ import annotations

from datetime import date as date_cls

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.api.deps import CurrentUser, current_user, get_db
from app.api.schemas import MarkAttendanceRequest
from app.auth.audit import log_permission_check
from app.auth.permissions import check_permission
from app.tools.attendance_tools import get_attendance, list_class_roster, mark_attendance

router = APIRouter(prefix="/api/attendance", tags=["attendance"])


def _gate(db: Session, user: CurrentUser, intent: str, resource: str) -> None:
    decision = check_permission(user.role, intent)
    log_permission_check(
        db, user_id=user.id, action=f"rest:{intent}", resource=resource, allowed=decision.allowed
    )
    if not decision.allowed:
        raise HTTPException(status.HTTP_403_FORBIDDEN, decision.reason or "Not permitted")


@router.get("/roster")
def roster(user: CurrentUser = Depends(current_user), db: Session = Depends(get_db)) -> dict:
    _gate(db, user, "view_attendance", "roster")
    if user.role != "teacher":
        raise HTTPException(status.HTTP_403_FORBIDDEN, "Only a class teacher has a roster")
    return list_class_roster(db, teacher_id=user.id)


@router.get("/{student_id}")
def read_attendance(
    student_id: str,
    user: CurrentUser = Depends(current_user),
    db: Session = Depends(get_db),
) -> dict:
    _gate(db, user, "view_attendance", f"student:{student_id}")
    result = get_attendance(
        db, requester_id=user.id, requester_role=user.role, student_id=student_id
    )
    if not result.get("ok"):
        raise HTTPException(status.HTTP_403_FORBIDDEN, "No access to that student's record")
    return result


@router.post("/mark")
def mark(
    payload: MarkAttendanceRequest,
    user: CurrentUser = Depends(current_user),
    db: Session = Depends(get_db),
) -> dict:
    _gate(db, user, "mark_attendance", f"student:{payload.student_id or payload.student_name}")
    on_date = date_cls.fromisoformat(payload.date) if payload.date else None
    result = mark_attendance(
        db,
        teacher_id=user.id,
        status=payload.status,
        student_id=payload.student_id,
        student_name=payload.student_name,
        on_date=on_date,
    )
    if not result.get("ok"):
        raise HTTPException(status.HTTP_400_BAD_REQUEST, result.get("error", "Could not mark"))
    return result
