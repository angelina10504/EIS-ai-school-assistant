"""Attendance tools. Narrow and intent-named — not generic CRUD."""
from __future__ import annotations

from datetime import date as date_cls, timedelta

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.db.models import Attendance, Class, Student
from app.tools.scope import resolve_student

VALID_STATUSES = ("present", "absent", "late")


def _percentage(records: list[Attendance]) -> float:
    if not records:
        return 0.0
    counted = sum(1.0 if r.status == "present" else 0.5 if r.status == "late" else 0.0 for r in records)
    return round(counted / len(records) * 100, 1)


def get_attendance(
    session: Session,
    *,
    requester_id: str,
    requester_role: str,
    student_id: str | None = None,
    student_name: str | None = None,
    on_date: date_cls | None = None,
    days: int = 90,
) -> dict:
    """Read attendance for one student, after re-checking the relationship server-side."""
    resolution = resolve_student(
        session,
        requester_id=requester_id,
        requester_role=requester_role,
        student_name=student_name,
        student_id=student_id,
    )
    if resolution.student is None:
        return {
            "ok": False,
            "error": resolution.error or "unknown_student",
            "candidates": [c.name for c in resolution.candidates or []],
            "asked_about": student_name,
        }

    view = resolution.student
    since = date_cls.today() - timedelta(days=days)
    records = list(
        session.scalars(
            select(Attendance)
            .where(Attendance.student_id == view.student_id, Attendance.date >= since)
            .order_by(Attendance.date.desc())
        ).all()
    )

    result = {
        "ok": True,
        "student_name": view.name,
        "roll_number": view.roll_number,
        "class_name": view.class_name,
        "window_days": days,
        "percentage": _percentage(records),
        "present_days": sum(1 for r in records if r.status == "present"),
        "absent_days": sum(1 for r in records if r.status == "absent"),
        "late_days": sum(1 for r in records if r.status == "late"),
        "total_days": len(records),
        "recent": [
            {"date": r.date.isoformat(), "status": r.status} for r in records[:7]
        ],
    }

    if on_date is not None:
        match = next((r for r in records if r.date == on_date), None)
        result["on_date"] = {
            "date": on_date.isoformat(),
            "status": match.status if match else None,
            "recorded": match is not None,
        }
    return result


def mark_attendance(
    session: Session,
    *,
    teacher_id: str,
    status: str,
    on_date: date_cls | None = None,
    student_id: str | None = None,
    student_name: str | None = None,
) -> dict:
    """Write one attendance row. Only ever reachable for a teacher's own class."""
    if status not in VALID_STATUSES:
        return {"ok": False, "error": "invalid_status", "valid": list(VALID_STATUSES)}

    resolution = resolve_student(
        session,
        requester_id=teacher_id,
        requester_role="teacher",
        student_name=student_name,
        student_id=student_id,
    )
    if resolution.student is None:
        return {
            "ok": False,
            "error": resolution.error or "unknown_student",
            "candidates": [c.name for c in resolution.candidates or []],
            "asked_about": student_name,
        }

    view = resolution.student
    when = on_date or date_cls.today()

    existing = session.scalar(
        select(Attendance).where(
            Attendance.student_id == view.student_id, Attendance.date == when
        )
    )
    previous = existing.status if existing else None
    if existing:
        existing.status = status
        existing.marked_by = teacher_id
    else:
        session.add(
            Attendance(
                student_id=view.student_id, date=when, status=status, marked_by=teacher_id
            )
        )
    session.flush()

    return {
        "ok": True,
        "student_name": view.name,
        "roll_number": view.roll_number,
        "class_name": view.class_name,
        "date": when.isoformat(),
        "status": status,
        "previous_status": previous,
        "updated_existing": existing is not None,
    }


def list_class_roster(session: Session, *, teacher_id: str) -> dict:
    """Supports 'who's in my class?' without exposing anyone else's students."""
    classes = list(session.scalars(select(Class).where(Class.teacher_id == teacher_id)).all())
    return {
        "ok": True,
        "classes": [
            {
                "class_name": c.name,
                "students": sorted(
                    s.user.name
                    for s in session.scalars(
                        select(Student).where(Student.class_id == c.id)
                    ).all()
                ),
            }
            for c in classes
        ],
    }
