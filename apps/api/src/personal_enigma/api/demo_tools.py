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
from personal_enigma.api.demo_attestation import (
    ATTESTATION_TOOL,
    AttestedState,
    UserAttestation,
    apply_user_attestation,
    attestation_title,
)
from personal_enigma.api.demo_availability import (
    build_availability_turn,
    calendar_events_in_period,
    format_time_fit_message,
    period_bounds,
)
from personal_enigma.api.demo_chat import DemoChatIndex, find_chat_quote
from personal_enigma.api.demo_intents import (
    build_alternate_task_turn,
    build_attention_horizon_turn,
    build_changed_turn,
    build_explain_referent_turn,
    build_needs_me_turn,
    build_next_turn,
    build_reject_next_turn,
    build_support_payload,
    build_waiting_turn,
    waiting_items,
)
from personal_enigma.api.intent_router import TimeExpression
from personal_enigma.api.speech_acts import (
    classify_speech_act,
    infer_attestation_state,
    is_support_not_authority,
    signals_difficulty,
)
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
    "world.record_user_attestation",
    "source.recent",
    "source.quote",
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
        "world.record_user_attestation",
        "source.recent",
        "source.quote",
        "assist.propose",
        "assist.approve",
    )
)

# Capability fence — not a second tool registry. The model cannot request these.
DENIED_REMOTE_CAPABILITIES: tuple[str, ...] = (
    "gmail.search",
    "gmail.send",
    "whatsapp.search",
    "whatsapp.send",
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


class SourceRecentInput(BaseModel):
    channel: str | None = Field(
        default=None,
        description="email, whatsapp, or chat. Defaults to the channel named in the utterance.",
    )


class SourceQuoteInput(BaseModel):
    source_id: str | None = Field(
        default=None,
        description=(
            "Local source id to quote. Omit to resolve from the utterance "
            "(e.g. Elena). The verbatim body is displayed locally and is never "
            "returned on the tool wire."
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


class WorldRecordUserAttestationInput(BaseModel):
    target_id: str | None = Field(
        default=None,
        description=(
            "Obligation / attention-item id the user is reporting about, from "
            "referent_candidates. Omit for implicit 'it' / current_subject — "
            "Enigma binds an explicit id before execution."
        ),
    )
    state: AttestedState = Field(
        default="COMPLETED",
        description=(
            "COMPLETED when the user reports they did it / sent it / paid it. "
            "OPEN when they correct a prior report ('actually I haven't finished'). "
            "CANCELLED when they no longer need to do it. "
            "This records evidence; it does not execute an Assist or an external write."
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
    attestations: list[UserAttestation] = field(default_factory=list)
    chat_index: DemoChatIndex = field(default_factory=DemoChatIndex)


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
                    "SUPPORT: discuss, explain, break down, or name a first step "
                    "for the current subject. Use for 'help, I'm overwhelmed', "
                    "'I need help with that', 'I find this hard', or 'let's talk "
                    "through it'. Distress may increase supportiveness, never "
                    "authority. Ambiguous help requests default to the "
                    "least-authoritative useful interpretation — this tool, not "
                    "assist.propose. Does not prepare, propose, approve, or execute."
                ),
                "parameters": WorldExplainInput.model_json_schema(),
            },
        },
        {
            "type": "function",
            "function": {
                "name": "world.record_user_attestation",
                "description": (
                    "Record that the user told Enigma the private world changed. "
                    "Use when the user reports they did something, sent something, "
                    "paid something, or that they have not actually finished. "
                    "Reports are evidence — not Assist, not an approval ceremony, "
                    "not an external mutation (no bank login, no manufactured payment). "
                    "'I booked it' / 'I've done the draft colours' → this tool. "
                    "'Book it' / 'Do the token inventory' → assist.propose. "
                    "Conversation alone must never be the only place this change exists."
                ),
                "parameters": WorldRecordUserAttestationInput.model_json_schema(),
            },
        },
        {
            "type": "function",
            "function": {
                "name": "source.recent",
                "description": (
                    "Recent private sources (email or WhatsApp) as local summaries. "
                    "Does not return wholesale bodies. Use for 'latest from my emails' "
                    "or 'anything in WhatsApp'."
                ),
                "parameters": SourceRecentInput.model_json_schema(),
            },
        },
        {
            "type": "function",
            "function": {
                "name": "source.quote",
                "description": (
                    "Quote a private source locally. The verbatim body is shown in "
                    "the conversation UI and is never returned to the model. "
                    "Use when the user asks what someone exactly said."
                ),
                "parameters": SourceQuoteInput.model_json_schema(),
            },
        },
        {
            "type": "function",
            "function": {
                "name": "assist.propose",
                "description": (
                    "PREPARE / PROPOSE only. Funnel: UNDERSTAND → SUPPORT → "
                    "PREPARE → PROPOSE → APPROVE → EXECUTE. Never skip toward "
                    "more authority. Use after an explicit prepare/do request "
                    "('can you draft something', 'help me do that', 'do it'). "
                    "Not for 'I need help', distress, or ADHD mentions. "
                    "Never auto-executes. A referent correction is not a proposal. "
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
                    "Yes after SHOW / EXPLAIN is not approval. "
                    "Distress may increase supportiveness, never authority — "
                    "ADHD or overwhelm never upgrades this even if a proposal is pending."
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


def bind_world_attestation(
    session: DemoToolSession,
    arguments: dict[str, Any],
    *,
    user_message: str = "",
) -> tuple[dict[str, Any], dict[str, Any]]:
    """Resolve world.record_user_attestation to an explicit target_id."""
    model_arguments = dict(arguments)
    utterance = user_message or session.user_message
    state_raw = model_arguments.get("state")
    attested_state: AttestedState
    if state_raw in {"COMPLETED", "OPEN", "CANCELLED"}:
        attested_state = state_raw
    else:
        attested_state = infer_attestation_state(utterance)
    explicit = model_arguments.get("target_id") or model_arguments.get("target")
    if isinstance(explicit, str) and explicit.strip():
        target_id = explicit.strip()
        executed = {"target_id": target_id, "state": attested_state}
        return executed, _resolution(
            tool=ATTESTATION_TOOL,
            source="explicit target_id",
            bound_id=target_id,
            summary=f"explicit target_id → {target_id}",
            model_arguments=model_arguments,
            executed_arguments=executed,
        )
    named = match_named_referent(utterance, referent_candidates(session.state))
    if named:
        executed = {"target_id": named, "state": attested_state}
        return executed, _resolution(
            tool=ATTESTATION_TOOL,
            source="named_referent",
            bound_id=named,
            summary=f"named_referent → {named}",
            model_arguments=model_arguments,
            executed_arguments=executed,
        )
    subject = session.context.current_subject_id
    if subject:
        executed = {"target_id": subject, "state": attested_state}
        return executed, _resolution(
            tool=ATTESTATION_TOOL,
            source="implicit current_subject",
            bound_id=subject,
            summary=f"implicit current_subject → {subject}",
            model_arguments=model_arguments,
            executed_arguments=executed,
        )
    return {"state": attested_state, **model_arguments}, _resolution(
        tool=ATTESTATION_TOOL,
        source="unresolved",
        bound_id=None,
        summary="unresolved — no explicit, named, or current_subject target",
        model_arguments=model_arguments,
        executed_arguments={"state": attested_state, **dict(model_arguments)},
    )


def bind_authority_arguments(
    session: DemoToolSession,
    name: str,
    arguments: dict[str, Any],
    *,
    user_message: str = "",
) -> tuple[dict[str, Any], dict[str, Any] | None]:
    """Fill implicit authority args. Queries stay implicit; propose/approve/attest bind."""
    if name == "assist.propose":
        return bind_assist_propose(session, arguments, user_message=user_message)
    if name == "assist.approve":
        return bind_assist_approve(session, arguments)
    if name == ATTESTATION_TOOL:
        return bind_world_attestation(session, arguments, user_message=user_message)
    if name == "agenda.get":
        executed = dict(arguments)
        if not executed.get("period") and session.context.temporal_constraint:
            executed["period"] = session.context.temporal_constraint
        return executed, None
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
        if parsed.duration_minutes is not None:
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
            fit_period = parsed.period or "later_today"
            text = format_time_fit_message(
                state=state,
                checkpoint_id=session.checkpoint_id,
                reference=reference,
                task_minutes=minutes,
                task_title=title,
                period=fit_period,
            )
            if parsed.period and parsed.period != "later_today":
                occupancy = build_availability_turn(
                    state,
                    checkpoint_id=session.checkpoint_id,
                    at=at,
                    period=parsed.period,
                )
                occ_text = occupancy[0]["text"] if occupancy else ""
                if occ_text:
                    text = f"{occ_text} {text}"
            turn = [{"kind": "enigma_message", "text": text, "at": at}]
            return ToolExecutionResult(
                name=name,
                data={
                    "time_fit": True,
                    "task_minutes": minutes,
                    "task_title": title,
                    "period": parsed.period,
                },
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
        empty_horizon = not events and not attention_rows and not action_rows
        if empty_horizon:
            # Candidates stay resolvable; they are not conversation focus.
            turn = [item for item in turn if item.get("kind") == "enigma_message"]
        return ToolExecutionResult(
            name=name,
            data={
                "period": period_enum.value,
                "calendar_items": events,
                "attention": attention_rows,
                "next_actions": action_rows,
                "empty_horizon": empty_horizon,
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
        chat_blockers = [
            {
                "id": blocker.evidence_ids[0] if blocker.evidence_ids else blocker.description,
                "description": blocker.description,
                "counterpart": blocker.counterpart,
            }
            for blocker in session.chat_index.world.blockers
        ]
        return ToolExecutionResult(
            name=name,
            data={
                "blockers": [row.model_dump(mode="json") for row in blockers],
                "chat_blocker_ids": [row["id"] for row in chat_blockers],
            },
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
        hay = session.user_message.casefold()
        facts = [fact.summary for fact in session.chat_index.world.facts]
        if any(token in hay for token in ("elena", "parent", "coming", "say")):
            for summary in facts:
                turn.insert(
                    0,
                    {"kind": "enigma_message", "text": summary, "at": at},
                )
        subject_id = ctx.current_subject_id
        support = build_support_payload(state, ctx)
        return ToolExecutionResult(
            name=name,
            data={
                "subject_id": subject_id,
                "recover": parsed.recover,
                "target": parsed.target,
                "facts": facts,
                "title": support["title"],
                "why_it_matters": support["why_it_matters"],
                "first_step": support["first_step"],
                "estimated_minutes": support["estimated_minutes"],
                "support_options": support["support_options"],
                "assist_offered": False,
            },
            turn_items=turn,
        )

    if name == "assist.propose":
        utterance = session.user_message
        if is_support_not_authority(utterance):
            return _denied_speech_act(
                session,
                name,
                reason="help_is_not_prepare",
                message=(
                    "That's a request for support, not for me to prepare an action. "
                    "We can talk it through first."
                ),
            )
        if classify_speech_act(utterance) == "USER_ATTESTATION":
            return _denied_speech_act(
                session,
                name,
                reason="report_is_not_action",
                message="That's a report about the world, not a request to act.",
            )
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
        utterance = session.user_message
        if is_support_not_authority(utterance) or signals_difficulty(utterance):
            return _denied_speech_act(
                session,
                name,
                reason="difficulty_is_not_consent",
                message=(
                    "Distress may increase supportiveness, never authority. "
                    "That isn't approval."
                ),
            )
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

    if name == ATTESTATION_TOOL:
        parsed_attest = WorldRecordUserAttestationInput.model_validate(arguments)
        target_id = parsed_attest.target_id
        if not target_id:
            turn = [
                {
                    "kind": "enigma_message",
                    "text": "I'm not sure what you're referring to.",
                    "at": at,
                }
            ]
            return ToolExecutionResult(
                name=name,
                ok=False,
                data={"reason": "unresolved_target"},
                turn_items=turn,
            )
        title = attestation_title(state, target_id)
        if ctx.current_subject_id != target_id:
            ctx.current_subject_id = target_id
            ctx.current_attention_item_id = target_id
            ctx.current_subject_kind = ctx.current_subject_kind or "attention_item"
        record = apply_user_attestation(
            attestations=session.attestations,
            completed_item_ids=session.completed_item_ids,
            advances=session.assist_advances,
            target_id=target_id,
            state=parsed_attest.state,
            at=at,
            utterance=session.user_message,
        )
        session.state = overlay_session_world(
            session.state,
            session.completed_item_ids,
            session.assist_advances,
        )
        reconcile_action_focus(ctx, session.state)
        if parsed_attest.state == "COMPLETED":
            text = f"Noted — I'll treat {title} as done."
        elif parsed_attest.state == "OPEN":
            text = f"Noted — I'll treat {title} as still open."
        else:
            text = f"Noted — you don't need to do {title} anymore."
        turn = [{"kind": "enigma_message", "text": text, "at": at}]
        return ToolExecutionResult(
            name=name,
            data={
                "target_id": target_id,
                "state": parsed_attest.state,
                "evidence": record.evidence,
                "attestation_id": record.id,
                "supersedes": record.supersedes,
                "source": "user_attestation",
            },
            turn_items=turn,
        )

    if name == "source.recent":
        parsed_recent = SourceRecentInput.model_validate(arguments)
        channel = (parsed_recent.channel or "").casefold()
        if not channel:
            hay = session.user_message.casefold()
            if "whatsapp" in hay or "chat" in hay:
                channel = "whatsapp"
            else:
                channel = "email"
        if channel in {"whatsapp", "chat"}:
            rows = [
                {
                    "id": message.provider_message_id,
                    "from": (message.from_person.display_name if message.from_person else None),
                    "at": message.sent_at.isoformat() if message.sent_at else None,
                }
                for message in session.chat_index.messages
                if message.kind == "text"
            ][-5:]
            facts = [fact.summary for fact in session.chat_index.world.facts]
            text = (
                " ".join(facts)
                if facts
                else "Nothing recent in WhatsApp that I derived a fact from."
            )
            turn = [{"kind": "enigma_message", "text": text, "at": at}]
            return ToolExecutionResult(
                name=name,
                data={"channel": "whatsapp", "recent_ids": [row["id"] for row in rows]},
                turn_items=turn,
            )
        rows = []
        for message in session.chat_index.mail[-5:]:
            stamped = message.received_at or message.sent_at
            rows.append(
                {
                    "id": message.provider_message_id,
                    "subject": message.subject,
                    "at": stamped.isoformat() if stamped is not None else None,
                }
            )
        if not rows:
            text = "I don't know."
        else:
            subjects = [row["subject"] or row["id"] for row in rows]
            text = "Latest email: " + "; ".join(str(item) for item in subjects) + "."
        turn = [{"kind": "enigma_message", "text": text, "at": at}]
        return ToolExecutionResult(
            name=name,
            data={"channel": "email", "recent_ids": [row["id"] for row in rows]},
            turn_items=turn,
        )

    if name == "source.quote":
        parsed_quote = SourceQuoteInput.model_validate(arguments)
        message = find_chat_quote(
            session.chat_index,
            source_id=parsed_quote.source_id,
            user_message=session.user_message,
            conversation=session.conversation,
        )
        if message is None:
            turn = [
                {
                    "kind": "enigma_message",
                    "text": "I don't have that original message.",
                    "at": at,
                }
            ]
            return ToolExecutionResult(
                name=name,
                ok=False,
                data={"quoted_locally": False, "source_id": parsed_quote.source_id},
                turn_items=turn,
            )
        if session.chat_index.is_expired(message):
            turn = [
                {
                    "kind": "enigma_message",
                    "text": (
                        "That original message is no longer stored. "
                        "I still have the derived fact."
                    ),
                    "at": at,
                }
            ]
            return ToolExecutionResult(
                name=name,
                data={
                    "quoted_locally": False,
                    "expired": True,
                    "source_id": message.provider_message_id,
                },
                turn_items=turn,
            )
        speaker = (
            message.from_person.display_name if message.from_person else "Someone"
        )
        body = message.body_text or ""
        turn = [
            {
                "kind": "source_quote",
                "text": f'{speaker}: "{body}"',
                "source_id": message.provider_message_id,
                "at": at,
                "local_only": True,
                "privacy_level": "very_high",
                "egress_classification": "local_only",
            }
        ]
        return ToolExecutionResult(
            name=name,
            data={
                "quoted_locally": True,
                "source_id": message.provider_message_id,
            },
            turn_items=turn,
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
