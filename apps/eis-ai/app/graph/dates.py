"""Turn the date phrase the classifier extracted into a real date."""
from __future__ import annotations

import re
from datetime import date as date_cls, datetime, timedelta

_WEEKDAYS = {
    "monday": 0, "tuesday": 1, "wednesday": 2, "thursday": 3,
    "friday": 4, "saturday": 5, "sunday": 6,
}
_MONTHS = {
    m: i
    for i, m in enumerate(
        ["jan", "feb", "mar", "apr", "may", "jun", "jul", "aug", "sep", "oct", "nov", "dec"],
        start=1,
    )
}


def resolve_date(phrase: str | None, today: date_cls | None = None) -> date_cls | None:
    if not phrase:
        return None
    today = today or date_cls.today()
    text = phrase.strip().lower()

    if text in ("today", "now", "aaj", "आज"):
        return today
    if text in ("yesterday", "kal", "कल"):
        return today - timedelta(days=1)
    if "day before yesterday" in text:
        return today - timedelta(days=2)
    if text in ("tomorrow",):
        return today + timedelta(days=1)

    iso = re.search(r"\b(\d{4})-(\d{2})-(\d{2})\b", text)
    if iso:
        try:
            return date_cls(int(iso.group(1)), int(iso.group(2)), int(iso.group(3)))
        except ValueError:
            return None

    ago = re.search(r"\b(\d+)\s+days?\s+ago\b", text)
    if ago:
        return today - timedelta(days=int(ago.group(1)))

    weekday = re.search(r"\b(last|this|past)?\s*(" + "|".join(_WEEKDAYS) + r")\b", text)
    if weekday:
        target = _WEEKDAYS[weekday.group(2)]
        delta = (today.weekday() - target) % 7
        delta = delta or 7  # "last monday" on a Monday means the previous one
        return today - timedelta(days=delta)

    dm = re.search(r"\b(\d{1,2})(?:st|nd|rd|th)?\s+([a-z]{3,})\b", text)
    if dm and dm.group(2)[:3] in _MONTHS:
        month = _MONTHS[dm.group(2)[:3]]
        day = int(dm.group(1))
        year = today.year if month <= today.month else today.year - 1
        try:
            return date_cls(year, month, day)
        except ValueError:
            return None

    slash = re.search(r"\b(\d{1,2})/(\d{1,2})(?:/(\d{2,4}))?\b", text)
    if slash:
        day, month = int(slash.group(1)), int(slash.group(2))
        year = int(slash.group(3) or today.year)
        year += 2000 if year < 100 else 0
        try:
            return date_cls(year, month, day)
        except ValueError:
            return None

    for fmt in ("%d %B %Y", "%B %d %Y", "%d %b %Y"):
        try:
            return datetime.strptime(f"{phrase} {today.year}", fmt).date()
        except ValueError:
            continue
    return None
