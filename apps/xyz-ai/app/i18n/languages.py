"""Language registry — BCP-47 codes for Google STT/TTS plus display names."""
from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class Language:
    code: str          # short code stored on users.preferred_language
    bcp47: str         # what Google Cloud Speech expects
    english_name: str
    native_name: str
    tts_voice: str     # a Google Cloud TTS voice that exists for this locale


LANGUAGES: dict[str, Language] = {
    "en": Language("en", "en-IN", "English", "English", "en-IN-Wavenet-D"),
    "hi": Language("hi", "hi-IN", "Hindi", "हिन्दी", "hi-IN-Wavenet-D"),
    "ta": Language("ta", "ta-IN", "Tamil", "தமிழ்", "ta-IN-Wavenet-D"),
    "te": Language("te", "te-IN", "Telugu", "తెలుగు", "te-IN-Standard-B"),
    "mr": Language("mr", "mr-IN", "Marathi", "मराठी", "mr-IN-Wavenet-C"),
    "bn": Language("bn", "bn-IN", "Bengali", "বাংলা", "bn-IN-Wavenet-C"),
    "gu": Language("gu", "gu-IN", "Gujarati", "ગુજરાતી", "gu-IN-Wavenet-C"),
    "pa": Language("pa", "pa-IN", "Punjabi", "ਪੰਜਾਬੀ", "pa-IN-Wavenet-C"),
    "kn": Language("kn", "kn-IN", "Kannada", "ಕನ್ನಡ", "kn-IN-Wavenet-C"),
    "ml": Language("ml", "ml-IN", "Malayalam", "മലയാളം", "ml-IN-Wavenet-C"),
    "ur": Language("ur", "ur-IN", "Urdu", "اردو", "ur-IN-Wavenet-B"),
}

DEFAULT_LANGUAGE = "en"


def get_language(code: str | None) -> Language:
    if not code:
        return LANGUAGES[DEFAULT_LANGUAGE]
    short = code.split("-")[0].lower()
    return LANGUAGES.get(short, LANGUAGES[DEFAULT_LANGUAGE])


def bcp47(code: str | None) -> str:
    return get_language(code).bcp47


def english_name(code: str | None) -> str:
    return get_language(code).english_name


def supported_codes() -> list[str]:
    return list(LANGUAGES)
