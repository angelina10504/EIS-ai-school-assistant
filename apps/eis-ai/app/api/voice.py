"""Voice endpoints. Thin wrappers so the frontend never touches Google directly."""
from __future__ import annotations

import asyncio

from fastapi import APIRouter, Depends, File, Form, HTTPException, UploadFile, status
from starlette.concurrency import run_in_threadpool

from app.api.deps import CurrentUser, current_user
from app.api.schemas import TTSRequest
from app.voice import stt as stt_module
from app.voice import tts as tts_module

router = APIRouter(prefix="/api/voice", tags=["voice"])

MAX_AUDIO_BYTES = 10 * 1024 * 1024
# A slow Google call must never hold a request open indefinitely.
SPEECH_TIMEOUT_SECONDS = 30


@router.post("/stt")
async def speech_to_text(
    audio: UploadFile = File(...),
    language: str = Form("en"),
    user: CurrentUser = Depends(current_user),
) -> dict:
    payload = await audio.read()
    if not payload:
        raise HTTPException(status.HTTP_400_BAD_REQUEST, "Empty audio upload")
    if len(payload) > MAX_AUDIO_BYTES:
        raise HTTPException(status.HTTP_413_REQUEST_ENTITY_TOO_LARGE, "Audio clip too large")
    # transcribe() is blocking network I/O. Calling it directly from an async
    # endpoint pins the event loop, so one slow Google call freezes every other
    # request — including login. Hand it to a worker thread instead.
    try:
        transcript = await asyncio.wait_for(
            run_in_threadpool(
                stt_module.transcribe, payload, language or user.preferred_language
            ),
            timeout=SPEECH_TIMEOUT_SECONDS,
        )
    except asyncio.TimeoutError:
        raise HTTPException(
            status.HTTP_504_GATEWAY_TIMEOUT,
            "Speech-to-Text did not respond in time. Please try again.",
        )
    except stt_module.SpeechUnavailable as exc:
        raise HTTPException(status.HTTP_503_SERVICE_UNAVAILABLE, str(exc))
    return {
        "transcript": transcript.text,
        "language": transcript.language,
        "confidence": transcript.confidence,
    }


@router.post("/tts")
def text_to_speech(payload: TTSRequest, user: CurrentUser = Depends(current_user)) -> dict:
    try:
        speech = tts_module.synthesize(payload.text, payload.language or user.preferred_language)
    except tts_module.SpeechUnavailable as exc:
        raise HTTPException(status.HTTP_503_SERVICE_UNAVAILABLE, str(exc))
    return {
        "audio_base64": speech.audio_base64,
        "mime_type": speech.mime_type,
        "language": speech.language,
        "marks": [{"name": m.name, "word": m.word, "seconds": m.seconds} for m in speech.marks],
    }
