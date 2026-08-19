"""Demo data: 1 principal, 2 teachers, 2 classes, 6 students, 3 parents, ~7 weeks
of weekday attendance so that follow-up questions and analytics have real history.

    python -m app.db.seed          # create tables (SQLite) and seed
    python -m app.db.seed --reset  # wipe and reseed
"""
from __future__ import annotations

import argparse
from datetime import date, timedelta

from sqlalchemy import delete, select

from app.auth.security import hash_password
from app.db.models import (
    Attendance,
    AuditLog,
    Class,
    ConversationMessage,
    ConversationSession,
    EscalationRequest,
    ParentStudentLink,
    Student,
    User,
)
from app.db.session import create_all, db_session

DEMO_PASSWORD = "password123"
SCHOOL_DAYS = 34  # weekdays of history

# name, email, absent-day offsets, late-day offsets (indexes into the weekday list)
STUDENT_PLAN = [
    ("Rahul Verma", "rahul@student.xyz.edu", "8A-01", "8A", [6, 19], [11, 27]),
    ("Priya Nair", "priya@student.xyz.edu", "8A-02", "8A", [3], [22]),
    ("Arjun Nair", "arjun@student.xyz.edu", "8A-03", "8A", [1, 2, 9, 14, 20, 25, 30], [8]),
    ("Sneha Kulkarni", "sneha@student.xyz.edu", "8B-01", "8B", [12], []),
    ("Imran Khan", "imran@student.xyz.edu", "8B-02", "8B", [4, 5, 17], [21, 29]),
    ("Divya Reddy", "divya@student.xyz.edu", "8B-03", "8B", [7, 16, 23, 28], [2, 13]),
]

PARENT_PLAN = [
    ("Sunita Verma", "sunita@parent.xyz.edu", ["Rahul Verma"]),
    ("Ramesh Nair", "ramesh@parent.xyz.edu", ["Priya Nair", "Arjun Nair"]),
    ("Farah Khan", "farah@parent.xyz.edu", ["Imran Khan"]),
]


def weekdays_back(count: int, today: date | None = None) -> list[date]:
    today = today or date.today()
    days: list[date] = []
    cursor = today
    while len(days) < count:
        if cursor.weekday() < 5:
            days.append(cursor)
        cursor -= timedelta(days=1)
    return sorted(days)


def reset(session) -> None:
    for model in (
        AuditLog,
        ConversationMessage,
        ConversationSession,
        EscalationRequest,
        Attendance,
        ParentStudentLink,
        Student,
        Class,
        User,
    ):
        session.execute(delete(model))
    session.flush()


def seed(session) -> dict:
    principal = User(
        role="principal",
        name="Dr. Meera Iyer",
        email="principal@xyz.edu",
        password_hash=hash_password(DEMO_PASSWORD),
        preferred_language="en",
    )
    anita = User(
        role="teacher",
        name="Anita Sharma",
        email="anita@teacher.xyz.edu",
        password_hash=hash_password(DEMO_PASSWORD),
        preferred_language="en",
    )
    vikram = User(
        role="teacher",
        name="Vikram Rao",
        email="vikram@teacher.xyz.edu",
        password_hash=hash_password(DEMO_PASSWORD),
        preferred_language="en",
    )
    session.add_all([principal, anita, vikram])
    session.flush()

    class_8a = Class(name="Class 8A", teacher_id=anita.id)
    class_8b = Class(name="Class 8B", teacher_id=vikram.id)
    session.add_all([class_8a, class_8b])
    session.flush()
    classes = {"8A": class_8a, "8B": class_8b}

    days = weekdays_back(SCHOOL_DAYS)
    students: dict[str, Student] = {}

    for name, email, roll, class_key, absents, lates in STUDENT_PLAN:
        user = User(
            role="student",
            name=name,
            email=email,
            password_hash=hash_password(DEMO_PASSWORD),
            preferred_language="en",
        )
        session.add(user)
        session.flush()
        student = Student(id=user.id, roll_number=roll, class_id=classes[class_key].id)
        session.add(student)
        session.flush()
        students[name] = student

        teacher_id = classes[class_key].teacher_id
        for index, day in enumerate(days):
            status = "absent" if index in absents else "late" if index in lates else "present"
            session.add(
                Attendance(
                    student_id=student.id, date=day, status=status, marked_by=teacher_id
                )
            )

    for name, email, children in PARENT_PLAN:
        parent = User(
            role="parent",
            name=name,
            email=email,
            password_hash=hash_password(DEMO_PASSWORD),
            preferred_language="en",
        )
        session.add(parent)
        session.flush()
        for child in children:
            session.add(
                ParentStudentLink(parent_id=parent.id, student_id=students[child].id)
            )

    session.flush()
    return {
        "users": session.scalar(select(User).limit(1)) is not None,
        "students": len(students),
        "school_days": len(days),
    }


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--reset", action="store_true", help="wipe existing rows first")
    args = parser.parse_args()

    create_all()
    with db_session() as session:
        existing = session.scalar(select(User).limit(1))
        if existing and not args.reset:
            print("Database already seeded. Re-run with --reset to wipe and reseed.")
            return
        if args.reset:
            reset(session)
        summary = seed(session)
    print(f"Seeded {summary['students']} students over {summary['school_days']} school days.")
    print(f"Demo password for every account: {DEMO_PASSWORD}")


if __name__ == "__main__":
    main()
