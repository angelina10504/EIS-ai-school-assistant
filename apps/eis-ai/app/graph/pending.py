"""Pending escalation offers, keyed by conversation session.

In-process on purpose: an offer that has not been confirmed is not a record, and
Implementation Guidelines §11 requires that nothing is written to
escalation_requests until the user says yes. A multi-process deployment would move
this to Redis or a dedicated table (see README, known limitations).
"""
from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timedelta, timezone

TTL = timedelta(minutes=15)


@dataclass
class PendingEscalation:
    session_id: str
    requester_id: str
    requester_role: str
    target_role: str
    target_name: str
    student_id: str | None
    reason: str | None
    created_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))

    @property
    def expired(self) -> bool:
        return datetime.now(timezone.utc) - self.created_at > TTL


_PENDING: dict[str, PendingEscalation] = {}


def put(pending: PendingEscalation) -> None:
    _PENDING[pending.session_id] = pending


def get(session_id: str) -> PendingEscalation | None:
    found = _PENDING.get(session_id)
    if found and found.expired:
        _PENDING.pop(session_id, None)
        return None
    return found


def clear(session_id: str) -> None:
    _PENDING.pop(session_id, None)


def clear_all() -> None:
    _PENDING.clear()
