"""School-wide analytics for the principal. Aggregates only — no raw student rows."""
from __future__ import annotations

from datetime import date as date_cls, timedelta

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.db.models import Attendance, Class, Student

_WEEKDAYS = ["Monday", "Tuesday", "Wednesday", "Thursday", "Friday"]


# A day counts as fully marked once this share of the roll has a record.
_COMPLETE_DAY_THRESHOLD = 0.8


def _is_complete(day_records: list[Attendance], roll_size: int) -> bool:
    if roll_size <= 0:
        return bool(day_records)
    return len(day_records) >= roll_size * _COMPLETE_DAY_THRESHOLD


def _pct(records: list[Attendance]) -> float:
    if not records:
        return 0.0
    counted = sum(1.0 if r.status == "present" else 0.5 if r.status == "late" else 0.0 for r in records)
    return round(counted / len(records) * 100, 1)


def get_attendance_analytics(session: Session, *, scope: str = "school", days: int = 90) -> dict:
    if scope != "school":
        return {"ok": False, "error": "unsupported_scope"}

    today = date_cls.today()
    since = today - timedelta(days=days)
    records = list(
        session.scalars(select(Attendance).where(Attendance.date >= since)).all()
    )
    students = list(session.scalars(select(Student)).all())
    classes = list(session.scalars(select(Class)).all())

    by_class: dict[str, list[Attendance]] = {c.id: [] for c in classes}
    student_class = {s.id: s.class_id for s in students}
    for record in records:
        class_id = student_class.get(record.student_id)
        if class_id in by_class:
            by_class[class_id].append(record)

    class_rows = sorted(
        (
            {
                "class_name": c.name,
                "percentage": _pct(by_class[c.id]),
                "student_count": sum(1 for s in students if s.class_id == c.id),
                "records": len(by_class[c.id]),
            }
            for c in classes
        ),
        key=lambda row: row["percentage"],
    )

    # Group by date for daily trend
    by_date: dict[date_cls, list[Attendance]] = {}
    for record in records:
        by_date.setdefault(record.date, []).append(record)

    all_dates = sorted(by_date.keys())

    # A day still being marked is not a data point. At 9am a school shows 0% present,
    # which would otherwise render as a catastrophic bar and flip the trend badge to
    # "declining". Today's real state is reported separately in the `today` block.
    roll_size = len(students)
    complete_dates = [d for d in all_dates if _is_complete(by_date[d], roll_size)]

    recent_dates = all_dates[-7:] if len(all_dates) >= 7 else all_dates
    recent_daily_trend = [
        {
            "date": d.isoformat(),
            "day_name": d.strftime("%a"),
            "percentage": _pct(by_date[d]),
            "marked": len(by_date[d]),
            "roll_size": roll_size,
            "in_progress": not _is_complete(by_date[d], roll_size),
            "present": sum(1 for r in by_date[d] if r.status == "present"),
            "absent": sum(1 for r in by_date[d] if r.status == "absent"),
            "late": sum(1 for r in by_date[d] if r.status == "late"),
        }
        for d in recent_dates
    ]

    # Momentum: last 7 fully-marked days against the 7 before them.
    if len(complete_dates) >= 14:
        window, prior = complete_dates[-7:], complete_dates[-14:-7]
    elif len(complete_dates) >= 4:
        mid = len(complete_dates) // 2
        window, prior = complete_dates[mid:], complete_dates[:mid]
    else:
        window, prior = [], []

    if window and prior:
        diff = round(
            _pct([r for d in window for r in by_date[d]])
            - _pct([r for d in prior for r in by_date[d]]),
            1,
        )
        trend_direction = "improving" if diff > 0.5 else "declining" if diff < -0.5 else "stable"
        trend_change = diff
    else:
        trend_direction = "stable"
        trend_change = 0.0

    # Weekday aggregate breakdown
    by_weekday: dict[str, list[Attendance]] = {day: [] for day in _WEEKDAYS}
    complete_set = set(complete_dates)
    for record in records:
        day_str = record.date.strftime("%A")
        if day_str in by_weekday and record.date in complete_set:
            by_weekday[day_str].append(record)

    weekday_breakdown = [
        {
            "day": day,
            "short_day": day[:3],
            "percentage": _pct(by_weekday[day]),
            "records": len(by_weekday[day]),
        }
        for day in _WEEKDAYS
        if by_weekday[day]
    ]

    today_records = [r for r in records if r.date == today]

    # Aggregate risk signal, deliberately a count rather than a list of names.
    per_student: dict[str, list[Attendance]] = {}
    for record in records:
        per_student.setdefault(record.student_id, []).append(record)
    below_75 = sum(1 for rows in per_student.values() if _pct(rows) < 75)
    at_risk_pct = round((below_75 / len(students) * 100), 1) if students else 0.0

    return {
        "ok": True,
        "scope": "school",
        "window_days": days,
        "overall_percentage": _pct(records),
        "total_students": len(students),
        "total_classes": len(classes),
        "records_considered": len(records),
        # Distinct days that actually have attendance, which is what a person means
        # by "how long" — window_days is just the SQL lookback.
        "school_days_counted": len(all_dates),
        "trend_direction": trend_direction,
        "trend_change": trend_change,
        "recent_daily_trend": recent_daily_trend,
        "weekday_breakdown": weekday_breakdown,
        "today": {
            "date": today.isoformat(),
            "marked": len(today_records),
            "present": sum(1 for r in today_records if r.status == "present"),
            "absent": sum(1 for r in today_records if r.status == "absent"),
            "late": sum(1 for r in today_records if r.status == "late"),
            "percentage": _pct(today_records) if today_records else 0.0,
            "roll_size": roll_size,
            "in_progress": not _is_complete(today_records, roll_size),
        },
        "by_class": class_rows,
        "lowest_class": class_rows[0]["class_name"] if class_rows else None,
        "highest_class": class_rows[-1]["class_name"] if class_rows else None,
        "students_below_75_percent": below_75,
        "at_risk_percentage": at_risk_pct,
    }
