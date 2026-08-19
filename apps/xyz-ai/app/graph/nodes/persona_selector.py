"""Node 6 — build the role's system prompt, localized to the session language."""
from __future__ import annotations

from sqlalchemy import select

from app.db.models import Class, ParentStudentLink, Student, User
from app.graph.state import ConversationState
from app.personas.templates import build_persona_prompt


def persona_selector(state: ConversationState) -> ConversationState:
    state["trace"].append("persona_selector")
    session = state["db"]
    role = state["role"]

    child_names = "your child"
    class_names = "your classes"

    if role == "parent":
        ids = session.scalars(
            select(ParentStudentLink.student_id).where(
                ParentStudentLink.parent_id == state["user_id"]
            )
        ).all()
        if ids:
            names = session.scalars(
                select(User.name).join(Student, Student.id == User.id).where(User.id.in_(ids))
            ).all()
            child_names = " and ".join(names)
    elif role == "teacher":
        names = session.scalars(
            select(Class.name).where(Class.teacher_id == state["user_id"])
        ).all()
        if names:
            class_names = " and ".join(names)

    state["persona_prompt"] = build_persona_prompt(
        role,
        name=state["user_name"],
        language=state["language"],
        child_names=child_names,
        class_names=class_names,
    )
    return state
