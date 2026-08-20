from __future__ import annotations

import logging

from app.config import get_settings
from app.llm.base import LLMProvider
from app.llm.offline import OfflineProvider

logger = logging.getLogger(__name__)

_provider: LLMProvider | None = None


def get_llm() -> LLMProvider:
    global _provider
    if _provider is None:
        settings = get_settings()
        if settings.llm_enabled:
            try:
                from app.llm.gemini import GeminiProvider

                _provider = GeminiProvider()
                logger.info("Using Gemini model %s", settings.gemini_model)
            except Exception:  # pragma: no cover - depends on local SDK/creds
                logger.exception("Gemini unavailable, falling back to offline provider")
                _provider = OfflineProvider()
        else:
            logger.warning("GEMINI_API_KEY not set — running with the offline provider")
            _provider = OfflineProvider()
    return _provider


def set_llm(provider: LLMProvider | None) -> None:
    """Test seam."""
    global _provider
    _provider = provider


__all__ = ["LLMProvider", "OfflineProvider", "get_llm", "set_llm"]
