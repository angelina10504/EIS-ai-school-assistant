"""Google Cloud Speech-to-Text wrapper.

Language-aware: the BCP-47 code comes from the caller's profile, with the other
supported Indian languages offered as alternatives so a code-switched utterance
still transcribes.
"""
from __future__ import annotations

import logging
from dataclasses import dataclass

from app.i18n.languages import LANGUAGES, bcp47
from app.voice.resilience import call_with_retry, is_transient

logger = logging.getLogger(__name__)


class SpeechUnavailable(RuntimeError):
    pass


@dataclass(frozen=True)
class Transcript:
    text: str
    language: str
    confidence: float


def _client():
    try:
        from pathlib import Path
        from google.cloud import speech
        from google.oauth2 import service_account
        from app.config import BASE_DIR, get_settings
    except ImportError as exc:  # pragma: no cover
        raise SpeechUnavailable("google-cloud-speech is not installed") from exc

    try:
        settings = get_settings()
        creds_path = settings.google_application_credentials
        if creds_path:
            path = Path(creds_path)
            if not path.is_absolute():
                path = BASE_DIR / path
            if path.exists():
                creds = service_account.Credentials.from_service_account_file(str(path))
                return speech.SpeechClient(credentials=creds), speech
        from app.config import get_settings

        return speech.SpeechClient(transport=get_settings().speech_transport), speech
    except Exception as exc:  # pragma: no cover - missing/invalid credentials
        from app.config import get_settings

        detail = f"{type(exc).__name__}: {exc}"
        logger.error("Speech-to-Text client could not start — %s", detail)
        raise SpeechUnavailable(
            f"Speech-to-Text is unavailable. Credentials: {get_settings().speech_status}. {detail}"
        ) from exc



def _recognize(client, speech, config, audio_bytes, *, what: str):
    return call_with_retry(
        lambda: client.recognize(
            config=config, audio=speech.RecognitionAudio(content=audio_bytes)
        ),
        what=what,
    )


def _config(speech, *, language: str, alternates: list[str], sample_rate: int | None):
    return speech.RecognitionConfig(
        encoding=speech.RecognitionConfig.AudioEncoding.WEBM_OPUS,
        language_code=language,
        enable_automatic_punctuation=True,
        **({"alternative_language_codes": alternates} if alternates else {}),
        **({"sample_rate_hertz": sample_rate} if sample_rate else {}),
    )


def transcribe(audio_bytes: bytes, language: str = "en", *, sample_rate: int | None = None) -> Transcript:
    """Audio to text, language-aware.

    First pass offers alternative language codes so a code-switched utterance still
    transcribes. Not every model/region accepts alternates, so a hard failure falls
    back to the primary language alone. Transient network errors are retried inside
    `_recognize` and surface as SpeechUnavailable (503) rather than a bare 500.
    """
    client, speech = _client()
    primary = bcp47(language)
    alternates = [lang.bcp47 for lang in LANGUAGES.values() if lang.bcp47 != primary][:3]

    try:
        response = _recognize(
            client, speech,
            _config(speech, language=primary, alternates=alternates, sample_rate=sample_rate),
            audio_bytes, what="Speech-to-Text",
        )
    except Exception as exc:
        if is_transient(exc):
            raise SpeechUnavailable(
                f"Speech-to-Text is temporarily unreachable ({type(exc).__name__}). "
                "This is usually a network blip — try again."
            ) from exc

        logger.warning(
            "STT failed with alternate languages (%s); retrying with %s only",
            type(exc).__name__, primary,
        )
        try:
            response = _recognize(
                client, speech,
                _config(speech, language=primary, alternates=[], sample_rate=sample_rate),
                audio_bytes, what="Speech-to-Text (primary language only)",
            )
        except Exception as retry_exc:
            raise SpeechUnavailable(
                f"Speech-to-Text failed: {type(retry_exc).__name__}: {retry_exc}"
            ) from retry_exc

    for result in response.results:
        if result.alternatives:
            best = result.alternatives[0]
            detected = (getattr(result, "language_code", "") or primary).split("-")[0]
            return Transcript(
                text=best.transcript.strip(), language=detected, confidence=best.confidence
            )
    return Transcript(text="", language=language, confidence=0.0)
