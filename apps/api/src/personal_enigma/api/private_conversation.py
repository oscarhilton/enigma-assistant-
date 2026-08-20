"""Deterministic My Enigma conversation — calendar READ + SUPPORT (P03)."""

from __future__ import annotations

import re
from enum import StrEnum
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
from personal_enigma.api.private_calendar_read import (
    infer_private_calendar_period,
    is_private_agenda_list_request,
)
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

# Patterns that signal the query is about the private calendar/world.
_CALENDAR_SUBJECT_RE = re.compile(
    r"\b(calendar|schedule|agenda|event|meeting|appointment|standup|free|available|availability"
    r"|doing|coming up|what'?s? on|on my|this week|next week|this weekend|tomorrow|today)\b",
    re.IGNORECASE,
)

# General-knowledge patterns: self-contained factual queries unrelated to private world.
_GENERAL_KNOWLEDGE_RE = re.compile(
    r"\b(capital of|who (?:is|was)|what is (?:the )?(?:capital|currency|population|language)"
    r"|how (?:tall|far|old|long|many|much)|when (?:was|did|is)|where is|"
    r"define |meaning of|who invented|what does .{1,40} mean)\b",
    re.IGNORECASE,
)

# Elliptical referents: turns that clearly lack a subject the prior context fills.
# These are bare horizon / follow-up words with no own domain.
_ELLIPTICAL_RE = re.compile(
    r"^(what about|and(?: after that)?|how about|"
    r"(?:this|next)\s+week\??|tomorrow\??|this\s+weekend\??|next\s+week\??)$",
    re.IGNORECASE,
)

# Phatic / affirmational / social surface patterns — no private-world referent.
# Matches non-question, non-domain utterances: confirmations, filler, enthusiasm, small talk.
_CONVERSATIONAL_RE = re.compile(
    r"^(?:"
    # Affirmations and agreements
    r"yep|yup|yeah|yes|nope|nah|no|ok|okay|k|sure|alright|alright then|right|cool|got it|"
    r"sounds good|sounds great|makes sense|perfect|great|awesome|nice|good|"
    # Social / phatic expressions
    r"thanks?|thank you|cheers|no worries|no problem|np|"
    r"lol|haha|heh|wow|oh|ah|hmm|hm|uh|"
    # Excitement / enthusiasm without domain
    r"im so ready(?: for you)?|i(?:'m| am) so ready(?: for you)?|"
    r"(?:so\s+)?ready(?: for(?: you)?)?|"
    r"let'?s(?: go)?|let us go|"
    r"i(?:'m| am) (?:here|back|ready|set|good|all set)|"
    r"(?:all\s+)?set(?: and ready)?|"
    r"(?:i(?:'m| am) )?pumped|(?:i(?:'m| am) )?excited|"
    # Filler
    r"you there\??|you good\??|still there\??|hello\??|hey\??|hi\??"
    r")[\s!.?,]*$",
    re.IGNORECASE,
)


class TurnSemanticKind(StrEnum):
    SELF_CONTAINED = "self_contained"  # has own domain — calendar Q, GK, task
    ELLIPTICAL = "elliptical"          # missing subject; prior context fills it
    CONVERSATIONAL = "conversational"  # phatic/affirmational; no private referent


def _turn_semantic_completeness(
    text: str,
    context: ConversationContext,
) -> TurnSemanticKind:
    """Classify the current turn's semantic completeness.

    SELF_CONTAINED: the turn has its own domain semantics — calendar query, GK, task.
    ELLIPTICAL: the turn is incomplete and prior context supplies the missing subject.
    CONVERSATIONAL: phatic, affirmational, or social — no private-world referent needed.

    Only ELLIPTICAL turns may inherit a private planner from context.
    """
    # A turn with explicit calendar/private-world domain is self-contained.
    if infer_private_calendar_period(text) is not None:
        return TurnSemanticKind.SELF_CONTAINED
    if is_private_agenda_list_request(text):
        return TurnSemanticKind.SELF_CONTAINED
    if bool(_CALENDAR_SUBJECT_RE.search(text)):
        return TurnSemanticKind.SELF_CONTAINED
    if bool(_GENERAL_KNOWLEDGE_RE.search(text)):
        return TurnSemanticKind.SELF_CONTAINED

    # Check intent router — known domain intents are self-contained.
    resolved = resolve_intent(text)
    self_contained_kinds = {
        ConversationIntentKind.ATTENTION_QUERY,
        ConversationIntentKind.NEXT_ACTION_QUERY,
        ConversationIntentKind.AVAILABILITY_QUERY,
        ConversationIntentKind.DURATION_QUERY,
        ConversationIntentKind.TIME_FIT_QUERY,
        ConversationIntentKind.CHANGES_QUERY,
        ConversationIntentKind.WAITING_ON_QUERY,
        ConversationIntentKind.CAN_WAIT_QUERY,
        ConversationIntentKind.HELP_QUERY,
        ConversationIntentKind.CAPABILITIES_QUERY,
        ConversationIntentKind.UNSUPPORTED_WORLD_QUERY,
    }
    if resolved.kind in self_contained_kinds:
        return TurnSemanticKind.SELF_CONTAINED

    # Phatic / conversational with no domain referent.
    if bool(_CONVERSATIONAL_RE.match(text.strip())):
        return TurnSemanticKind.CONVERSATIONAL

    # Bare elliptical follow-ups that rely on prior context for their subject.
    normalized = text.strip().lower().rstrip("?! .")
    if bool(_ELLIPTICAL_RE.match(normalized)):
        # Only ELLIPTICAL when prior context actually provides a referent.
        if context.temporal_constraint is not None:
            return TurnSemanticKind.ELLIPTICAL
        # No prior referent to fill — fall through to conversational.
        return TurnSemanticKind.CONVERSATIONAL

    # UNKNOWN intent with no calendar markers and no phatic pattern:
    # treat as conversational rather than manufacturing a private-world need.
    if resolved.kind == ConversationIntentKind.UNKNOWN:
        return TurnSemanticKind.CONVERSATIONAL

    return TurnSemanticKind.SELF_CONTAINED


def _is_general_knowledge(text: str) -> bool:
    """True when the utterance is clearly self-contained general/factual knowledge.

    This is a privacy invariant fence: explicit general-knowledge queries must
    not inherit a private-world frame and trigger private calendar retrieval.
    """
    return bool(_GENERAL_KNOWLEDGE_RE.search(text)) and not bool(
        _CALENDAR_SUBJECT_RE.search(text)
    )


def _is_calendar_related(text: str) -> bool:
    """True when the query plausibly refers to the calendar/private world."""
    if infer_private_calendar_period(text) is not None:
        return True
    if is_private_agenda_list_request(text):
        return True
    return bool(_CALENDAR_SUBJECT_RE.search(text))


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
    period = infer_private_calendar_period(text)
    # Only inherit temporal context when the current query is calendar-related.
    # Explicit current-turn period always wins; inheritance fills gaps only.
    if period is None and _is_calendar_related(text):
        period = context.temporal_constraint
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
    if is_private_agenda_list_request(text):
        return "agenda.get", {"period": "this_week"}
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

    # GRAVITY_01: Greetings are phatic — no private-world entry.
    resolved_up_front = resolve_intent(text)
    if resolved_up_front.kind == ConversationIntentKind.GREETING:
        greeting_items: list[dict[str, Any]] = [
            {
                "kind": "enigma_message",
                "text": "Hey! Ask me what's on your calendar or what needs your attention.",
                "at": at,
                "correlation_id": corr,
            }
        ]
        trace = build_intent_router_trace(
            user_message=text,
            conversation_state={"authority_ceiling": "READ_SUPPORT"},
            last_intent=ctx.last_intent,
            turn_items=greeting_items,
            correlation_id=corr,
        )
        trace = trace.model_copy(
            update={
                "path": "intent_router",
                "planner": "conversation",
                "tools_available": [],
                "executed_tool_request": [],
                "tool_results": [],
            }
        )
        trace_payload = trace.model_dump(mode="json")
        _attach_trace(greeting_items, trace_payload)
        conversation.extend(greeting_items)
        update_context_from_turn_items(ctx, greeting_items)
        return {
            "items": greeting_items,
            "conversation": {"items": list(conversation)},
            "llm_trace": trace_payload,
        }

    # PRIVACY_01 / GRAVITY_03: General-knowledge queries must not enter private retrieval.
    if _is_general_knowledge(text):
        gk_items: list[dict[str, Any]] = [
            {
                "kind": "enigma_message",
                "text": "I don't have general knowledge — try a search engine for that.",
                "at": at,
                "correlation_id": corr,
            }
        ]
        trace = build_intent_router_trace(
            user_message=text,
            conversation_state={"authority_ceiling": "READ_SUPPORT"},
            last_intent=ctx.last_intent,
            turn_items=gk_items,
            correlation_id=corr,
        )
        trace = trace.model_copy(
            update={
                "path": "intent_router",
                "planner": "general_knowledge_ejected",
                "tools_available": [],
                "executed_tool_request": [],
                "tool_results": [],
            }
        )
        trace_payload = trace.model_dump(mode="json")
        _attach_trace(gk_items, trace_payload)
        conversation.extend(gk_items)
        update_context_from_turn_items(ctx, gk_items)
        return {
            "items": gk_items,
            "conversation": {"items": list(conversation)},
            "llm_trace": trace_payload,
        }

    # Semantic inheritance gate — the key invariant:
    #   SELF_CONTAINED → use its own domain (handled above or below)
    #   ELLIPTICAL     → may inherit a private planner from context
    #   CONVERSATIONAL → CONVERSATION_ONLY, no private retrieval
    semantic_kind = _turn_semantic_completeness(text, ctx)
    if semantic_kind == TurnSemanticKind.CONVERSATIONAL:
        conv_items: list[dict[str, Any]] = [
            {
                "kind": "enigma_message",
                "text": "I'm here — ask me what's on your calendar or what needs your attention.",
                "at": at,
                "correlation_id": corr,
            }
        ]
        trace = build_intent_router_trace(
            user_message=text,
            conversation_state={"authority_ceiling": "READ_SUPPORT"},
            last_intent=ctx.last_intent,
            turn_items=conv_items,
            correlation_id=corr,
        )
        trace = trace.model_copy(
            update={
                "path": "intent_router",
                "planner": "conversation",
                "tools_available": [],
                "executed_tool_request": [],
                "tool_results": [],
            }
        )
        trace_payload = trace.model_dump(mode="json")
        _attach_trace(conv_items, trace_payload)
        conversation.extend(conv_items)
        update_context_from_turn_items(ctx, conv_items)
        return {
            "items": conv_items,
            "conversation": {"items": list(conversation)},
            "llm_trace": trace_payload,
        }

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
