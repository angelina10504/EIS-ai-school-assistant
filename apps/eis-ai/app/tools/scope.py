"""Relationship checks. Every tool calls into here before touching a record.

The LLM supplies *names*, never IDs it invented — and even when it supplies an ID,
these functions re-derive from the requester's own row what that requester is
allowed to see. An injected instruction cannot widen this.
"""
from __future__ import annotations

from dataclasses import dataclass

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.db.models import Class, ParentStudentLink, Student, User


@dataclass(frozen=True)
class StudentView:
    student_id: str
    name: str
    roll_number: str
    class_id: str | None
    class_name: str | None


def _to_view(student: Student) -> StudentView:
    return StudentView(
        student_id=student.id,
        name=student.user.name,
        roll_number=student.roll_number,
        class_id=student.class_id,
        class_name=student.klass.name if student.klass else None,
    )


def visible_students(session: Session, requester_id: str, requester_role: str) -> list[StudentView]:
    """Every student this requester is permitted to see, derived from the database."""
    if requester_role == "student":
        student = session.get(Student, requester_id)
        return [_to_view(student)] if student else []

    if requester_role == "parent":
        ids = session.scalars(
            select(ParentStudentLink.student_id).where(
                ParentStudentLink.parent_id == requester_id
            )
        ).all()
        if not ids:
            return []
        students = session.scalars(select(Student).where(Student.id.in_(ids))).all()
        return [_to_view(s) for s in students]

    if requester_role == "teacher":
        class_ids = session.scalars(
            select(Class.id).where(Class.teacher_id == requester_id)
        ).all()
        if not class_ids:
            return []
        students = session.scalars(
            select(Student).where(Student.class_id.in_(class_ids))
        ).all()
        return [_to_view(s) for s in students]

    # Principals reach student data only through aggregate analytics.
    return []


def can_access_student(
    session: Session, requester_id: str, requester_role: str, student_id: str
) -> bool:
    return any(v.student_id == student_id for v in visible_students(session, requester_id, requester_role))


@dataclass(frozen=True)
class Resolution:
    student: StudentView | None = None
    candidates: list[StudentView] | None = None
    error: str | None = None


def resolve_student(
    session: Session,
    *,
    requester_id: str,
    requester_role: str,
    student_name: str | None = None,
    student_id: str | None = None,
) -> Resolution:
    """Turn whatever the model extracted into exactly one student the requester may see."""
    allowed = visible_students(session, requester_id, requester_role)
    if not allowed:
        return Resolution(error="no_visible_students")

    if student_id:
        match = next((s for s in allowed if s.student_id == student_id), None)
        return Resolution(student=match) if match else Resolution(error="not_permitted")

    if not student_name:
        if len(allowed) == 1:
            return Resolution(student=allowed[0])
        return Resolution(candidates=allowed, error="ambiguous")

    needle = student_name.strip().lower()

    # A roll number is as good as a name when a teacher rattles one off.
    by_roll = [s for s in allowed if s.roll_number.lower() == needle]
    if len(by_roll) == 1:
        return Resolution(student=by_roll[0])

    exact = [s for s in allowed if s.name.lower() == needle]
    if len(exact) == 1:
        return Resolution(student=exact[0])

    partial = [
        s
        for s in allowed
        if needle in s.name.lower() or needle in {p.lower() for p in s.name.split()}
    ]
    if len(partial) == 1:
        return Resolution(student=partial[0])
    if len(partial) > 1:
        return Resolution(candidates=partial, error="ambiguous")

    # The name is real elsewhere in the school but not in this requester's scope —
    # answer the same way as a name that does not exist, so the refusal leaks nothing.
    exists = session.scalar(
        select(User).join(Student, Student.id == User.id).where(User.name.ilike(f"%{student_name}%"))
    )
    return Resolution(error="not_permitted" if exists else "unknown_student")
