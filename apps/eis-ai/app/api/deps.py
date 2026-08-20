"""Request-scoped dependencies: the DB session and the caller's identity."""
from __future__ import annotations

from dataclasses import dataclass

from fastapi import Depends, Header, HTTPException, status
from sqlalchemy.orm import Session

from app.auth.security import InvalidToken, decode_access_token
from app.db.models import User
from app.db.session import fastapi_session


@dataclass(frozen=True)
class CurrentUser:
    id: str
    role: str
    name: str
    preferred_language: str


def get_db() -> Session:  # pragma: no cover - thin wrapper for DI
    yield from fastapi_session()


def current_user(
    authorization: str | None = Header(default=None),
    db: Session = Depends(get_db),
) -> CurrentUser:
    if not authorization or not authorization.lower().startswith("bearer "):
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, "Missing bearer token")
    try:
        payload = decode_access_token(authorization.split(" ", 1)[1].strip())
    except InvalidToken:
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, "Invalid or expired session")

    user = db.get(User, payload.get("sub"))
    if user is None:
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, "Unknown user")

    # The role is re-read from the database, not taken from the token body.
    return CurrentUser(
        id=user.id, role=user.role, name=user.name, preferred_language=user.preferred_language or "en"
    )
