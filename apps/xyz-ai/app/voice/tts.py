"""Google Cloud Text-to-Speech with SSML <mark> timepoints for lip-sync.

Cloud TTS does not emit visemes. We insert a <mark> between every word, ask for
timepoints, and hand the frontend `{audio, marks[]}` — enough to drive a 3-5 shape
mouth state machine (Implementation Guidelines §8-9).
"""
from __future__ import annotations

import base64
import logging
import re
from dataclasses import dataclass

from app.i18n.languages import bcp47, get_language

logger = logging.getLogger(__name__)


class SpeechUnavailable(RuntimeError):
    pass


@dataclass(frozen=True)
class Mark:
    name: str
    word: str
    seconds: float


@dataclass(frozen=True)
class Speech:
    audio_base64: str
    mime_type: str
    marks: list[Mark]
    language: str


_ESCAPE = {"&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;"}


def _escape(text: str) -> str:
    return "".join(_ESCAPE.get(char, char) for char in text)


def build_ssml(text: str) -> tuple[str, list[str]]:
    words = [w for w in re.split(r"\s+", text.strip()) if w]
    parts = []
    for index, word in enumerate(words):
        parts.append(f'<mark name="w{index}"/>{_escape(word)}')
    return f"<speak>{' '.join(parts)}</speak>", words


def _client():
    try:
        from pathlib import Path
        from google.cloud import texttospeech_v1beta1 as texttospeech
        from google.oauth2 import service_account
        from app.config import BASE_DIR, get_settings
    except ImportError as exc:  # pragma: no cover
        raise SpeechUnavailable("google-cloud-texttospeech is not installed") from exc

    try:
        settings = get_settings()
        creds_path = settings.google_application_credentials
        if creds_path:
            path = Path(creds_path)
            if not path.is_absolute():
                path = BASE_DIR / path
            if path.exists():
                creds = service_account.Credentials.from_service_account_file(str(path))
                return texttospeech.TextToSpeechClient(credentials=creds), texttospeech
        return texttospeech.TextToSpeechClient(), texttospeech
    except Exception as exc:  # pragma: no cover - missing/invalid credentials
        from app.config import get_settings

        detail = f"{type(exc).__name__}: {exc}"
        logger.error("Text-to-Speech client could not start — %s", detail)
        raise SpeechUnavailable(
            f"Text-to-Speech is unavailable. Credentials: {get_settings().speech_status}. {detail}"
        ) from exc


def synthesize(text: str, language: str = "en") -> Speech:
    client, tts = _client()
    ssml, words = build_ssml(text)
    lang = get_language(language)

    timepoint_type = getattr(
        tts.SynthesizeSpeechRequest,
        "TimepointType",
        None,
    )
    enable_time_pointing = (
        [timepoint_type.SSML_MARK] if timepoint_type else [1]
    )

    request = tts.SynthesizeSpeechRequest(
        input=tts.SynthesisInput(ssml=ssml),
        voice=tts.VoiceSelectionParams(language_code=bcp47(language), name=lang.tts_voice),
        audio_config=tts.AudioConfig(
            audio_encoding=tts.AudioEncoding.MP3, speaking_rate=1.0, pitch=0.0
        ),
        enable_time_pointing=enable_time_pointing,
    )
    try:
        response = client.synthesize_speech(request=request)
    except Exception as exc:  # pragma: no cover - voice name may not exist in a region
        logger.warning("TTS failed with voice %s (%s); retrying with default voice", lang.tts_voice, exc)
        request.voice = tts.VoiceSelectionParams(language_code=bcp47(language))
        response = client.synthesize_speech(request=request)

    marks = [
        Mark(name=tp.mark_name, word=words[int(tp.mark_name[1:])] if tp.mark_name[1:].isdigit() and int(tp.mark_name[1:]) < len(words) else "", seconds=tp.time_seconds)
        for tp in getattr(response, "timepoints", [])
    ]
    if not marks:
        marks = estimate_marks(words)

    return Speech(
        audio_base64=base64.b64encode(response.audio_content).decode(),
        mime_type="audio/mpeg",
        marks=marks,
        language=get_language(language).code,
    )


def estimate_marks(words: list[str], wpm: float = 150.0) -> list[Mark]:
    """Fallback timing when the API returns no timepoints — keeps the avatar moving."""
    seconds_per_char = 60.0 / (wpm * 5.1)
    cursor = 0.0
    marks = []
    for index, word in enumerate(words):
        marks.append(Mark(name=f"w{index}", word=word, seconds=round(cursor, 3)))
        cursor += max(0.12, len(word) * seconds_per_char) + 0.06
    return marks
