"""Assemble the LangGraph pipeline (Implementation Guidelines §6.2).

auth_resolver → language_detector → memory_loader → intent_classifier →
permission_gate → persona_selector → tool_executor → response_formatter →
memory_writer

The order is fixed and linear on purpose: the permission gate cannot be routed
around, because there is no edge that skips it.
"""
from __future__ import annotations

from datetime import date
from functools import lru_cache
from typing import Any

from langgraph.graph import END, START, StateGraph

from app.graph.nodes import (
    auth_resolver,
    intent_classifier,
    language_detector,
    memory_loader,
    memory_writer,
    permission_gate,
    persona_selector,
    response_formatter,
    tool_executor,
)
from app.graph.state import ConversationState, new_state

NODE_ORDER = [
    ("auth_resolver", auth_resolver),
    ("language_detector", language_detector),
    ("memory_loader", memory_loader),
    ("intent_classifier", intent_classifier),
    ("permission_gate", permission_gate),
    ("persona_selector", persona_selector),
    ("tool_executor", tool_executor),
    ("response_formatter", response_formatter),
    ("memory_writer", memory_writer),
]


def build_graph():
    builder = StateGraph(ConversationState)
    for name, fn in NODE_ORDER:
        builder.add_node(name, fn)
    builder.add_edge(START, NODE_ORDER[0][0])
    for (left, _), (right, _) in zip(NODE_ORDER, NODE_ORDER[1:]):
        builder.add_edge(left, right)
    builder.add_edge(NODE_ORDER[-1][0], END)
    return builder.compile()


@lru_cache
def get_graph():
    return build_graph()


def run_turn(
    *,
    db: Any,
    user_id: str,
    session_id: str,
    message: str,
    language: str | None = None,
    today: str | None = None,
) -> ConversationState:
    """One chat turn, start to finish."""
    state = new_state(
        db=db,
        user_id=user_id,
        session_id=session_id,
        message=message,
        language=language,
        today=today or date.today().isoformat(),
    )
    return get_graph().invoke(state)  # type: ignore[return-value]
