"""Deterministic My Enigma conversation — calendar READ + SUPPORT (P03)."""

from __future__ import annotations

from typing import Any

from personal_enigma.api.conversation_context import ConversationContext


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
    )
    return {
        "items": result.items,
        "conversation": {"items": list(conversation)},
        "llm_trace": result.llm_trace,
        "calendar_facts_used": result.calendar_facts_used,
        "context": result.context or ctx,
    }


__all__ = [
    "handle_private_message",
]
