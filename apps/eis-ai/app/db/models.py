"""SQLAlchemy models mirroring infra/supabase/schema.sql exactly.

Postgres is the deployment target (Supabase); SQLite is supported for offline
dev, so UUID defaults are generated in Python rather than by gen_random_uuid().
"""
from __future__ import annotations

import uuid
from datetime import date as _date, datetime, timezone

from sqlalchemy import (
    Boolean,
    CheckConstraint,
    Date,
    DateTime,
    ForeignKey,
    String,
    Text,
    UniqueConstraint,
    Uuid,
)
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column, relationship


def _uuid() -> str:
    return str(uuid.uuid4())


def _now() -> datetime:
    return datetime.now(timezone.utc)


class Base(DeclarativeBase):
    pass


# Native uuid on Postgres, CHAR(32) on SQLite — same Python str either way.
UUID_COL = Uuid(as_uuid=False)


class User(Base):
    __tablename__ = "users"
    __table_args__ = (
        CheckConstraint("role in ('student','parent','teacher','principal')", name="users_role_check"),
    )

    id: Mapped[str] = mapped_column(UUID_COL, primary_key=True, default=_uuid)
    role: Mapped[str] = mapped_column(String(20), nullable=False)
    name: Mapped[str] = mapped_column(Text, nullable=False)
    email: Mapped[str | None] = mapped_column(Text, unique=True)
    password_hash: Mapped[str] = mapped_column(Text, nullable=False)
    preferred_language: Mapped[str] = mapped_column(String(8), default="en")
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_now)

    student_profile: Mapped["Student | None"] = relationship(back_populates="user", uselist=False)


class Class(Base):
    __tablename__ = "classes"

    id: Mapped[str] = mapped_column(UUID_COL, primary_key=True, default=_uuid)
    name: Mapped[str] = mapped_column(Text, nullable=False)
    teacher_id: Mapped[str | None] = mapped_column(UUID_COL, ForeignKey("users.id"))

    teacher: Mapped[User | None] = relationship()
    students: Mapped[list["Student"]] = relationship(back_populates="klass")


class Student(Base):
    __tablename__ = "students"

    id: Mapped[str] = mapped_column(UUID_COL, ForeignKey("users.id"), primary_key=True)
    roll_number: Mapped[str] = mapped_column(Text, nullable=False)
    class_id: Mapped[str | None] = mapped_column(UUID_COL, ForeignKey("classes.id"))

    user: Mapped[User] = relationship(back_populates="student_profile")
    klass: Mapped[Class | None] = relationship(back_populates="students")


class ParentStudentLink(Base):
    __tablename__ = "parent_student_link"

    parent_id: Mapped[str] = mapped_column(UUID_COL, ForeignKey("users.id"), primary_key=True)
    student_id: Mapped[str] = mapped_column(UUID_COL, ForeignKey("students.id"), primary_key=True)


class Attendance(Base):
    __tablename__ = "attendance"
    __table_args__ = (
        UniqueConstraint("student_id", "date", name="attendance_student_id_date_key"),
        CheckConstraint("status in ('present','absent','late')", name="attendance_status_check"),
    )

    id: Mapped[str] = mapped_column(UUID_COL, primary_key=True, default=_uuid)
    student_id: Mapped[str] = mapped_column(UUID_COL, ForeignKey("students.id"))
    date: Mapped[_date] = mapped_column(Date, nullable=False)
    status: Mapped[str] = mapped_column(String(10), nullable=False)
    marked_by: Mapped[str | None] = mapped_column(UUID_COL, ForeignKey("users.id"))
    marked_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_now)


class EscalationRequest(Base):
    __tablename__ = "escalation_requests"
    __table_args__ = (
        CheckConstraint("target_role in ('teacher','management')", name="escalation_target_check"),
        CheckConstraint(
            "status in ('pending','confirmed','completed')", name="escalation_status_check"
        ),
    )

    id: Mapped[str] = mapped_column(UUID_COL, primary_key=True, default=_uuid)
    requester_id: Mapped[str] = mapped_column(UUID_COL, ForeignKey("users.id"))
    target_role: Mapped[str] = mapped_column(String(16), nullable=False)
    student_id: Mapped[str | None] = mapped_column(UUID_COL, ForeignKey("students.id"))
    reason: Mapped[str | None] = mapped_column(Text)
    status: Mapped[str] = mapped_column(String(16), nullable=False, default="pending")
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_now)


class ConversationSession(Base):
    __tablename__ = "conversation_sessions"

    id: Mapped[str] = mapped_column(UUID_COL, primary_key=True, default=_uuid)
    user_id: Mapped[str] = mapped_column(UUID_COL, ForeignKey("users.id"))
    language: Mapped[str] = mapped_column(String(8), default="en")
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_now)


class ConversationMessage(Base):
    __tablename__ = "conversation_messages"
    __table_args__ = (
        CheckConstraint("sender in ('user','assistant')", name="messages_sender_check"),
    )

    id: Mapped[str] = mapped_column(UUID_COL, primary_key=True, default=_uuid)
    session_id: Mapped[str] = mapped_column(UUID_COL, ForeignKey("conversation_sessions.id"))
    sender: Mapped[str] = mapped_column(String(10), nullable=False)
    content: Mapped[str] = mapped_column(Text, nullable=False)
    intent: Mapped[str | None] = mapped_column(Text)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_now)


class AuditLog(Base):
    __tablename__ = "audit_log"

    id: Mapped[str] = mapped_column(UUID_COL, primary_key=True, default=_uuid)
    user_id: Mapped[str | None] = mapped_column(UUID_COL, ForeignKey("users.id"))
    action: Mapped[str] = mapped_column(Text, nullable=False)
    resource: Mapped[str | None] = mapped_column(Text)
    allowed: Mapped[bool] = mapped_column(Boolean, nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_now)
