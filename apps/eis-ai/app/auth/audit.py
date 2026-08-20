"""Every permission check — allowed or denied — lands in audit_log."""
from __future__ import annotations

from sqlalchemy.orm import Session

from app.db.models import AuditLog


def log_permission_check(
    session: Session,
    *,
    user_id: str | None,
    action: str,
    resource: str | None,
    allowed: bool,
) -> None:
    session.add(
        AuditLog(user_id=user_id, action=action, resource=resource, allowed=allowed)
    )
    session.flush()
