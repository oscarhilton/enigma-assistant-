"""Deterministic My Enigma conversation — calendar READ + SUPPORT (P03)."""

from __future__ import annotations

import re
from typing import Any
from uuid import uuid4

from personal_enigma.api.conversation_context import (
    ConversationContext,
    update_context_from_turn_items,
)
from personal_enigma.api.demo_orchestrator import LlmTrace, build_intent_router_trace
from personal_enigma.api.intent_router import (
    ConversationIntentKind,
    resolve_intent,
)
from personal_enigma.api.private_calendar_read import infer_private_calendar_period
from personal_enigma.api.private_tools import (
    PrivateToolSession,
    execute_private_tool,
    private_capability_contract,
)
from personal_enigma.attention.projection import AttentionState, build_presentation_plan

_PREPARE_RE = re.compile(
    r"\b(book it|schedule it|add to calendar|create (?:an )?event|send (?:the )?invite)\b",
    re.IGNORECASE,
)


def _attach_trace(
    turn_items: list[dict[str, Any]], trace_payload: dict[str, Any]
) -> None:
    if not turn_items:
        return
    stamped: dict[str, Any] = dict(turn_items[0])
    stamped["llm_trace"] = trace_payload
    turn_items[0] = stamped


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


def _route_private_tool(text: str, context: ConversationContext) -> tuple[str, dict[str, Any]]:
    period = infer_private_calendar_period(text) or context.temporal_constraint
    hay = text.casefold()
    if period and (_PREPARE_RE.search(text) is None):
        if "free" in hay or "clear" in hay or "available" in hay:
            return "availability.check", {"period": period}
        if (
            "doing" in hay
            or "coming up" in hay
            or "what's on" in hay
            or "whats on" in hay
            or "on my calendar" in hay
            or period in {"tomorrow", "this_weekend"}
            or infer_private_calendar_period(text) is not None
        ):
            return "agenda.get", {"period": period}
    resolved = resolve_intent(text)
    if resolved.kind == ConversationIntentKind.AVAILABILITY_QUERY:
        return "availability.check", {
            "period": resolved.period.value if resolved.period else period
        }
    if resolved.kind == ConversationIntentKind.HELP_QUERY:
        return "world.explain", {}
    if resolved.kind == ConversationIntentKind.ATTENTION_QUERY:
        return "attention.get_current", {}
    if period:
        return "agenda.get", {"period": period}
    return "world.explain", {}


def handle_private_message(
    *,
    text: str,
    at: str,
    adapter: Any,
    conversation: list[dict[str, Any]],
    context: ConversationContext | None = None,
) -> dict[str, Any]:
    """Handle one My Enigma turn without LLM — intent + READ/SUPPORT tools only."""
    ctx = context or ConversationContext()
    corr = f"corr-{uuid4().hex}"
    conversation.append(
        {"kind": "user_message", "text": text, "at": at, "correlation_id": corr}
    )

    if _PREPARE_RE.search(text):
        turn_items = [
            {
                "kind": "enigma_message",
                "text": (
                    "I can read your calendar and help you think through it — "
                    "I can't create or change calendar events yet."
                ),
                "at": at,
                "correlation_id": corr,
            }
        ]
        trace = build_intent_router_trace(
            user_message=text,
            conversation_state={"authority_ceiling": "READ_SUPPORT"},
            last_intent=ctx.last_intent,
            turn_items=turn_items,
            correlation_id=corr,
        )
        trace = trace.model_copy(
            update={
                "path": "intent_router",
                "tools_available": list(private_capability_contract()["allowed"]),
            }
        )
        trace_payload = trace.model_dump(mode="json")
        _attach_trace(turn_items, trace_payload)
        conversation.extend(turn_items)
        update_context_from_turn_items(ctx, turn_items)
        return {
            "items": turn_items,
            "conversation": {"items": list(conversation)},
            "llm_trace": trace.model_dump(mode="json"),
        }

    state = _silence_attention(at)
    tool_name, arguments = _route_private_tool(text, ctx)
    if arguments.get("period"):
        ctx.temporal_constraint = str(arguments["period"])

    session = PrivateToolSession(
        state=state,
        context=ctx,
        at=at,
        adapter=adapter,
        user_message=text,
    )
    result = execute_private_tool(session, tool_name, arguments)
    turn_items = [
        {**item, "correlation_id": corr} if item.get("correlation_id") is None else item
        for item in result.turn_items
    ]

    trace = LlmTrace(
        path="intent_router",
        planner="private_calendar_read",
        user_message=text,
        conversation_state={
            "authority_ceiling": "READ_SUPPORT",
            "capability_contract": private_capability_contract(),
        },
        tools_available=list(private_capability_contract()["allowed"]),
        executed_tool_request=[{"name": tool_name, "arguments": arguments}],
        tool_results=[
            {
                "name": tool_name,
                "ok": result.ok,
                "calendar_items": result.data.get("calendar_items", []),
            }
        ],
        correlation_id=corr,
    )
    trace_payload = trace.model_dump(mode="json")
    _attach_trace(turn_items, trace_payload)

    conversation.extend(turn_items)
    update_context_from_turn_items(ctx, turn_items)
    return {
        "items": turn_items,
        "conversation": {"items": list(conversation)},
        "llm_trace": trace.model_dump(mode="json"),
        "calendar_facts_used": session.last_calendar_facts,
        "context": ctx,
    }


__all__ = ["handle_private_message"]
