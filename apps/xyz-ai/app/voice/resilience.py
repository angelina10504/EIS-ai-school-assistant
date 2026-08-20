"""Shared retry/translation for Google Speech RPCs.

A transient network wobble — a cancelled DNS query, a 503 from a busy region —
was surfacing to the browser as a bare 500 with no explanation. These helpers
retry the recoverable cases and convert whatever survives into SpeechUnavailable,
so the API answers 503 with a reason instead of an opaque server error.
"""
from __future__ import annotations

import logging
import time
from typing import Callable, TypeVar

logger = logging.getLogger(__name__)

RETRY_ATTEMPTS = 3
RETRY_BACKOFF_SECONDS = 0.5

T = TypeVar("T")

# Substrings that mean "try again", not "this is broken".
_TRANSIENT = (
    "UNAVAILABLE",
    "503",
    "DNS",
    "deadline",
    "DEADLINE_EXCEEDED",
    "connection reset",
    "temporarily",
    "INTERNAL",
    "500",
)


def is_transient(exc: Exception) -> bool:
    text = str(exc)
    return any(token.lower() in text.lower() for token in _TRANSIENT)


def call_with_retry(operation: Callable[[], T], *, what: str) -> T:
    """Run a Speech RPC, riding out transient failures."""
    last: Exception | None = None
    for attempt in range(RETRY_ATTEMPTS):
        try:
            return operation()
        except Exception as exc:
            last = exc
            if not is_transient(exc) or attempt == RETRY_ATTEMPTS - 1:
                break
            delay = RETRY_BACKOFF_SECONDS * (2**attempt)
            logger.warning(
                "%s hit a transient error (attempt %d/%d): %s — retrying in %.1fs",
                what, attempt + 1, RETRY_ATTEMPTS, type(exc).__name__, delay,
            )
            time.sleep(delay)

    assert last is not None
    logger.error("%s failed: %s: %s", what, type(last).__name__, last)
    raise last
