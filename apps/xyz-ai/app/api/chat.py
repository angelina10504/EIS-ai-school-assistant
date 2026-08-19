"""The chat surface: one endpoint that runs the graph, one that confirms an offer."""
from __future__ import annotations

from datetime import date

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.api.deps import CurrentUser, current_user, get_db
from app.api.schemas import ChatRequest, ChatResponse, ConfirmRequest
from app.db.models import ConversationSession
from app.graph import pending, run_turn
from app.graph.nodes import (
    auth_resolver,
    language_detector,
    memory_loader,
    memory_writer,
    permission_gate,
    persona_selector,
    response_formatter,
    tool_executor,
)
from app.graph.state import new_state

router = APIRouter(prefix="/api/chat", tags=["chat"])

_INTERNAL_KEYS = {"escalation_id", "flags"}


def _owned_session(db: Session, session_id: str, user: CurrentUser) -> ConversationSession:
    conversation = db.get(ConversationSession, session_id)
    if conversation is None or conversation.user_id != user.id:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Conversation session not found")
    return conversation


def _public(tool_result: dict | None) -> dict | None:
    if not tool_result:
        return None
    return {k: v for k, v in tool_result.items() if k not in _INTERNAL_KEYS}


@router.post("", response_model=ChatResponse)
@router.post("/", response_model=ChatResponse, include_in_schema=False)
def chat(
    payload: ChatRequest,
    user: CurrentUser = Depends(current_user),
    db: Session = Depends(get_db),
) -> ChatResponse:
    conversation = _owned_session(db, payload.session_id, user)

    state = run_turn(
        db=db,
        user_id=user.id,
        session_id=conversation.id,
        message=payload.message,
        language=payload.language or conversation.language or user.preferred_language,
    )

    # A voice utterance in another language switches the session over.
    if state.get("language") and state["language"] != conversation.language:
        conversation.language = state["language"]
        db.flush()

    return ChatResponse(
        response=state.get("response") or "",
        intent=state.get("intent"),
        language=state.get("language", "en"),
        requires_confirmation=bool(state.get("requires_confirmation")),
        permitted=bool(state.get("permitted")),
        security_flags=state.get("security_flags", []),
        trace=state.get("trace", []),
        data=_public(state.get("tool_result")),
    )


@router.post("/confirm", response_model=ChatResponse)
def confirm(
    payload: ConfirmRequest,
    user: CurrentUser = Depends(current_user),
    db: Session = Depends(get_db),
) -> ChatResponse:
    """Explicit 'yes' step. Nothing was written to escalation_requests before this."""
    conversation = _owned_session(db, payload.session_id, user)

    outstanding = pending.get(conversation.id)
    if outstanding is None:
        raise HTTPException(status.HTTP_409_CONFLICT, "There is nothing awaiting confirmation")

    if not payload.confirm:
        pending.clear(conversation.id)
        return ChatResponse(
            response="No problem — I won't put that request through.",
            intent="escalate",
            language=conversation.language or "en",
            requires_confirmation=False,
            data={"kind": "escalation_cancelled"},
        )

    # Reuse the graph's own nodes so the audit log and memory stay consistent.
    state = new_state(
        db=db,
        user_id=user.id,
        session_id=conversation.id,
        message="Yes, please request the call.",
        language=conversation.language or user.preferred_language,
        today=date.today().isoformat(),
    )
    auth_resolver(state)
    language_detector(state)
    memory_loader(state)
    state["intent"] = "escalate"
    state["confirming"] = True
    permission_gate(state)
    persona_selector(state)
    tool_executor(state)
    response_formatter(state)
    memory_writer(state)

    return ChatResponse(
        response=state.get("response") or "",
        intent="escalate",
        language=state.get("language", "en"),
        requires_confirmation=False,
        permitted=bool(state.get("permitted")),
        trace=state.get("trace", []),
        data=_public(state.get("tool_result")),
    )
