from __future__ import annotations

from typing import Any, Literal

from pydantic import BaseModel, Field


class LoginRequest(BaseModel):
    email: str
    password: str


class UserOut(BaseModel):
    id: str
    name: str
    role: str
    preferred_language: str


class LoginResponse(BaseModel):
    token: str
    user: UserOut
    session_id: str


class NewSessionResponse(BaseModel):
    session_id: str
    language: str


class ChatRequest(BaseModel):
    session_id: str
    message: str = Field(min_length=1, max_length=4000)
    language: str | None = None


class ChatResponse(BaseModel):
    response: str
    intent: str | None
    language: str
    requires_confirmation: bool = False
    permitted: bool = True
    security_flags: list[str] = []
    trace: list[str] = []
    data: dict[str, Any] | None = None


class ConfirmRequest(BaseModel):
    session_id: str
    confirm: bool = True


class MarkAttendanceRequest(BaseModel):
    student_id: str | None = None
    student_name: str | None = None
    status: Literal["present", "absent", "late"]
    date: str | None = None


class TTSRequest(BaseModel):
    text: str = Field(min_length=1, max_length=2000)
    language: str = "en"


class LanguageRequest(BaseModel):
    language: str
