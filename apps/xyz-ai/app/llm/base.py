from __future__ import annotations

from abc import ABC, abstractmethod

from app.llm.schema import Classification


class LLMProvider(ABC):
    """What the graph needs from a language model. Two calls, nothing more."""

    name: str = "base"
    is_live: bool = False

    @abstractmethod
    def classify(
        self,
        *,
        message: str,
        role: str,
        history: list[dict],
        today: str,
        roster_hint: list[str] | None = None,
    ) -> Classification: ...

    @abstractmethod
    def respond(
        self,
        *,
        system_prompt: str,
        history: list[dict],
        message: str,
        data_block: str,
    ) -> str: ...
