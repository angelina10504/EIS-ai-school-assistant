"""Mock school-ERP analytics API — principal only, aggregates only."""
from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.api.deps import CurrentUser, current_user, get_db
from app.auth.audit import log_permission_check
from app.auth.permissions import check_permission
from app.tools.analytics_tools import get_attendance_analytics

router = APIRouter(prefix="/api/analytics", tags=["analytics"])


@router.get("/attendance")
def attendance_analytics(
    user: CurrentUser = Depends(current_user), db: Session = Depends(get_db)
) -> dict:
    decision = check_permission(user.role, "view_analytics")
    log_permission_check(
        db, user_id=user.id, action="rest:view_analytics", resource="school", allowed=decision.allowed
    )
    if not decision.allowed:
        raise HTTPException(status.HTTP_403_FORBIDDEN, decision.reason or "Not permitted")
    return get_attendance_analytics(db, scope="school")
