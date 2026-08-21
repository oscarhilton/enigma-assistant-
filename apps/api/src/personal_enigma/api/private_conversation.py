"""Deterministic My Enigma conversation — calendar READ + SUPPORT (P03)."""

from __future__ import annotations

import re
from typing import Any

from personal_enigma.api.conversation_context import ConversationContext
from personal_enigma.attention.projection import AttentionState, build_presentation_plan

_PREPARE_RE = re.compile(
    r"\b(book it|schedule it|add to calendar|create (?:an )?event|send (?:the )?invite|"
    r"book\b[^.?!]{0,40}\bcalendar)\b",
    re.IGNORECASE,
)


def _silence_attention(now: str) -> AttentionState:
    return AttentionState(
        simulated_time=now,
        checkpoint_id=None,
        needs_you=[],
        context=[],
        next_actions=[],
        can_wait_summary=None,
        presentation=build_presentation_plan(0),
    )


def handle_private_message(
    *,
    text: str,
    at: str,
    adapter: Any,
    conversation: list[dict[str, Any]],
    context: ConversationContext | None = None,
) -> dict[str, Any]:
    """Handle one My Enigma turn via the shared turn kernel."""
    from personal_enigma.api.turn_kernel import run_private_turn

    ctx = context or ConversationContext()
    result = run_private_turn(
        text=text,
        at=at,
        adapter=adapter,
        conversation=conversation,
        context=ctx,
        silence_attention=_silence_attention,
    )
    return {
        "items": result.items,
        "conversation": {"items": list(conversation)},
        "llm_trace": result.llm_trace,
        "calendar_facts_used": result.calendar_facts_used,
        "context": result.context or ctx,
    }


__all__ = [
    "_silence_attention",
    "handle_private_message",
]
