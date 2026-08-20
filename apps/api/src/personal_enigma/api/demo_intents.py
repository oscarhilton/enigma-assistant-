"""Deterministic Demo conversation intents — world state in, structured turns out.

C05 intents never consult chat history. C07 ``help`` resolves "that" from the last
structured item Enigma presented (attention_item / next_action / attention_summary),
never by searching free-text chat.
"""

from __future__ import annotations

from datetime import UTC, datetime
from typing import Any, Literal

from personal_enigma.api.conversation_context import (
    ConversationContext,
    estimated_minutes_for_action,
    pick_alternate_next_action,
    resolve_referent,
)
from personal_enigma.api.demo_assist import (
    AssistPlan,
    assist_proposal_item,
    make_assist_plan,
    resolve_assist_target,
)
from personal_enigma.api.demo_availability import (
    build_availability_turn,
    calendar_events_in_period,
    format_time_fit_message,
    period_bounds,
)
from personal_enigma.api.intent_router import (
    ConversationIntentKind,
    TimeExpression,
    normalize_utterance,
    resolve_intent,
)
from personal_enigma.attention.projection import AttentionItemView, AttentionState, NextActionView

IntentName = Literal["needs_me", "why", "changed", "waiting", "can_wait", "next", "help"]

_GREETINGS = frozenset({"hey", "hi", "hello"})

_INTENT_TO_LEGACY: dict[ConversationIntentKind, IntentName] = {
    ConversationIntentKind.ATTENTION_QUERY: "needs_me",
    ConversationIntentKind.NEXT_ACTION_QUERY: "next",
    ConversationIntentKind.CHANGES_QUERY: "changed",
    ConversationIntentKind.WAITING_ON_QUERY: "waiting",
    ConversationIntentKind.CAN_WAIT_QUERY: "can_wait",
    ConversationIntentKind.WHY_QUERY: "why",
    ConversationIntentKind.HELP_QUERY: "help",
}


def match_intent(text: str) -> IntentName | None:
    resolved = resolve_intent(text)
    if resolved.kind == ConversationIntentKind.GREETING:
        return None
    if resolved.kind == ConversationIntentKind.UNKNOWN:
        return None
    if resolved.kind == ConversationIntentKind.AVAILABILITY_QUERY:
        return None
    return _INTENT_TO_LEGACY.get(resolved.kind)


def _attention_item(item: AttentionItemView, at: str) -> dict[str, Any]:
    return {"kind": "attention_item", "at": at, "item": item.model_dump(mode="json")}


def _next_action_item(action: NextActionView, at: str) -> dict[str, Any]:
    return {"kind": "next_action", "at": at, "action": action.model_dump(mode="json")}


def _enigma_message(text: str, at: str) -> dict[str, Any]:
    return {"kind": "enigma_message", "text": text, "at": at}


def next_action_source_ids(state: AttentionState) -> set[str]:
    return {row.source_candidate_id for row in state.next_actions if row.source_candidate_id}


def waiting_items(state: AttentionState) -> list[AttentionItemView]:
    """Context items that are not support-layer next actions (blockers / not unblocked)."""
    next_sources = next_action_source_ids(state)
    return [item for item in state.context if item.id not in next_sources]


def deferred_context_items(state: AttentionState) -> list[AttentionItemView]:
    """Context that is not a next action — reassurance, not WORTH DOING."""
    return waiting_items(state)


def suppressed_titles(state: AttentionState) -> list[str]:
    summary = state.can_wait_summary
    if summary is None:
        return []
    seen: set[str] = set()
    titles: list[str] = []
    for title in summary.sample_titles:
        if title and title not in seen:
            seen.add(title)
            titles.append(title)
    return titles


def _bucket_index(state: AttentionState) -> dict[str, tuple[str, AttentionItemView]]:
    index: dict[str, tuple[str, AttentionItemView]] = {}
    for item in state.needs_you:
        index[item.id] = ("needs_you", item)
    for item in state.context:
        index[item.id] = ("context", item)
    return index


def changed_attention_items(
    current: AttentionState,
    prior: AttentionState,
) -> list[AttentionItemView]:
    """Items whose needs_you / context membership changed. Current state wins."""
    prior_index = _bucket_index(prior)
    current_index = _bucket_index(current)
    changed: list[AttentionItemView] = []
    seen: set[str] = set()
    for item_id, (bucket, item) in current_index.items():
        previous = prior_index.get(item_id)
        if previous is None or previous[0] != bucket:
            changed.append(item)
            seen.add(item_id)
    for item_id, (_bucket, item) in prior_index.items():
        if item_id not in current_index and item_id not in seen:
            changed.append(item)
    return changed


def changed_next_actions(
    current: AttentionState,
    prior: AttentionState,
) -> list[NextActionView]:
    prior_ids = {row.id for row in prior.next_actions}
    return [row for row in current.next_actions if row.id not in prior_ids]


def format_attention_summary_text(state: AttentionState) -> str:
    """Human summary copy — never the kind name ``attention_summary``."""
    count = state.presentation.chat_opening_count
    if count == 0:
        opening = "Nothing needs you."
    elif count == 1:
        opening = "One thing needs you."
    else:
        opening = f"{count} things need you."
    if count == 0 and state.next_actions:
        title = state.next_actions[0].title
        return f"{opening} A good thing you could do: {title}."
    return opening


def build_needs_me_turn(state: AttentionState, at: str) -> list[dict[str, Any]]:
    return [
        {
            "kind": "attention_summary",
            "at": at,
            "state": state.model_dump(mode="json"),
            "text": format_attention_summary_text(state),
        }
    ]


_COUNT_WORDS = {1: "one", 2: "two", 3: "three", 4: "four", 5: "five"}
_HORIZON_LABELS: dict[str, str] = {
    "today": "today",
    "later_today": "later today",
    "this_afternoon": "this afternoon",
    "this_evening": "this evening",
    "tomorrow": "tomorrow",
    "after_tomorrow": "the day after tomorrow",
    "this_week": "this week",
    "next_week": "next week",
}
_HORIZON_INCLUDES_NOW = frozenset(
    {
        "today",
        "later_today",
        "this_afternoon",
        "this_evening",
        "this_week",
    }
)


def _count_word(n: int) -> str:
    return _COUNT_WORDS.get(n, str(n))


def _radar_items(state: AttentionState) -> list[AttentionItemView]:
    coalesced = next_action_source_ids(state)
    return [item for item in state.context if item.id not in coalesced]


def format_cardinality_note(
    actions: list[NextActionView],
    radar: list[AttentionItemView],
    requested_count: int,
    horizon_label: str,
) -> str | None:
    """Requested N is a presentation preference — never pad the support layer."""
    strong_count = len(actions)
    if requested_count <= strong_count:
        return None
    if strong_count == 1:
        lead = (
            f"I only have one strong next action for {horizon_label}: "
            f"{actions[0].title}."
        )
    elif strong_count == 0:
        lead = (
            f"I don't have {_count_word(requested_count)} strong next actions "
            f"for {horizon_label}."
        )
    else:
        lead = (
            f"I only have {_count_word(strong_count)} strong next actions for "
            f"{horizon_label}, not {_count_word(requested_count)}."
        )
    if radar:
        radar_phrase = " / ".join(item.title for item in radar)
        pronoun = "them" if len(radar) != 1 else "it"
        return (
            f"{lead} Also keeping {radar_phrase} on radar, but I wouldn't "
            f"promote {pronoun} to make up {_count_word(requested_count)}."
        )
    return f"{lead} I wouldn't invent extras to make up {_count_word(requested_count)}."


def build_priorities_turn(
    state: AttentionState,
    at: str,
    *,
    requested_count: int,
) -> list[dict[str, Any]]:
    """Top-N query — acknowledge the requested count without inventing next actions."""
    note = format_cardinality_note(
        list(state.next_actions),
        _radar_items(state),
        requested_count,
        "today",
    )
    turn: list[dict[str, Any]] = []
    if note:
        turn.append(_enigma_message(note, at))
    turn.extend(build_needs_me_turn(state, at))
    return turn


def _parse_at(at: str) -> datetime:
    reference = datetime.fromisoformat(at.replace("Z", "+00:00"))
    if reference.tzinfo is None:
        return reference.replace(tzinfo=UTC)
    return reference.astimezone(UTC)


def build_attention_horizon_turn(
    state: AttentionState,
    *,
    checkpoint_id: str,
    at: str,
    period: TimeExpression,
    requested_count: int | None = None,
) -> list[dict[str, Any]]:
    """Re-query world over a horizon. Do not extrapolate the previous answer."""
    period_key = period.value
    label = _HORIZON_LABELS.get(period_key, period_key.replace("_", " "))
    reference = _parse_at(at)
    start, end = period_bounds(reference, period_key)
    events = calendar_events_in_period(checkpoint_id, start, end)
    cal_ids = {row["evidence_id"] for row in events}
    includes_now = period_key in _HORIZON_INCLUDES_NOW
    coalesced = next_action_source_ids(state)

    needs = [
        item
        for item in state.needs_you
        if includes_now or set(item.evidence_ids) & cal_ids
    ]
    radar = [
        item
        for item in state.context
        if item.id not in coalesced and set(item.evidence_ids) & cal_ids
    ]
    actions = list(state.next_actions) if includes_now else []

    parts: list[str] = []
    if not needs:
        if radar:
            parts.append("Nothing needs your attention right now.")
        else:
            parts.append(f"Nothing needs you {label} as an interrupt.")
    else:
        titles = "; ".join(item.title for item in needs)
        parts.append(f"Needs you {label}: {titles}.")

    cardinality = None
    if requested_count is not None:
        cardinality = format_cardinality_note(actions, radar, requested_count, label)
    if cardinality:
        parts.append(cardinality)
    elif actions:
        if len(actions) == 1:
            parts.append(f"Strong next action: {actions[0].title}.")
        else:
            joined = "; ".join(action.title for action in actions)
            parts.append(f"Strong next actions: {joined}.")

    if radar:
        radar_phrase = " / ".join(item.title for item in radar)
        if not needs:
            parts.append(f"Looking ahead {label}: {radar_phrase}.")
        else:
            parts.append(f"On radar {label}: {radar_phrase}.")

    if events:
        cal_bits: list[str] = []
        for event in events:
            start_at = _parse_at(event["start_at"])
            end_at = _parse_at(event["end_at"])
            day = start_at.strftime("%A")
            cal_bits.append(
                f"{day} has {event['title']}, "
                f"{start_at.strftime('%H:%M')}–{end_at.strftime('%H:%M')}"
            )
        parts.append("Calendar: " + "; ".join(cal_bits) + ".")
    else:
        parts.append(f"I don't see anything on the calendar {label}.")

    turn: list[dict[str, Any]] = [_enigma_message(" ".join(parts), at)]
    turn.extend(_next_action_item(action, at) for action in actions)
    turn.extend(_attention_item(item, at) for item in (*needs, *radar))
    return turn


def build_why_turn(state: AttentionState, at: str) -> list[dict[str, Any]]:
    target = state.needs_you[0] if state.needs_you else (
        state.context[0] if state.context else None
    )
    if target is None:
        return [_enigma_message("I do not have a specific item to explain yet.", at)]
    return [_attention_item(target, at)]


_SUPPORT_OPTIONS: tuple[str, ...] = (
    "talk through what needs deciding",
    "make it smaller",
    "figure out the first step",
    "or I can prepare something if you ask me to",
)


def build_support_payload(
    state: AttentionState,
    context: ConversationContext,
) -> dict[str, Any]:
    """SUPPORT payload — discuss / explain / break down / first step. Not Assist."""
    action, title = resolve_referent(state, context)
    item_id = action.source_candidate_id if action is not None else context.current_subject_id
    item: AttentionItemView | None = None
    if item_id:
        for candidate in (*state.needs_you, *state.context):
            if candidate.id == item_id:
                item = candidate
                break
    display_title = (item.title if item is not None else title) or "this"
    why = ""
    if item is not None and item.explanation:
        why = item.explanation
    elif action is not None:
        why = action.reason
    first_step = "Name the smallest next move."
    estimated: int | None = None
    if action is not None:
        first_step = action.reason or action.title
        estimated = estimated_minutes_for_action(action)
    return {
        "title": display_title,
        "why_it_matters": why,
        "first_step": first_step,
        "estimated_minutes": estimated,
        "support_options": list(_SUPPORT_OPTIONS),
        "assist_offered": False,
        "subject_id": item_id,
    }


def support_message(payload: dict[str, Any]) -> str:
    """Talk through the problem. Never skip to a proposal card."""
    title = str(payload.get("title") or "this")
    why = str(payload.get("why_it_matters") or "").strip()
    first = str(payload.get("first_step") or "name the smallest next move")
    minutes = payload.get("estimated_minutes")
    why_clause = f" It's showing up because {why}." if why else ""
    duration = f" About {minutes} minutes." if isinstance(minutes, int) else ""
    return (
        f"Let's talk through {title}.{why_clause} "
        f"A useful first step is {first}.{duration} "
        "We can break it down, make it smaller, or I can prepare something if you ask — "
        "I'm not going to start it unless you want that."
    )


def build_explain_referent_turn(
    state: AttentionState,
    context: ConversationContext,
    at: str,
    *,
    recover: bool = False,
) -> list[dict[str, Any]]:
    """Explain the conversation referent — not the first context item (C09).

    SUPPORT copy talks through the problem. It is not an Assist card.
    """
    action, title = resolve_referent(state, context)
    item_id = action.source_candidate_id if action is not None else context.current_subject_id
    if not item_id:
        return [_enigma_message("I'm not sure what you're referring to.", at)]
    payload = build_support_payload(state, context)
    for item in (*state.needs_you, *state.context):
        if item.id == item_id:
            if recover:
                return [
                    _enigma_message(
                        "You're right — I switched tasks. You were asking about "
                        f"{title or item.title}. It's showing up because it became "
                        "unblocked and is a good optional next action, not because "
                        "it's urgent.",
                        at,
                    ),
                    _attention_item(item, at),
                ]
            return [
                _enigma_message(support_message(payload), at),
                _attention_item(item, at),
            ]
    return [_enigma_message(f"I don't have an explanation for {title or item_id}.", at)]


def build_changed_turn(
    current: AttentionState,
    prior: AttentionState | None,
    at: str,
) -> list[dict[str, Any]]:
    if prior is None:
        return [_enigma_message("Nothing has changed — the world just loaded.", at)]
    items = changed_attention_items(current, prior)
    actions = changed_next_actions(current, prior)
    if not items and not actions:
        return [_enigma_message("Nothing has changed.", at)]
    turn: list[dict[str, Any]] = [_attention_item(item, at) for item in items]
    turn.extend(_next_action_item(action, at) for action in actions)
    return turn


def build_waiting_turn(state: AttentionState, at: str) -> list[dict[str, Any]]:
    items = waiting_items(state)
    if not items:
        return [_enigma_message("You're not waiting on anything.", at)]
    return [_attention_item(item, at) for item in items]


def build_can_wait_turn(state: AttentionState, at: str) -> list[dict[str, Any]]:
    deferred = deferred_context_items(state)
    held = suppressed_titles(state)
    turn: list[dict[str, Any]] = [_attention_item(item, at) for item in deferred]
    if held:
        if len(held) == 1:
            text = f"{held[0]} can wait."
        else:
            text = "These can wait: " + "; ".join(held) + "."
        turn.append(_enigma_message(text, at))
    if not turn:
        return [_enigma_message("Nothing in particular needs to wait.", at)]
    return turn


def build_next_turn(state: AttentionState, at: str) -> list[dict[str, Any]]:
    if not state.next_actions:
        # Absence of a recommendation is not evidence of absence of activity.
        return [_enigma_message("Nothing stands out as a strong next action.", at)]
    return [_next_action_item(action, at) for action in state.next_actions]


_REJECT_ACKNOWLEDGEMENTS = ("Fair enough.", "Sure.")


def build_reject_next_turn(
    state: AttentionState,
    context: ConversationContext,
    at: str,
) -> list[dict[str, Any]]:
    """Session-only rejection — suppress current next action, no world mutation."""
    del state  # world state unchanged
    action_id = context.current_next_action_id
    if action_id:
        context.suppress_next_action(action_id)
    ack = _REJECT_ACKNOWLEDGEMENTS[0]
    return [_enigma_message(ack, at)]


def build_alternate_task_turn(
    state: AttentionState,
    context: ConversationContext,
    at: str,
) -> list[dict[str, Any]]:
    suppressed = set(context.suppressed_next_action_ids)
    alternate = pick_alternate_next_action(state, suppressed)
    if alternate is None:
        return [_enigma_message("Nothing else comes to mind right now.", at)]
    return [_next_action_item(alternate, at)]


def build_duration_turn(
    state: AttentionState,
    context: ConversationContext,
    at: str,
) -> list[dict[str, Any]]:
    action, title = resolve_referent(state, context)
    if action is None or title is None:
        return [_enigma_message("I'm not sure what you're referring to.", at)]
    minutes = estimated_minutes_for_action(action)
    if minutes is None:
        return [_enigma_message(f"I don't have a time estimate for {title}.", at)]
    return [_enigma_message(f"{title} should take around {minutes} minutes.", at)]


def build_time_fit_turn(
    state: AttentionState,
    context: ConversationContext,
    *,
    checkpoint_id: str,
    at: str,
) -> list[dict[str, Any]]:
    from datetime import UTC, datetime

    action, title = resolve_referent(state, context)
    if action is None:
        return [_enigma_message("I'm not sure what you're referring to.", at)]
    minutes = estimated_minutes_for_action(action)
    if minutes is None:
        return [_enigma_message(f"I don't have a time estimate for {title}.", at)]
    reference = datetime.fromisoformat(at.replace("Z", "+00:00"))
    if reference.tzinfo is None:
        reference = reference.replace(tzinfo=UTC)
    text = format_time_fit_message(
        state=state,
        checkpoint_id=checkpoint_id,
        reference=reference,
        task_minutes=minutes,
        task_title=title,
    )
    return [_enigma_message(text, at)]


def match_greeting(text: str) -> bool:
    return normalize_utterance(text) in _GREETINGS


def build_greeting_turn(at: str) -> list[dict[str, Any]]:
    return [_enigma_message("Hey. What's up?", at)]


def build_acknowledgment_turn(at: str) -> list[dict[str, Any]]:
    return [_enigma_message("I hear you.", at)]


def build_unsupported_world_turn(at: str, text: str = "") -> list[dict[str, Any]]:
    normalized = normalize_utterance(text)
    if "weather" in normalized:
        return [
            _enigma_message(
                "I don't have a weather source, so I can't tell you what it's like outside.",
                at,
            )
        ]
    if "key" in normalized:
        return [_enigma_message("I don't know.", at)]
    return [_enigma_message("I don't know.", at)]


_DEMO_CAPABILITIES_TEXT = (
    "In this demo I can help with what's on your attention — urgent items, next actions, "
    "calendar availability, what changed, and what you're waiting on. "
    "I don't have general knowledge or live sources like weather."
)


def build_capabilities_turn(at: str) -> list[dict[str, Any]]:
    return [_enigma_message(_DEMO_CAPABILITIES_TEXT, at)]


def build_unknown_turn(at: str, text: str = "") -> list[dict[str, Any]]:
    if "key" in normalize_utterance(text):
        return [_enigma_message("I don't know.", at)]
    return [_enigma_message("I'm not sure I follow.", at)]


def build_help_turn(
    state: AttentionState,
    conversation: list[dict[str, Any]],
    at: str,
    *,
    completed_item_ids: set[str] | None = None,
) -> tuple[list[dict[str, Any]], AssistPlan | None]:
    """Structured Assist proposal for the current 'that'. Never auto-executes."""
    done = completed_item_ids or set()
    target = resolve_assist_target(state, conversation, done)
    if target is None:
        return (
            [_enigma_message("There's nothing for me to help with right now.", at)],
            None,
        )
    plan = make_assist_plan(target)
    return [assist_proposal_item(plan, at)], plan


def build_intent_turn(
    text: str,
    state: AttentionState,
    *,
    at: str,
    checkpoint_id: str | None = None,
    prior_state: AttentionState | None = None,
    conversation: list[dict[str, Any]] | None = None,
    completed_item_ids: set[str] | None = None,
    conversation_context: ConversationContext | None = None,
) -> tuple[list[dict[str, Any]], AssistPlan | None]:
    ctx = conversation_context or ConversationContext()
    resolved = ctx.compose_intent(text)
    kind = resolved.kind
    if kind == ConversationIntentKind.ATTENTION_QUERY:
        if resolved.period is not None:
            return (
                build_attention_horizon_turn(
                    state,
                    checkpoint_id=checkpoint_id or state.checkpoint_id or "",
                    at=at,
                    period=resolved.period,
                    requested_count=resolved.requested_count,
                ),
                None,
            )
        if resolved.requested_count is not None:
            return (
                build_priorities_turn(
                    state,
                    at,
                    requested_count=resolved.requested_count,
                ),
                None,
            )
        return build_needs_me_turn(state, at), None
    if kind == ConversationIntentKind.WHY_QUERY:
        return build_why_turn(state, at), None
    if kind == ConversationIntentKind.CHANGES_QUERY:
        return build_changed_turn(state, prior_state, at), None
    if kind == ConversationIntentKind.WAITING_ON_QUERY:
        return build_waiting_turn(state, at), None
    if kind == ConversationIntentKind.CAN_WAIT_QUERY:
        return build_can_wait_turn(state, at), None
    if kind == ConversationIntentKind.NEXT_ACTION_QUERY:
        if resolved.period is not None:
            return (
                build_attention_horizon_turn(
                    state,
                    checkpoint_id=checkpoint_id or state.checkpoint_id or "",
                    at=at,
                    period=resolved.period,
                    requested_count=resolved.requested_count,
                ),
                None,
            )
        return build_next_turn(state, at), None
    if kind == ConversationIntentKind.REJECT_NEXT_ACTION:
        return build_reject_next_turn(state, ctx, at), None
    if kind == ConversationIntentKind.ALTERNATE_TASK_QUERY:
        return build_alternate_task_turn(state, ctx, at), None
    if kind == ConversationIntentKind.DURATION_QUERY:
        return build_duration_turn(state, ctx, at), None
    if kind == ConversationIntentKind.TIME_FIT_QUERY:
        return (
            build_time_fit_turn(
                state,
                ctx,
                checkpoint_id=checkpoint_id or state.checkpoint_id or "",
                at=at,
            ),
            None,
        )
    if kind == ConversationIntentKind.AVAILABILITY_QUERY:
        return (
            build_availability_turn(
                state,
                checkpoint_id=checkpoint_id or state.checkpoint_id or "",
                at=at,
                period=resolved.period.value if resolved.period else None,
            ),
            None,
        )
    if kind == ConversationIntentKind.HELP_QUERY:
        return build_help_turn(
            state,
            conversation or [],
            at,
            completed_item_ids=completed_item_ids,
        )
    if kind == ConversationIntentKind.GREETING:
        return build_greeting_turn(at), None
    if kind == ConversationIntentKind.ACKNOWLEDGMENT:
        return build_acknowledgment_turn(at), None
    if kind == ConversationIntentKind.UNSUPPORTED_WORLD_QUERY:
        return build_unsupported_world_turn(at, text), None
    if kind == ConversationIntentKind.CAPABILITIES_QUERY:
        return build_capabilities_turn(at), None
    return build_unknown_turn(at, text), None


__all__ = [
    "IntentName",
    "build_alternate_task_turn",
    "build_attention_horizon_turn",
    "build_duration_turn",
    "build_explain_referent_turn",
    "build_support_payload",
    "support_message",
    "build_help_turn",
    "build_intent_turn",
    "build_priorities_turn",
    "format_cardinality_note",
    "build_reject_next_turn",
    "build_time_fit_turn",
    "changed_attention_items",
    "changed_next_actions",
    "deferred_context_items",
    "build_acknowledgment_turn",
    "build_capabilities_turn",
    "build_greeting_turn",
    "build_unsupported_world_turn",
    "match_greeting",
    "match_intent",
    "next_action_source_ids",
    "normalize_utterance",
    "resolve_intent",
    "suppressed_titles",
    "waiting_items",
]
