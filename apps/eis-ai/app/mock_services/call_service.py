"""Mock call / support-request dispatcher.

Stands in for the school ERP's real notification system. It can fail, and when it
fails the assistant is required to say so rather than claim someone was contacted
(assessment §3, Implementation Guidelines §11.4).
"""
from __future__ import annotations

import random
from dataclasses import dataclass

# Flipped by tests and by the demo script to exercise the failure path.
FORCE_FAILURE = False
FAILURE_RATE = 0.0


@dataclass(frozen=True)
class DispatchResult:
    ok: bool
    ticket_ref: str | None = None
    error: str | None = None


def dispatch_call_request(*, target_role: str, target_name: str, reference: str) -> DispatchResult:
    if FORCE_FAILURE or (FAILURE_RATE and random.random() < FAILURE_RATE):
        return DispatchResult(ok=False, error="call_service_unavailable")
    prefix = "TCH" if target_role == "teacher" else "MGM"
    return DispatchResult(ok=True, ticket_ref=f"{prefix}-{reference[:8].upper()}")
