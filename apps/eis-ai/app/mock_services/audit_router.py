"""Read-only view of the caller's own audit trail — powers the security demo panel."""
from __future__ import annotations

from fastapi import APIRouter, Depends
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.api.deps import CurrentUser, current_user, get_db
from app.db.models import AuditLog

router = APIRouter(prefix="/api/audit", tags=["audit"])


@router.get("/recent")
def recent(
    limit: int = 25, user: CurrentUser = Depends(current_user), db: Session = Depends(get_db)
) -> dict:
    rows = db.scalars(
        select(AuditLog)
        .where(AuditLog.user_id == user.id)
        .order_by(AuditLog.created_at.desc(), AuditLog.id.desc())
        .limit(min(limit, 100))
    ).all()
    return {
        "entries": [
            {
                "action": r.action,
                "resource": r.resource,
                "allowed": r.allowed,
                "at": r.created_at.isoformat() if r.created_at else None,
            }
            for r in rows
        ]
    }
