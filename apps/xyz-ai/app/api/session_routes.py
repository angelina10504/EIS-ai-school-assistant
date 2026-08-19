"""Mock login + conversation-session lifecycle."""
from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.api.deps import CurrentUser, current_user, get_db
from app.api.schemas import (
    LanguageRequest,
    LoginRequest,
    LoginResponse,
    NewSessionResponse,
    UserOut,
)
from app.auth.security import create_access_token, verify_password
from app.db.models import ConversationSession, User
from app.i18n.languages import LANGUAGES, get_language

router = APIRouter(prefix="/api/session", tags=["session"])


@router.post("/login", response_model=LoginResponse)
def login(payload: LoginRequest, db: Session = Depends(get_db)) -> LoginResponse:
    user = db.scalar(select(User).where(User.email == payload.email.strip().lower()))
    if user is None or not verify_password(payload.password, user.password_hash):
        # Same message either way — no account enumeration.
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, "Invalid email or password")

    conversation = ConversationSession(user_id=user.id, language=user.preferred_language or "en")
    db.add(conversation)
    db.flush()

    return LoginResponse(
        token=create_access_token(user.id, user.role, user.name),
        user=UserOut(
            id=user.id,
            name=user.name,
            role=user.role,
            preferred_language=user.preferred_language or "en",
        ),
        session_id=conversation.id,
    )


@router.post("/new", response_model=NewSessionResponse)
def new_conversation(
    user: CurrentUser = Depends(current_user), db: Session = Depends(get_db)
) -> NewSessionResponse:
    conversation = ConversationSession(user_id=user.id, language=user.preferred_language)
    db.add(conversation)
    db.flush()
    return NewSessionResponse(session_id=conversation.id, language=conversation.language)


@router.get("/me", response_model=UserOut)
def me(user: CurrentUser = Depends(current_user)) -> UserOut:
    return UserOut(
        id=user.id, name=user.name, role=user.role, preferred_language=user.preferred_language
    )


@router.post("/language", response_model=UserOut)
def set_language(
    payload: LanguageRequest,
    user: CurrentUser = Depends(current_user),
    db: Session = Depends(get_db),
) -> UserOut:
    code = get_language(payload.language).code
    if payload.language.split("-")[0] not in LANGUAGES:
        raise HTTPException(status.HTTP_400_BAD_REQUEST, "Unsupported language")
    row = db.get(User, user.id)
    row.preferred_language = code
    db.flush()
    return UserOut(id=row.id, name=row.name, role=row.role, preferred_language=code)
