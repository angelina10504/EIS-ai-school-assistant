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

# Fixed UUIDs, matching infra/supabase/seed.sql exactly. Random ids would change on
# every reseed, invalidating any JWT already issued — which logs you out of the app
# the moment you refresh the demo data.
ID = {
    "principal": "00000000-0000-4000-8000-000000000001",
    "anita": "00000000-0000-4000-8000-000000000002",
    "vikram": "00000000-0000-4000-8000-000000000003",
    "8A": "00000000-0000-4000-8000-0000000000a1",
    "8B": "00000000-0000-4000-8000-0000000000a2",
}

# name, email, absent-day offsets, late-day offsets (indexes into the weekday list)
STUDENT_PLAN = [
    ("00000000-0000-4000-8000-000000000011", "Rahul Verma", "rahul@student.eis.edu", "8A-01", "8A", [6, 19], [11, 27]),
    ("00000000-0000-4000-8000-000000000012", "Priya Nair", "priya@student.eis.edu", "8A-02", "8A", [3], [22]),
    ("00000000-0000-4000-8000-000000000013", "Arjun Nair", "arjun@student.eis.edu", "8A-03", "8A", [1, 2, 9, 14, 20, 25, 30], [8]),
    ("00000000-0000-4000-8000-000000000014", "Sneha Kulkarni", "sneha@student.eis.edu", "8B-01", "8B", [12], []),
    ("00000000-0000-4000-8000-000000000015", "Imran Khan", "imran@student.eis.edu", "8B-02", "8B", [4, 5, 17], [21, 29]),
    ("00000000-0000-4000-8000-000000000016", "Divya Reddy", "divya@student.eis.edu", "8B-03", "8B", [7, 16, 23, 28], [2, 13]),
]

PARENT_PLAN = [
    ("00000000-0000-4000-8000-000000000021", "Sunita Verma", "sunita@parent.eis.edu", ["Rahul Verma"]),
    ("00000000-0000-4000-8000-000000000022", "Ramesh Nair", "ramesh@parent.eis.edu", ["Priya Nair", "Arjun Nair"]),
    ("00000000-0000-4000-8000-000000000023", "Farah Khan", "farah@parent.eis.edu", ["Imran Khan"]),
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
        id=ID["principal"],
        role="principal",
        name="Dr. Meera Iyer",
        email="principal@eis.edu",
        password_hash=hash_password(DEMO_PASSWORD),
        preferred_language="en",
    )
    anita = User(
        id=ID["anita"],
        role="teacher",
        name="Anita Sharma",
        email="anita@teacher.eis.edu",
        password_hash=hash_password(DEMO_PASSWORD),
        preferred_language="en",
    )
    vikram = User(
        id=ID["vikram"],
        role="teacher",
        name="Vikram Rao",
        email="vikram@teacher.eis.edu",
        password_hash=hash_password(DEMO_PASSWORD),
        preferred_language="en",
    )
    session.add_all([principal, anita, vikram])
    session.flush()

    class_8a = Class(id=ID["8A"], name="Class 8A", teacher_id=anita.id)
    class_8b = Class(id=ID["8B"], name="Class 8B", teacher_id=vikram.id)
    session.add_all([class_8a, class_8b])
    session.flush()
    classes = {"8A": class_8a, "8B": class_8b}

    days = weekdays_back(SCHOOL_DAYS)
    students: dict[str, Student] = {}

    for user_id, name, email, roll, class_key, absents, lates in STUDENT_PLAN:
        user = User(
            id=user_id,
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

    for parent_id, name, email, children in PARENT_PLAN:
        parent = User(
            id=parent_id,
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
