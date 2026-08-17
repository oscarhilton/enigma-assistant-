"""Demo conversation tools — Enigma core authority, LLM-selectable boundary (C09).

Each tool wraps existing C05–C07 handlers. Tool JSON is authoritative; model prose is not.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import UTC, datetime
from typing import Any, Literal

from pydantic import BaseModel, Field

from personal_enigma.api.conversation_context import (
    ConversationContext,
    estimated_minutes_for_action,
    find_next_action_by_id,
    match_named_referent,
    pick_alternate_next_action,
    reconcile_action_focus,
    referent_candidates,
    resolve_referent,
)
from personal_enigma.api.demo_assist import (
    AssistPlan,
    SyntheticDemoServices,
    apply_verified_assist_effect,
    assist_proposal_item,
    assist_result_item,
    assist_target_from_id,
    execute_and_verify,
    make_assist_plan,
    overlay_session_world,
    resolve_assist_target,
)
from personal_enigma.api.demo_availability import (
    build_availability_turn,
    calendar_events_in_period,
    format_time_fit_message,
    period_bounds,
)
from personal_enigma.api.demo_intents import (
    build_alternate_task_turn,
    build_attention_horizon_turn,
    build_changed_turn,
    build_explain_referent_turn,
    build_needs_me_turn,
    build_next_turn,
    build_reject_next_turn,
    build_waiting_turn,
    waiting_items,
)
from personal_enigma.api.intent_router import TimeExpression
from personal_enigma.attention.projection import AttentionState, NextActionView

ToolName = Literal[
    "attention.get_current",
    "next_action.get",
    "next_action.get_alternatives",
    "next_action.reject",
    "referent.get_duration",
    "availability.check",
    "agenda.get",
    "world.get_changes",
    "world.get_blockers",
    "world.explain",
    "assist.propose",
    "assist.approve",
]

ALLOWED_TOOL_NAMES: frozenset[str] = frozenset(
    (
        "attention.get_current",
        "next_action.get",
        "next_action.get_alternatives",
        "next_action.reject",
        "referent.get_duration",
        "availability.check",
        "agenda.get",
        "world.get_changes",
        "world.get_blockers",
        "world.explain",
        "assist.propose",
        "assist.approve",
    )
)

# Capability fence — not a second tool registry. The model cannot request these.
DENIED_REMOTE_CAPABILITIES: tuple[str, ...] = (
    "gmail.search",
    "gmail.send",
    "arbitrary filesystem",
    "arbitrary network",
)


class AvailabilityCheckInput(BaseModel):
    period: str | None = Field(
        default=None,
        description=(
            "Time window to test occupancy: later_today, this_afternoon, this_evening, "
            "tomorrow, this_week, next_week, this_weekend, friday_night, saturday. "
            "Answers whether the window is free — not what is on it."
        ),
    )
    duration_minutes: int | None = Field(
        default=None,
        description=(
            "When set without period, checks whether the current referent fits later today."
        ),
    )


class AgendaGetInput(BaseModel):
    period: str = Field(
        description=(
            "Horizon whose contents to return: today, this_week, next_week, "
            "this_weekend, later_today, tomorrow, saturday. "
            "Returns calendar events, attention items, and next actions in that period."
        ),
    )


class AssistProposeInput(BaseModel):
    target_id: str | None = Field(
        default=None,
        description=(
            "Attention-item id to propose assist for, from referent_candidates. "
            "Set this when the user names or corrects the subject. Omit only for "
            "implicit 'that' / current_subject — Enigma binds an explicit id "
            "before execution."
        ),
    )


class AssistApproveInput(BaseModel):
    proposal_id: str | None = Field(
        default=None,
        description=(
            "Id of the pending assist proposal. Required at execution. "
            "May be omitted in the model request; Enigma binds "
            "current_assist_proposal_id before executing."
        ),
    )


class WorldExplainInput(BaseModel):
    recover: bool = Field(
        default=False,
        description="When true, acknowledge a prior wrong referent and re-explain the subject.",
    )
    target: str | None = Field(
        default=None,
        description=(
            "Attention-item id to explain, from referent_candidates. "
            "Set this when the user names or corrects the subject "
            "(e.g. 'the token thing') — never invent an id."
        ),
    )


class ToolCallRecord(BaseModel):
    name: ToolName
    arguments: dict[str, Any] = Field(default_factory=dict)


class ToolExecutionResult(BaseModel):
    name: ToolName
    ok: bool = True
    data: dict[str, Any] = Field(default_factory=dict)
    turn_items: list[dict[str, Any]] = Field(default_factory=list)
    assist_plan: dict[str, Any] | None = None


@dataclass
class DemoToolSession:
    """Mutable session slice passed into tool execution."""

    state: AttentionState
    context: ConversationContext
    checkpoint_id: str
    prior_state: AttentionState | None
    at: str
    conversation: list[dict[str, Any]]
    completed_item_ids: set[str] = field(default_factory=set)
    pending_assists: dict[str, AssistPlan] = field(default_factory=dict)
    synthetic_services: SyntheticDemoServices = field(default_factory=SyntheticDemoServices)
    user_message: str = ""
    assist_advances: dict[str, NextActionView] = field(default_factory=dict)


def tool_schemas() -> list[dict[str, Any]]:
    """OpenAI-compatible function schemas for demo conversation tools."""
    return [
        {
            "type": "function",
            "function": {
                "name": "attention.get_current",
                "description": "Current attention projection: needs_you, context, next_actions.",
                "parameters": {"type": "object", "properties": {}, "additionalProperties": False},
            },
        },
        {
            "type": "function",
            "function": {
                "name": "next_action.get",
                "description": "Primary next actions from the support layer.",
                "parameters": {"type": "object", "properties": {}, "additionalProperties": False},
            },
        },
        {
            "type": "function",
            "function": {
                "name": "next_action.get_alternatives",
                "description": (
                    "Alternate next action after rejection — excludes suppressed ids, "
                    "prefers lower-friction context items."
                ),
                "parameters": {"type": "object", "properties": {}, "additionalProperties": False},
            },
        },
        {
            "type": "function",
            "function": {
                "name": "next_action.reject",
                "description": (
                    "Session-only rejection of the current next action (e.g. can't be bothered). "
                    "Does not mutate world state."
                ),
                "parameters": {"type": "object", "properties": {}, "additionalProperties": False},
            },
        },
        {
            "type": "function",
            "function": {
                "name": "referent.get_duration",
                "description": (
                    "Estimated minutes for the conversation referent "
                    "(current_next_action_id or current_attention_item_id)."
                ),
                "parameters": {"type": "object", "properties": {}, "additionalProperties": False},
            },
        },
        {
            "type": "function",
            "function": {
                "name": "availability.check",
                "description": (
                    "Is a calendar window free, or does a referent duration fit later today. "
                    "Occupancy / time-fit only — not a list of what is on the period."
                ),
                "parameters": AvailabilityCheckInput.model_json_schema(),
            },
        },
        {
            "type": "function",
            "function": {
                "name": "agenda.get",
                "description": (
                    "What is on a time horizon: calendar events, attention items, and "
                    "next actions whose evidence falls in the period. Use for week or "
                    "day overviews. Does not invent venues, deadlines, or advice."
                ),
                "parameters": AgendaGetInput.model_json_schema(),
            },
        },
        {
            "type": "function",
            "function": {
                "name": "world.get_changes",
                "description": "Attention and next-action changes vs prior checkpoint.",
                "parameters": {"type": "object", "properties": {}, "additionalProperties": False},
            },
        },
        {
            "type": "function",
            "function": {
                "name": "world.get_blockers",
                "description": "Waiting-on / blocker context items (not unblocked next actions).",
                "parameters": {"type": "object", "properties": {}, "additionalProperties": False},
            },
        },
        {
            "type": "function",
            "function": {
                "name": "world.explain",
                "description": (
                    "Explain why a conversation subject matters — uses "
                    "current_subject_id from structured turns, or an explicit "
                    "target id from referent_candidates when the user corrects the subject."
                ),
                "parameters": WorldExplainInput.model_json_schema(),
            },
        },
        {
            "type": "function",
            "function": {
                "name": "assist.propose",
                "description": (
                    "Structured assist proposal (PREPARE / ACT). Never auto-executes. "
                    "Not inspect, advise, or answering a yes/no. "
                    "A referent correction is not a proposal. "
                    "Pass target_id from referent_candidates when the user names a "
                    "subject. Omit only for implicit 'that'."
                ),
                "parameters": AssistProposeInput.model_json_schema(),
            },
        },
        {
            "type": "function",
            "function": {
                "name": "assist.approve",
                "description": (
                    "Explicit approval of a surfaced assist proposal — synthetic "
                    "execute + verify. Only valid when the previous Enigma turn "
                    "created an approval affordance (the proposal card). "
                    "Yes after SHOW / EXPLAIN is not approval."
                ),
                "parameters": AssistApproveInput.model_json_schema(),
            },
        },
    ]


def _next_action_payload(action: NextActionView) -> dict[str, Any]:
    return action.model_dump(mode="json")


def is_allowed_tool(name: str) -> bool:
    """True when ``name`` is in the demo conversation allowlist."""
    return name in ALLOWED_TOOL_NAMES


def denied_tool_result(
    session: DemoToolSession,
    name: str,
    *,
    reason: str = "tool_not_in_allowlist",
) -> ToolExecutionResult:
    """Deterministic denial for out-of-allowlist or unauthorised tool requests."""
    at = session.at
    turn = [
        {
            "kind": "enigma_message",
            "text": "That action is not available.",
            "at": at,
        }
    ]
    return ToolExecutionResult.model_construct(
        name=name,
        ok=False,
        data={"denied": True, "reason": reason},
        turn_items=turn,
    )


def _resolution(
    *,
    tool: str,
    source: str,
    bound_id: str | None,
    summary: str,
    model_arguments: dict[str, Any],
    executed_arguments: dict[str, Any],
) -> dict[str, Any]:
    return {
        "tool": tool,
        "source": source,
        "bound_id": bound_id,
        "summary": summary,
        "model_arguments": model_arguments,
        "executed_arguments": executed_arguments,
    }


def _denied_speech_act(
    session: DemoToolSession,
    name: ToolName,
    *,
    reason: str,
    message: str,
) -> ToolExecutionResult:
    at = session.at
    return ToolExecutionResult(
        name=name,
        ok=False,
        data={"denied": True, "reason": reason},
        turn_items=[{"kind": "enigma_message", "text": message, "at": at}],
    )


def sync_assist_proposal(session: DemoToolSession, plan: AssistPlan) -> None:
    """Proposal surfaced → store and conversation context share the same id."""
    session.pending_assists[plan.proposal_id] = plan
    session.context.current_assist_proposal_id = plan.proposal_id
    session.context.set_pending_confirmation(
        "APPROVE_CONFIRMATION",
        plan.proposal_id,
    )


def reconcile_pending_proposal_id(session: DemoToolSession) -> str | None:
    """Context id must resolve in pending_assists. Stale ids are dropped."""
    ctx_id = session.context.current_assist_proposal_id
    if ctx_id and ctx_id in session.pending_assists:
        return ctx_id
    if ctx_id and ctx_id not in session.pending_assists:
        if len(session.pending_assists) == 1:
            only_id = next(iter(session.pending_assists))
            session.context.current_assist_proposal_id = only_id
            return only_id
        session.context.current_assist_proposal_id = None
        return None
    if len(session.pending_assists) == 1:
        only_id = next(iter(session.pending_assists))
        session.context.current_assist_proposal_id = only_id
        return only_id
    return None


def bind_assist_propose(
    session: DemoToolSession,
    arguments: dict[str, Any],
    *,
    user_message: str = "",
) -> tuple[dict[str, Any], dict[str, Any]]:
    """Resolve assist.propose to an explicit target_id before execution."""
    model_arguments = dict(arguments)
    explicit = model_arguments.get("target_id") or model_arguments.get("target")
    if isinstance(explicit, str) and explicit.strip():
        target_id = explicit.strip()
        executed = {"target_id": target_id}
        return executed, _resolution(
            tool="assist.propose",
            source="explicit target_id",
            bound_id=target_id,
            summary=f"explicit target_id → {target_id}",
            model_arguments=model_arguments,
            executed_arguments=executed,
        )
    utterance = user_message or session.user_message
    named = match_named_referent(utterance, referent_candidates(session.state))
    if named:
        executed = {"target_id": named}
        return executed, _resolution(
            tool="assist.propose",
            source="named_referent",
            bound_id=named,
            summary=f"named_referent → {named}",
            model_arguments=model_arguments,
            executed_arguments=executed,
        )
    subject = session.context.current_subject_id
    if subject:
        executed = {"target_id": subject}
        return executed, _resolution(
            tool="assist.propose",
            source="implicit current_subject",
            bound_id=subject,
            summary=f"implicit current_subject → {subject}",
            model_arguments=model_arguments,
            executed_arguments=executed,
        )
    fallback = resolve_assist_target(
        session.state, session.conversation, session.completed_item_ids
    )
    if fallback is not None:
        target_id = fallback.attention_item_id
        executed = {"target_id": target_id}
        return executed, _resolution(
            tool="assist.propose",
            source="conversation_fallback",
            bound_id=target_id,
            summary=f"conversation_fallback → {target_id}",
            model_arguments=model_arguments,
            executed_arguments=executed,
        )
    return model_arguments, _resolution(
        tool="assist.propose",
        source="unresolved",
        bound_id=None,
        summary="unresolved — no explicit, named, or current_subject target",
        model_arguments=model_arguments,
        executed_arguments=dict(model_arguments),
    )


def bind_assist_approve(
    session: DemoToolSession,
    arguments: dict[str, Any],
) -> tuple[dict[str, Any], dict[str, Any]]:
    """Bind assist.approve to an explicit proposal_id before execution."""
    model_arguments = dict(arguments)
    explicit = model_arguments.get("proposal_id")
    if isinstance(explicit, str) and explicit.strip():
        proposal_id = explicit.strip()
        executed = {"proposal_id": proposal_id}
        return executed, _resolution(
            tool="assist.approve",
            source="explicit proposal_id",
            bound_id=proposal_id,
            summary=f"explicit proposal_id → {proposal_id}",
            model_arguments=model_arguments,
            executed_arguments=executed,
        )
    proposal_id = reconcile_pending_proposal_id(session)
    if proposal_id:
        executed = {"proposal_id": proposal_id}
        return executed, _resolution(
            tool="assist.approve",
            source="implicit current_assist_proposal_id",
            bound_id=proposal_id,
            summary=f"implicit current_assist_proposal_id → {proposal_id}",
            model_arguments=model_arguments,
            executed_arguments=executed,
        )
    return model_arguments, _resolution(
        tool="assist.approve",
        source="unresolved",
        bound_id=None,
        summary="unresolved — assist.approve requires an explicit proposal_id",
        model_arguments=model_arguments,
        executed_arguments=dict(model_arguments),
    )


def bind_authority_arguments(
    session: DemoToolSession,
    name: str,
    arguments: dict[str, Any],
    *,
    user_message: str = "",
) -> tuple[dict[str, Any], dict[str, Any] | None]:
    """Fill implicit authority args. Queries stay implicit; propose/approve bind."""
    if name == "assist.propose":
        return bind_assist_propose(session, arguments, user_message=user_message)
    if name == "assist.approve":
        return bind_assist_approve(session, arguments)
    return dict(arguments), None


def execute_tool(
    session: DemoToolSession, name: ToolName, arguments: dict[str, Any]
) -> ToolExecutionResult:
    """Run one tool against session state. Returns structured data + conversation turn items."""
    if not is_allowed_tool(name):
        return denied_tool_result(session, name)

    at = session.at
    state = session.state
    ctx = session.context

    if name == "attention.get_current":
        turn = build_needs_me_turn(state, at)
        return ToolExecutionResult(
            name=name,
            data={"state": state.model_dump(mode="json")},
            turn_items=turn,
        )

    if name == "next_action.get":
        turn = build_next_turn(state, at)
        actions = [row.model_dump(mode="json") for row in state.next_actions]
        return ToolExecutionResult(
            name=name,
            data={"next_actions": actions},
            turn_items=turn,
        )

    if name == "next_action.get_alternatives":
        turn = build_alternate_task_turn(state, ctx, at)
        alternate = pick_alternate_next_action(state, set(ctx.suppressed_next_action_ids))
        data: dict[str, Any] = {"alternate": None}
        if alternate is not None:
            data["alternate"] = _next_action_payload(alternate)
        return ToolExecutionResult(name=name, data=data, turn_items=turn)

    if name == "next_action.reject":
        turn = build_reject_next_turn(state, ctx, at)
        return ToolExecutionResult(
            name=name,
            data={"suppressed_next_action_ids": list(ctx.suppressed_next_action_ids)},
            turn_items=turn,
        )

    if name == "referent.get_duration":
        action, title = resolve_referent(state, ctx)
        if action is None or title is None:
            turn = [
                {
                    "kind": "enigma_message",
                    "text": "I'm not sure what you're referring to.",
                    "at": at,
                }
            ]
            return ToolExecutionResult(
                name=name, ok=False, data={"referent": None}, turn_items=turn
            )
        minutes = estimated_minutes_for_action(action)
        if minutes is None:
            text = f"I don't have a time estimate for {title}."
            turn = [{"kind": "enigma_message", "text": text, "at": at}]
            return ToolExecutionResult(
                name=name,
                data={"title": title, "estimated_minutes": None},
                turn_items=turn,
            )
        text = f"{title} should take around {minutes} minutes."
        turn = [{"kind": "enigma_message", "text": text, "at": at}]
        return ToolExecutionResult(
            name=name,
            data={"title": title, "estimated_minutes": minutes, "action_id": action.id},
            turn_items=turn,
        )

    if name == "availability.check":
        parsed = AvailabilityCheckInput.model_validate(arguments)
        if parsed.duration_minutes is not None and parsed.period is None:
            action, title = resolve_referent(state, ctx)
            if action is None:
                turn = [
                    {
                        "kind": "enigma_message",
                        "text": "I'm not sure what you're referring to.",
                        "at": at,
                    }
                ]
                return ToolExecutionResult(name=name, ok=False, turn_items=turn)
            minutes = estimated_minutes_for_action(action) or parsed.duration_minutes
            reference = datetime.fromisoformat(at.replace("Z", "+00:00"))
            if reference.tzinfo is None:
                reference = reference.replace(tzinfo=UTC)
            text = format_time_fit_message(
                state=state,
                checkpoint_id=session.checkpoint_id,
                reference=reference,
                task_minutes=minutes,
                task_title=title,
            )
            turn = [{"kind": "enigma_message", "text": text, "at": at}]
            return ToolExecutionResult(
                name=name,
                data={"time_fit": True, "task_minutes": minutes, "task_title": title},
                turn_items=turn,
            )
        turn = build_availability_turn(
            state,
            checkpoint_id=session.checkpoint_id,
            at=at,
            period=parsed.period,
        )
        return ToolExecutionResult(
            name=name,
            data={"period": parsed.period},
            turn_items=turn,
        )

    if name == "agenda.get":
        parsed_agenda = AgendaGetInput.model_validate(arguments)
        try:
            period_enum = TimeExpression(parsed_agenda.period)
        except ValueError:
            turn = [
                {
                    "kind": "enigma_message",
                    "text": "I don't know that time horizon.",
                    "at": at,
                }
            ]
            return ToolExecutionResult(
                name=name,
                ok=False,
                data={"period": parsed_agenda.period, "unknown_period": True},
                turn_items=turn,
            )
        turn = build_attention_horizon_turn(
            state,
            checkpoint_id=session.checkpoint_id,
            at=at,
            period=period_enum,
        )
        reference = datetime.fromisoformat(at.replace("Z", "+00:00"))
        if reference.tzinfo is None:
            reference = reference.replace(tzinfo=UTC)
        start, end = period_bounds(reference, period_enum.value)
        events = calendar_events_in_period(session.checkpoint_id, start, end)
        attention_rows = [
            item.get("item")
            for item in turn
            if item.get("kind") == "attention_item" and isinstance(item.get("item"), dict)
        ]
        action_rows = [
            item.get("action")
            for item in turn
            if item.get("kind") == "next_action" and isinstance(item.get("action"), dict)
        ]
        return ToolExecutionResult(
            name=name,
            data={
                "period": period_enum.value,
                "calendar_items": events,
                "attention": attention_rows,
                "next_actions": action_rows,
            },
            turn_items=turn,
        )

    if name == "world.get_changes":
        turn = build_changed_turn(state, session.prior_state, at)
        return ToolExecutionResult(
            name=name, data={"has_prior": session.prior_state is not None}, turn_items=turn
        )

    if name == "world.get_blockers":
        blockers = waiting_items(state)
        turn = build_waiting_turn(state, at)
        return ToolExecutionResult(
            name=name,
            data={"blockers": [row.model_dump(mode="json") for row in blockers]},
            turn_items=turn,
        )

    if name == "world.explain":
        parsed = WorldExplainInput.model_validate(arguments)
        if parsed.target:
            ctx.current_subject_id = parsed.target
            ctx.current_attention_item_id = parsed.target
            ctx.current_subject_kind = "attention_item"
            action = find_next_action_by_id(state, ctx.current_next_action_id)
            if action is None or action.source_candidate_id != parsed.target:
                ctx.current_next_action_id = None
        turn = build_explain_referent_turn(
            state,
            ctx,
            at,
            recover=parsed.recover,
        )
        subject_id = ctx.current_subject_id
        return ToolExecutionResult(
            name=name,
            data={
                "subject_id": subject_id,
                "recover": parsed.recover,
                "target": parsed.target,
            },
            turn_items=turn,
        )

    if name == "assist.propose":
        if not session.context.propose_authorized():
            return _denied_speech_act(
                session,
                name,
                reason="pending_act_is_not_prepare",
                message="That wasn't a request to prepare an action.",
            )
        if session.context.turn_local_recorded_this_turn:
            return _denied_speech_act(
                session,
                name,
                reason="turn_local_constraint_is_not_action",
                message="I'll keep that in mind for this turn — it isn't an action.",
            )
        bound, _resolution = bind_assist_propose(
            session, arguments, user_message=session.user_message
        )
        target_id = bound.get("target_id") if isinstance(bound.get("target_id"), str) else None
        target = assist_target_from_id(state, target_id, session.completed_item_ids)
        if target is None:
            turn = [
                {
                    "kind": "enigma_message",
                    "text": "There's nothing for me to help with right now.",
                    "at": at,
                }
            ]
            return ToolExecutionResult(name=name, ok=False, turn_items=turn)
        ctx.current_subject_id = target.attention_item_id
        ctx.current_attention_item_id = target.attention_item_id
        ctx.current_subject_kind = target.source_kind
        plan = make_assist_plan(target)
        sync_assist_proposal(session, plan)
        turn = [assist_proposal_item(plan, at)]
        return ToolExecutionResult(
            name=name,
            data={
                "proposal": plan.public_proposal(),
                "target_id": target.attention_item_id,
            },
            turn_items=turn,
            assist_plan={"proposal_id": plan.proposal_id},
        )

    if name == "assist.approve":
        if not session.context.approval_authorized():
            return _denied_speech_act(
                session,
                name,
                reason="pending_act_is_not_approve",
                message="That wasn't an approval.",
            )
        bound, _resolution = bind_assist_approve(session, arguments)
        proposal_id = bound.get("proposal_id")
        if not isinstance(proposal_id, str) or not proposal_id.strip():
            turn = [
                {"kind": "enigma_message", "text": "I don't know that assist proposal.", "at": at}
            ]
            return ToolExecutionResult(name=name, ok=False, turn_items=turn)
        plan = session.pending_assists.get(proposal_id)
        if plan is None:
            ctx.current_assist_proposal_id = None
            turn = [
                {"kind": "enigma_message", "text": "I don't know that assist proposal.", "at": at}
            ]
            return ToolExecutionResult(name=name, ok=False, turn_items=turn)
        ok, message = execute_and_verify(plan, session.synthetic_services)
        effect = None
        if ok:
            effect = apply_verified_assist_effect(
                plan,
                completed_item_ids=session.completed_item_ids,
                advances=session.assist_advances,
            )
            session.state = overlay_session_world(
                session.state,
                session.completed_item_ids,
                session.assist_advances,
            )
            reconcile_action_focus(ctx, session.state)
        result = assist_result_item(proposal_id=proposal_id, ok=ok, message=message, at=at)
        session.pending_assists.pop(proposal_id, None)
        if ctx.current_assist_proposal_id == proposal_id:
            ctx.current_assist_proposal_id = None
        ctx.set_pending_confirmation(None)
        return ToolExecutionResult(
            name=name,
            data={"ok": ok, "message": message, "proposal_id": proposal_id, "effect": effect},
            turn_items=[result],
        )

    return denied_tool_result(session, name, reason="unknown_tool")


__all__ = [
    "ALLOWED_TOOL_NAMES",
    "DENIED_REMOTE_CAPABILITIES",
    "DemoToolSession",
    "ToolCallRecord",
    "ToolExecutionResult",
    "ToolName",
    "bind_authority_arguments",
    "denied_tool_result",
    "execute_tool",
    "is_allowed_tool",
    "reconcile_pending_proposal_id",
    "sync_assist_proposal",
    "tool_schemas",
]
