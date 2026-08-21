"""Shared turn kernel — interpret → plan → execute → verify → respond (ADR-040)."""

from __future__ import annotations

import re
from collections.abc import Sequence
from dataclasses import dataclass, field
from typing import Any, Literal, Protocol
from uuid import uuid4

from personal_enigma.api.build_identity import attach_forensic_provenance
from personal_enigma.api.context_compilation import (
    _AVAILABILITY_FREE_CUE,
    RequestInterpretation,
)
from personal_enigma.api.conversation_context import (
    ConversationContext,
    update_context_from_turn_items,
)
from personal_enigma.api.demo_orchestrator import LlmTrace, build_intent_router_trace
from personal_enigma.api.demo_tools import ToolExecutionResult
from personal_enigma.api.evidence_bundle import planned_tools_for_kind
from personal_enigma.api.intent_router import ConversationIntentKind, resolve_intent
from personal_enigma.api.private_calendar_read import infer_private_calendar_period
from personal_enigma.api.private_tools import (
    PrivateToolSession,
    execute_private_tool,
    private_capability_contract,
)
from personal_enigma.api.semantic_bootstrap import interpret_with_router
from personal_enigma.attention.projection import AttentionState, build_presentation_plan

TurnOutcomeStatus = Literal[
    "fulfilled",
    "partial",
    "misdispatched",
    "unsupported",
    "source_unavailable",
    "failed",
]


@dataclass(frozen=True)
class ExecutionPlan:
    """Planned capabilities for one turn — immutable after plan phase."""

    planned_capabilities: tuple[str, ...]
    steps: tuple[dict[str, Any], ...] = ()


@dataclass(frozen=True)
class TurnOutcome:
    """Fulfilment verdict for a completed turn."""

    status: TurnOutcomeStatus
    planned_capabilities: tuple[str, ...]
    executed_capabilities: tuple[str, ...]
    coverage_adequate: bool


@dataclass
class TurnResult:
    """Normalized turn payload from the shared kernel."""

    items: list[dict[str, Any]]
    llm_trace: dict[str, Any]
    outcome: TurnOutcome
    calendar_facts_used: list[dict[str, Any]] = field(default_factory=list)
    context: ConversationContext | None = None
    assist_plan: Any | None = None


@dataclass(frozen=True)
class WorldTurnProfile:
    """World-specific adapters — routing and fulfilment semantics stay shared."""

    world_id: str
    environment: str
    authority_ceiling: str


def derive_turn_outcome(
    *,
    planned: ExecutionPlan,
    executed_names: list[str],
    tool_results: Sequence[ToolExecutionResult | dict[str, Any]],
    misdispatched: bool = False,
) -> TurnOutcome:
    """Conjunctive fulfilment: weakest critical link wins."""
    executed = tuple(executed_names)
    planned_caps = planned.planned_capabilities
    if misdispatched:
        return TurnOutcome(
            status="misdispatched",
            planned_capabilities=planned_caps,
            executed_capabilities=executed,
            coverage_adequate=False,
        )
    if not planned_caps and not executed:
        return TurnOutcome(
            status="fulfilled",
            planned_capabilities=planned_caps,
            executed_capabilities=executed,
            coverage_adequate=True,
        )
    if planned_caps and not executed:
        return TurnOutcome(
            status="unsupported",
            planned_capabilities=planned_caps,
            executed_capabilities=executed,
            coverage_adequate=False,
        )
    failed = any(
        (
            result.ok is False
            if isinstance(result, ToolExecutionResult)
            else not result.get("ok", True)
        )
        for result in tool_results
    )
    if failed:
        return TurnOutcome(
            status="failed",
            planned_capabilities=planned_caps,
            executed_capabilities=executed,
            coverage_adequate=False,
        )
    missing = [cap for cap in planned_caps if cap not in executed]
    if missing and executed:
        return TurnOutcome(
            status="partial",
            planned_capabilities=planned_caps,
            executed_capabilities=executed,
            coverage_adequate=False,
        )
    return TurnOutcome(
        status="fulfilled",
        planned_capabilities=planned_caps,
        executed_capabilities=executed,
        coverage_adequate=True,
    )


_PREPARE_RE = re.compile(
    r"\b(book it|schedule it|add to calendar|create (?:an )?event|send (?:the )?invite|"
    r"book\b[^.?!]{0,40}\bcalendar)\b",
    re.IGNORECASE,
)

_DEMO_TO_PRIVATE_TOOL: dict[str, str] = {
    "agenda.get": "briefing.read",
    "availability.check": "availability.check",
    "attention.get_current": "attention.get_current",
    "next_action.get": "attention.get_current",
    "world.explain": "world.explain",
}


class _PrivateKernelSession(Protocol):
    context: ConversationContext
    state: AttentionState


@dataclass(frozen=True)
class _PrivateKernelSessionImpl:
    context: ConversationContext
    state: AttentionState
    adapter: Any


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


def _private_planned_capabilities(
    interp: RequestInterpretation,
    *,
    selected_tool: str | None = None,
) -> tuple[str, ...]:
    """Plan only the tool the private kernel executes this turn."""
    if selected_tool:
        return (selected_tool,)
    oracle = [
        _DEMO_TO_PRIVATE_TOOL.get(name, name)
        for name in planned_tools_for_kind(interp.request_kind)
    ]
    oracle = list(dict.fromkeys(oracle))
    if oracle:
        return tuple(oracle)
    if "availability" in interp.capability_families:
        return ("availability.check",)
    if "agenda" in interp.capability_families:
        return ("briefing.read",)
    if "attention" in interp.capability_families:
        return ("attention.get_current",)
    if "explain" in interp.capability_families:
        return ("world.explain",)
    return ()


def _explicit_private_period(
    text: str,
    interp: RequestInterpretation,
) -> str | None:
    return interp.constraints.period or infer_private_calendar_period(text)


def _resolve_private_period(
    text: str,
    interp: RequestInterpretation,
    context: ConversationContext,
) -> str | None:
    explicit = _explicit_private_period(text, interp)
    if explicit is not None:
        return explicit
    # next_work / attention asks without an explicit horizon must not inherit calendar scope.
    if interp.request_kind == "next_work":
        return None
    if interp.frame_inherited or interp.request_kind == "agenda":
        return context.temporal_constraint
    return None


def _select_private_tool(
    text: str,
    interp: RequestInterpretation,
    context: ConversationContext,
) -> tuple[str, dict[str, Any]] | None:
    """Pick one private READ/SUPPORT tool from compiler interpretation."""
    if interp.evidence_domain != "PRIVATE_WORLD":
        return None
    if interp.authority in {"PREPARE", "APPROVE", "EXECUTE", "ATTEST"}:
        return None

    period = _resolve_private_period(text, interp, context)
    families = set(interp.capability_families)

    if "availability" in families and _AVAILABILITY_FREE_CUE.search(text):
        return "availability.check", {"period": period}

    if interp.request_kind == "support_explain" or interp.profile == "SUPPORT":
        return "world.explain", {}

    if interp.request_kind == "next_work" and _explicit_private_period(text, interp) is None:
        return "attention.get_current", {}

    if period or "agenda" in families or interp.request_kind == "agenda":
        return "briefing.read", {"period": period or "this_week"}

    oracle = planned_tools_for_kind(interp.request_kind)
    if oracle:
        private_name = _DEMO_TO_PRIVATE_TOOL.get(oracle[0], oracle[0])
        args: dict[str, Any] = {}
        if private_name in {"briefing.read", "availability.check"}:
            args["period"] = period or "this_week"
        return private_name, args

    return None


def _planner_from_interpretation(
    interp: RequestInterpretation,
    *,
    authority_refusal: bool = False,
) -> str:
    if authority_refusal or interp.authority == "PREPARE" or interp.profile == "PREPARE_ACTION":
        return "authority_refusal"
    if interp.evidence_domain == "GENERAL_KNOWLEDGE" or interp.profile == "GENERAL_KNOWLEDGE":
        return "general_knowledge_ejected"
    if interp.evidence_domain == "PRIVATE_WORLD" and interp.authority in {"READ", "SUPPORT"}:
        return "private_calendar_read"
    return "conversation"


def _conversation_text_for_interpretation(
    interp: RequestInterpretation,
    *,
    text: str,
    authority_refusal: bool = False,
) -> str:
    if authority_refusal or interp.authority == "PREPARE" or interp.profile == "PREPARE_ACTION":
        return (
            "I can read your calendar and help you think through it — "
            "I can't create or change calendar events yet."
        )
    if interp.evidence_domain == "GENERAL_KNOWLEDGE" or interp.profile == "GENERAL_KNOWLEDGE":
        return "I don't have general knowledge — try a search engine for that."
    if resolve_intent(text).kind == ConversationIntentKind.GREETING:
        return "Hey! Ask me what's on your calendar or what needs your attention."
    return "I'm here — ask me what's on your calendar or what needs your attention."


def agent_work_label_from_outcome(outcome: TurnOutcome, *, tool_name: str | None = None) -> str:
    """Derive Goose/activity labels from TurnOutcome, not handler identity."""
    if outcome.status in {"unsupported", "misdispatched", "failed"}:
        return "Checked why this matters"
    if tool_name == "briefing.read" or tool_name == "agenda.get":
        return "Checked your week" if outcome.status == "fulfilled" else "Checked calendar"
    if tool_name == "availability.check":
        return "Checked availability"
    if tool_name == "attention.get_current":
        return "Checked attention"
    if outcome.executed_capabilities:
        return "Checked calendar"
    return "Handled"


def attach_kernel_forensics(
    trace: LlmTrace | dict[str, Any],
    *,
    profile: WorldTurnProfile,
    checkpoint_id: str | None = None,
    scenario: str | None = None,
) -> dict[str, Any]:
    """Wire build_identity forensics onto every kernel trace."""
    environment = profile.environment
    scenario_id = scenario or ("alex-v1" if profile.world_id == "alex_lab" else None)
    attached = attach_forensic_provenance(
        trace,
        environment=environment,
        scenario=scenario_id,
        checkpoint_id=checkpoint_id,
    )
    if hasattr(attached, "model_dump"):
        payload = attached.model_dump(mode="json")
    else:
        payload = dict(attached)
    return payload


def stamp_turn_outcome_on_trace(
    payload: dict[str, Any],
    outcome: TurnOutcome,
    *,
    tool_name: str | None = None,
) -> dict[str, Any]:
    """Attach fulfilment verdict and derived AgentWork label to trace."""
    stamped = dict(payload)
    primary_tool = tool_name or (
        outcome.executed_capabilities[0] if outcome.executed_capabilities else None
    )
    stamped["turn_outcome"] = {
        "status": outcome.status,
        "planned_capabilities": list(outcome.planned_capabilities),
        "executed_capabilities": list(outcome.executed_capabilities),
        "coverage_adequate": outcome.coverage_adequate,
        "agent_work_label": agent_work_label_from_outcome(outcome, tool_name=primary_tool),
    }
    return stamped


def _infer_alex_planned_capabilities(resolved: Any) -> tuple[str, ...]:
    """Map resolved Demo intent to composite/atomic capability names."""
    kind = resolved.kind
    if kind == ConversationIntentKind.ATTENTION_QUERY:
        if resolved.period is not None:
            return ("briefing.read",)
        return ("attention.get_current",)
    if kind == ConversationIntentKind.NEXT_ACTION_QUERY:
        if resolved.period is not None:
            return ("briefing.read",)
        return ("next_action.get",)
    if kind == ConversationIntentKind.AVAILABILITY_QUERY:
        return ("availability.check",)
    if kind == ConversationIntentKind.TIME_FIT_QUERY:
        return ("availability.time_fit",)
    if kind == ConversationIntentKind.WHY_QUERY:
        return ("attention.explain_why",)
    if kind == ConversationIntentKind.CHANGES_QUERY:
        return ("world.get_changes",)
    if kind == ConversationIntentKind.WAITING_ON_QUERY:
        return ("world.get_blockers",)
    if kind == ConversationIntentKind.CAN_WAIT_QUERY:
        return ("attention.get_current",)
    if kind == ConversationIntentKind.REJECT_NEXT_ACTION:
        return ("next_action.reject",)
    if kind == ConversationIntentKind.ALTERNATE_TASK_QUERY:
        return ("next_action.get_alternatives",)
    if kind == ConversationIntentKind.DURATION_QUERY:
        return ("referent.get_duration",)
    return ()


def run_alex_turn(
    *,
    text: str,
    at: str,
    corr: str,
    profile: WorldTurnProfile,
    conversation_context: ConversationContext,
    llm_enabled: bool,
    tool_session: Any | None = None,
    state: AttentionState | None = None,
    checkpoint_id: str | None = None,
    prior_state: AttentionState | None = None,
    conversation: list[dict[str, Any]] | None = None,
    completed_item_ids: set[str] | None = None,
) -> TurnResult:
    """Alex Lab turn via shared kernel — LLM orchestrator or deterministic intent router."""
    from personal_enigma.api.demo_intents import build_intent_turn
    from personal_enigma.api.demo_orchestrator import run_orchestrator_turn

    conversation_state = {
        "current_subject_id": conversation_context.current_subject_id,
        "current_subject_kind": conversation_context.current_subject_kind,
    }
    last_intent = conversation_context.last_intent

    if llm_enabled:
        if tool_session is None:
            raise ValueError("tool_session required when llm_enabled")
        orchestrated = run_orchestrator_turn(
            user_message=text,
            session=tool_session,
            correlation_id=corr,
        )
        turn_items = orchestrated.turn_items
        trace = orchestrated.llm_trace or build_intent_router_trace(
            user_message=text,
            conversation_state=conversation_state,
            last_intent=last_intent,
            turn_items=turn_items,
            correlation_id=corr,
        )
        executed = [call.name for call in orchestrated.tool_calls]
        plan = ExecutionPlan(planned_capabilities=tuple(executed))
        outcome = derive_turn_outcome(
            planned=plan,
            executed_names=executed,
            tool_results=orchestrated.tool_results,
            misdispatched=bool(executed) and executed == ["world.explain"],
        )
        primary_tool = executed[0] if executed else None
        payload = trace.model_dump(mode="json") if isinstance(trace, LlmTrace) else dict(trace)
        payload = attach_kernel_forensics(
            payload,
            profile=profile,
            checkpoint_id=checkpoint_id,
            scenario="alex-v1",
        )
        payload = stamp_turn_outcome_on_trace(payload, outcome, tool_name=primary_tool)
        if turn_items:
            turn_items = [
                {**turn_items[0], "llm_trace": payload}, *turn_items[1:]
            ]
        return TurnResult(
            items=turn_items,
            llm_trace=payload,
            outcome=outcome,
            assist_plan=orchestrated.assist_plan,
            context=conversation_context,
        )

    if state is None:
        raise ValueError("state required when llm_enabled is False")
    turn_items, assist_plan = build_intent_turn(
        text,
        state,
        at=at,
        checkpoint_id=checkpoint_id,
        prior_state=prior_state,
        conversation=conversation,
        completed_item_ids=completed_item_ids,
        conversation_context=conversation_context,
    )
    turn_items = [
        item if item.get("correlation_id") else {**item, "correlation_id": corr}
        for item in turn_items
    ]
    trace = build_intent_router_trace(
        user_message=text,
        conversation_state=conversation_state,
        last_intent=last_intent,
        turn_items=turn_items,
        correlation_id=corr,
    )
    resolved = conversation_context.compose_intent(text)
    planned_caps = _infer_alex_planned_capabilities(resolved)
    executed_request = trace.executed_tool_request or []
    executed_names = [row["name"] for row in executed_request if isinstance(row, dict)]
    if planned_caps and not executed_names:
        executed_names = list(planned_caps)
        trace = trace.model_copy(
            update={
                "executed_tool_request": [
                    {"name": cap, "arguments": {}} for cap in planned_caps
                ]
            }
        )
    plan = ExecutionPlan(planned_capabilities=planned_caps)
    outcome = derive_turn_outcome(
        planned=plan,
        executed_names=executed_names,
        tool_results=[],
        misdispatched=resolved.kind == ConversationIntentKind.UNKNOWN,
    )
    payload = trace.model_dump(mode="json")
    payload = attach_kernel_forensics(
        payload,
        profile=profile,
        checkpoint_id=checkpoint_id,
        scenario="alex-v1",
    )
    primary_tool = (
        executed_names[0]
        if executed_names
        else (planned_caps[0] if planned_caps else None)
    )
    payload = stamp_turn_outcome_on_trace(payload, outcome, tool_name=primary_tool)
    if turn_items:
        turn_items = [{**turn_items[0], "llm_trace": payload}, *turn_items[1:]]
    return TurnResult(
        items=turn_items,
        llm_trace=payload,
        outcome=outcome,
        assist_plan=assist_plan,
        context=conversation_context,
    )


def _attach_trace(turn_items: list[dict[str, Any]], trace_payload: dict[str, Any]) -> None:
    if not turn_items:
        return
    stamped: dict[str, Any] = dict(turn_items[0])
    stamped["llm_trace"] = trace_payload
    turn_items[0] = stamped


def _conversation_only_payload(
    *,
    text: str,
    user_message: str,
    at: str,
    corr: str,
    ctx: ConversationContext,
    planner: str,
    routing: dict[str, Any] | None = None,
) -> TurnResult:
    turn_items: list[dict[str, Any]] = [
        {"kind": "enigma_message", "text": text, "at": at, "correlation_id": corr}
    ]
    trace = build_intent_router_trace(
        user_message=user_message,
        conversation_state={"authority_ceiling": "READ_SUPPORT"},
        last_intent=ctx.last_intent,
        turn_items=turn_items,
        correlation_id=corr,
    )
    path = "intent_router"
    if routing and routing.get("primary") == "semantic":
        path = "llm"
    elif routing and routing.get("abstain"):
        path = "intent_router"
    trace = trace.model_copy(
        update={
            "path": path,
            "planner": planner,
            "tools_available": [],
            "executed_tool_request": [],
            "tool_results": [],
            "routing": routing,
            "router_fallback": not bool(routing and routing.get("primary") == "semantic"),
        }
    )
    profile = WorldTurnProfile(
        world_id="my_enigma",
        environment="private",
        authority_ceiling="READ_SUPPORT",
    )
    outcome = derive_turn_outcome(
        planned=ExecutionPlan(planned_capabilities=()),
        executed_names=[],
        tool_results=[],
    )
    trace_payload = attach_kernel_forensics(trace, profile=profile)
    trace_payload = stamp_turn_outcome_on_trace(trace_payload, outcome)
    _attach_trace(turn_items, trace_payload)
    return TurnResult(
        items=turn_items,
        llm_trace=trace_payload,
        outcome=outcome,
        context=ctx,
    )


def run_private_turn(
    *,
    text: str,
    at: str,
    adapter: Any,
    conversation: list[dict[str, Any]],
    context: ConversationContext | None = None,
) -> TurnResult:
    """My Enigma turn via shared kernel — semantic router → compiler → plan → execute."""
    ctx = context or ConversationContext()
    corr = f"corr-{uuid4().hex}"
    profile = WorldTurnProfile(
        world_id="my_enigma",
        environment="private",
        authority_ceiling="READ_SUPPORT",
    )
    conversation.append(
        {"kind": "user_message", "text": text, "at": at, "correlation_id": corr}
    )

    kernel_session = _PrivateKernelSessionImpl(
        context=ctx,
        state=_silence_attention(at),
        adapter=adapter,
    )
    decision = interpret_with_router(text, kernel_session)
    interp = decision.interpretation
    routing = decision.trace
    authority_refusal = (
        _PREPARE_RE.search(text) is not None
        or interp.authority == "PREPARE"
        or interp.profile == "PREPARE_ACTION"
    )

    if authority_refusal:
        result = _conversation_only_payload(
            text=_conversation_text_for_interpretation(
                interp, text=text, authority_refusal=True
            ),
            user_message=text,
            at=at,
            corr=corr,
            ctx=ctx,
            planner=_planner_from_interpretation(interp, authority_refusal=True),
            routing=routing,
        )
        conversation.extend(result.items)
        update_context_from_turn_items(ctx, result.items)
        result.context = ctx
        return result

    if (
        interp.evidence_domain in {"CONVERSATION_ONLY", "GENERAL_KNOWLEDGE"}
        or interp.profile in {"CONVERSATION", "GENERAL_KNOWLEDGE"}
        or interp.authority == "NONE"
    ):
        result = _conversation_only_payload(
            text=_conversation_text_for_interpretation(interp, text=text),
            user_message=text,
            at=at,
            corr=corr,
            ctx=ctx,
            planner=_planner_from_interpretation(interp),
            routing=routing,
        )
        conversation.extend(result.items)
        update_context_from_turn_items(ctx, result.items)
        result.context = ctx
        return result

    routed = _select_private_tool(text, interp, ctx)
    if routed is None:
        result = _conversation_only_payload(
            text="I'm not sure how to help with that yet — try asking about your calendar.",
            user_message=text,
            at=at,
            corr=corr,
            ctx=ctx,
            planner="conversation",
            routing=routing,
        )
        conversation.extend(result.items)
        update_context_from_turn_items(ctx, result.items)
        result.context = ctx
        return result

    tool_name, arguments = routed
    if arguments.get("period"):
        ctx.temporal_constraint = str(arguments["period"])

    session = PrivateToolSession(
        state=kernel_session.state,
        context=ctx,
        at=at,
        adapter=adapter,
        user_message=text,
    )
    planned_caps = _private_planned_capabilities(interp, selected_tool=tool_name)
    plan = ExecutionPlan(
        planned_capabilities=planned_caps,
        steps=({"name": tool_name, "arguments": arguments},),
    )
    exec_result = execute_private_tool(session, tool_name, arguments)
    turn_items = [
        {**item, "correlation_id": corr} if item.get("correlation_id") is None else item
        for item in exec_result.turn_items
    ]

    outcome = derive_turn_outcome(
        planned=plan,
        executed_names=[tool_name] if exec_result.ok else [],
        tool_results=[exec_result],
        misdispatched=tool_name == "world.explain",
    )

    trace = LlmTrace(
        path="llm" if routing.get("primary") == "semantic" else "intent_router",
        planner=_planner_from_interpretation(interp),
        user_message=text,
        conversation_state={
            "authority_ceiling": profile.authority_ceiling,
            "capability_contract": private_capability_contract(),
            "request_kind": interp.request_kind,
            "evidence_domain": interp.evidence_domain,
        },
        tools_available=list(private_capability_contract()["allowed"]),
        executed_tool_request=[{"name": tool_name, "arguments": arguments}],
        tool_results=[
            {
                "name": tool_name,
                "ok": exec_result.ok,
                "calendar_items": exec_result.data.get("calendar_items", []),
            }
        ],
        correlation_id=corr,
        routing=routing,
        router_fallback=routing.get("primary") != "semantic",
    )
    trace_payload = attach_kernel_forensics(trace, profile=profile)
    trace_payload = stamp_turn_outcome_on_trace(trace_payload, outcome, tool_name=tool_name)
    _attach_trace(turn_items, trace_payload)

    conversation.extend(turn_items)
    update_context_from_turn_items(ctx, turn_items)
    return TurnResult(
        items=turn_items,
        llm_trace=trace_payload,
        outcome=outcome,
        calendar_facts_used=session.last_calendar_facts,
        context=ctx,
    )


def run_turn(
    *,
    profile: WorldTurnProfile,
    text: str,
    at: str,
    adapter: Any,
    conversation: list[dict[str, Any]],
    context: ConversationContext | None = None,
) -> TurnResult:
    """Unified kernel entry — dispatches by world profile."""
    if profile.world_id == "my_enigma":
        return run_private_turn(
            text=text,
            at=at,
            adapter=adapter,
            conversation=conversation,
            context=context,
        )
    if profile.world_id == "alex_lab":
        raise ValueError(
            "Alex Lab turns use run_alex_turn(); pass llm_enabled and session/state explicitly"
        )
    raise ValueError(f"run_turn not wired for world {profile.world_id!r}")


__all__ = [
    "ExecutionPlan",
    "TurnOutcome",
    "TurnOutcomeStatus",
    "TurnResult",
    "WorldTurnProfile",
    "agent_work_label_from_outcome",
    "attach_kernel_forensics",
    "derive_turn_outcome",
    "run_alex_turn",
    "run_private_turn",
    "run_turn",
    "stamp_turn_outcome_on_trace",
]
