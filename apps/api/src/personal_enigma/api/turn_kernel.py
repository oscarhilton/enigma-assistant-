"""Shared turn kernel — interpret → plan → execute → verify → respond (ADR-040)."""

from __future__ import annotations

import re
from collections.abc import Sequence
from dataclasses import dataclass, field
from typing import Any, Literal
from uuid import uuid4

from personal_enigma.api.build_identity import attach_forensic_provenance
from personal_enigma.api.context_compilation import RequestInterpretation, interpret_request
from personal_enigma.api.conversation_context import (
    ConversationContext,
    assess_request_satisfaction,
    reduce_conversation_capsule,
    update_context_from_turn_items,
)
from personal_enigma.api.demo_orchestrator import LlmTrace, build_intent_router_trace
from personal_enigma.api.demo_tools import ToolExecutionResult
from personal_enigma.api.intent_router import ConversationIntent, ConversationIntentKind
from personal_enigma.api.private_calendar_read import (
    infer_private_calendar_period,
    is_private_agenda_list_request,
)
from personal_enigma.api.private_tools import (
    PrivateToolSession,
    execute_private_tool,
    private_capability_contract,
)
from personal_enigma.attention.projection import AttentionState

TurnOutcomeStatus = Literal[
    "fulfilled",
    "partial",
    "misdispatched",
    "unsupported",
    "source_unavailable",
    "failed",
]

_EXPLICIT_GENERAL_KNOWLEDGE_RE = re.compile(
    r"\b(capital of|who (?:is|was)|what is (?:the )?(?:capital|currency|population|language)"
    r"|how (?:tall|far|old|long|many|much)|when (?:was|did|is)|where is|"
    r"define |meaning of|who invented|what does .{1,40} mean)\b",
    re.IGNORECASE,
)

_PHATIC_SURFACE_RE = re.compile(
    r"^(?:"
    r"yep|yup|yeah|yes|nope|nah|no|ok|okay|k|sure|alright|right|cool|got it|"
    r"sounds good|sounds great|makes sense|perfect|great|awesome|nice|good|"
    r"thanks?|thank you|cheers|no worries|no problem|np|"
    r"lol|haha|heh|wow|oh|ah|hmm|hm|uh|"
    r"im so ready(?: for you)?|i(?:'m| am) so ready(?: for you)?|"
    r"(?:so\s+)?ready(?: for(?: you)?)?|"
    r"let'?s(?: go)?|let us go|"
    r"i(?:'m| am) (?:here|back|ready|set|good|all set)|"
    r"(?:all\s+)?set(?: and ready)?|"
    r"(?:i(?:'m| am) )?pumped|(?:i(?:'m| am) )?excited|"
    r"you there\??|you good\??|still there\??"
    r")[\s!.?,]*$",
    re.IGNORECASE,
)


def _is_explicit_general_knowledge(text: str) -> bool:
    return bool(_EXPLICIT_GENERAL_KNOWLEDGE_RE.search(text))


def _is_phatic_surface(text: str) -> bool:
    stripped = text.strip()
    if _PHATIC_SURFACE_RE.match(stripped):
        return True
    return bool(
        re.search(
            r"\b(?:im so ready(?: for you)?|i(?:'m| am) so ready(?: for you)?)\b",
            stripped,
            re.IGNORECASE,
        )
    )


def _is_underspecified_follow_up(
    text: str,
    resolved: ConversationIntent,
) -> bool:
    """True when a live frame may supply the missing private-world subject."""
    from personal_enigma.api.intent_router import (
        detect_period_follow_up,
        is_after_that_follow_up,
        normalize_utterance,
    )

    if detect_period_follow_up(text) is not None:
        return True
    if is_after_that_follow_up(text):
        return True
    if resolved.kind != ConversationIntentKind.UNKNOWN:
        return True
    if is_private_agenda_list_request(text):
        return True
    if infer_private_calendar_period(text) is not None:
        return True
    normalized = normalize_utterance(text)
    if normalized and len(normalized.split()) <= 3 and not _is_explicit_general_knowledge(text):
        return True
    return False


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


@dataclass(frozen=True)
class _PrivateInterpretSession:
    """Minimal session surface for interpret_request in My Enigma."""

    _context: ConversationContext
    _state: AttentionState

    @property
    def context(self) -> ConversationContext:
        return self._context

    @property
    def state(self) -> AttentionState:
        return self._state


def _effective_intent_kind(
    resolved: ConversationIntent,
    interp: RequestInterpretation,
    ctx: ConversationContext,
) -> ConversationIntentKind:
    if resolved.kind != ConversationIntentKind.UNKNOWN:
        return resolved.kind
    if interp.frame_inherited and ctx.last_intent is not None:
        return ctx.last_intent.kind
    return resolved.kind


def _resolve_private_period(
    text: str,
    resolved: ConversationIntent,
    interp: RequestInterpretation,
    ctx: ConversationContext,
) -> str | None:
    explicit = infer_private_calendar_period(text)
    if explicit is not None:
        return explicit
    if resolved.period is not None:
        return resolved.period.value
    if interp.constraints.period:
        return interp.constraints.period
    return ctx.temporal_constraint


def _private_request_kind(
    *,
    text: str,
    resolved: ConversationIntent,
    interp: RequestInterpretation,
    ctx: ConversationContext,
    tool_name: str,
) -> str | None:
    if interp.request_kind is not None:
        return interp.request_kind
    kind = _effective_intent_kind(resolved, interp, ctx)
    if kind == ConversationIntentKind.AVAILABILITY_QUERY:
        return "agenda"
    if kind == ConversationIntentKind.ATTENTION_QUERY:
        period = _resolve_private_period(text, resolved, interp, ctx)
        return "next_work" if period is None else "agenda"
    if tool_name == "briefing.read":
        return "agenda"
    if tool_name == "availability.check":
        return "agenda"
    if tool_name == "attention.get_current":
        return "next_work"
    return None


def _select_private_tool(
    *,
    text: str,
    resolved: ConversationIntent,
    interp: RequestInterpretation,
    ctx: ConversationContext,
) -> tuple[str, dict[str, Any]] | None:
    """Plan one READ/SUPPORT tool from composed intent + interpret_request."""
    self_contained = (
        is_private_agenda_list_request(text)
        or infer_private_calendar_period(text) is not None
        or resolved.kind
        in {
            ConversationIntentKind.ATTENTION_QUERY,
            ConversationIntentKind.AVAILABILITY_QUERY,
            ConversationIntentKind.NEXT_ACTION_QUERY,
            ConversationIntentKind.HELP_QUERY,
        }
    )
    if (
        interp.evidence_domain not in {"PRIVATE_WORLD"}
        and not interp.frame_inherited
        and not self_contained
    ):
        return None

    explicit_period = infer_private_calendar_period(text)
    if explicit_period is not None and resolved.kind != ConversationIntentKind.AVAILABILITY_QUERY:
        return "briefing.read", {"period": explicit_period}

    kind = _effective_intent_kind(resolved, interp, ctx)
    period = _resolve_private_period(text, resolved, interp, ctx)

    if kind == ConversationIntentKind.AVAILABILITY_QUERY:
        return "availability.check", {"period": period}
    if kind == ConversationIntentKind.ATTENTION_QUERY:
        if period:
            return "briefing.read", {"period": period}
        return "attention.get_current", {}
    if kind == ConversationIntentKind.HELP_QUERY:
        return "world.explain", {}
    if kind == ConversationIntentKind.NEXT_ACTION_QUERY:
        if period:
            return "briefing.read", {"period": period}
        return "attention.get_current", {}
    if interp.request_kind == "agenda" and period:
        return "briefing.read", {"period": period}
    if period:
        return "briefing.read", {"period": period}
    if is_private_agenda_list_request(text):
        return "briefing.read", {"period": period or "this_week"}
    return None


def _reduce_private_capsule(
    *,
    text: str,
    ctx: ConversationContext,
    interp: RequestInterpretation,
    resolved: ConversationIntent,
    tool_name: str,
    ok: bool,
) -> None:
    request_kind = _private_request_kind(
        text=text,
        resolved=resolved,
        interp=interp,
        ctx=ctx,
        tool_name=tool_name,
    )
    satisfaction = assess_request_satisfaction(
        request_kind,  # type: ignore[arg-type]
        [tool_name] if ok else [],
    )
    reduce_conversation_capsule(
        ctx,
        evidence_domain="PRIVATE_WORLD",
        authority=interp.authority if interp.authority != "NONE" else "READ",
        request_kind=request_kind,  # type: ignore[arg-type]
        satisfaction=satisfaction,
        temporal_constraint=_resolve_private_period(text, resolved, interp, ctx),
        scope=interp.constraints.scope,
        source=interp.constraints.source,
        last_capability=tool_name if ok else None,
        repair=bool(interp.frame_inherited and satisfaction != "SATISFIED"),
    )


def _conversation_only_payload(
    *,
    text: str,
    user_message: str,
    at: str,
    corr: str,
    ctx: ConversationContext,
    planner: str,
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
    trace = trace.model_copy(
        update={
            "path": "intent_router",
            "planner": planner,
            "tools_available": [],
            "executed_tool_request": [],
            "tool_results": [],
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
    context: ConversationContext | None,
    silence_attention: Any,
) -> TurnResult:
    """My Enigma turn via shared kernel — interpret_request → plan → execute."""
    from personal_enigma.api.private_conversation import _PREPARE_RE  # noqa: PLC0415

    ctx = context or ConversationContext()
    corr = f"corr-{uuid4().hex}"
    profile = WorldTurnProfile(
        world_id="my_enigma",
        environment="private",
        authority_ceiling="READ_SUPPORT",
    )
    ctx.begin_user_turn()
    conversation.append(
        {"kind": "user_message", "text": text, "at": at, "correlation_id": corr}
    )

    if _PREPARE_RE.search(text):
        result = _conversation_only_payload(
            text=(
                "I can read your calendar and help you think through it — "
                "I can't create or change calendar events yet."
            ),
            user_message=text,
            at=at,
            corr=corr,
            ctx=ctx,
            planner="authority_refusal",
        )
        conversation.extend(result.items)
        update_context_from_turn_items(ctx, result.items)
        result.context = ctx
        return result

    resolved = ctx.compose_intent(text)
    state: AttentionState = silence_attention(at)
    session = _PrivateInterpretSession(_context=ctx, _state=state)
    interp = interpret_request(text, session)  # type: ignore[arg-type]

    if resolved.kind == ConversationIntentKind.GREETING:
        result = _conversation_only_payload(
            text="Hey! Ask me what's on your calendar or what needs your attention.",
            user_message=text,
            at=at,
            corr=corr,
            ctx=ctx,
            planner="conversation",
        )
        conversation.extend(result.items)
        update_context_from_turn_items(ctx, result.items)
        result.context = ctx
        return result

    gk_without_follow_up = (
        interp.evidence_domain == "GENERAL_KNOWLEDGE"
        and not _is_underspecified_follow_up(text, resolved)
    )
    if _is_explicit_general_knowledge(text) or gk_without_follow_up:
        result = _conversation_only_payload(
            text="I don't have general knowledge — try a search engine for that.",
            user_message=text,
            at=at,
            corr=corr,
            ctx=ctx,
            planner="general_knowledge_ejected",
        )
        ctx.capsule = None
        ctx.temporal_constraint = None
        conversation.extend(result.items)
        update_context_from_turn_items(ctx, result.items)
        result.context = ctx
        return result

    if _is_phatic_surface(text) or (
        interp.evidence_domain == "CONVERSATION_ONLY"
        and not _is_underspecified_follow_up(text, resolved)
    ):
        result = _conversation_only_payload(
            text="I'm here — ask me what's on your calendar or what needs your attention.",
            user_message=text,
            at=at,
            corr=corr,
            ctx=ctx,
            planner="conversation",
        )
        conversation.extend(result.items)
        update_context_from_turn_items(ctx, result.items)
        result.context = ctx
        return result

    routed = _select_private_tool(text=text, resolved=resolved, interp=interp, ctx=ctx)
    if routed is None:
        result = _conversation_only_payload(
            text="I'm not sure how to help with that yet — try asking about your calendar.",
            user_message=text,
            at=at,
            corr=corr,
            ctx=ctx,
            planner="conversation",
        )
        conversation.extend(result.items)
        update_context_from_turn_items(ctx, result.items)
        result.context = ctx
        return result

    tool_name, arguments = routed
    if arguments.get("period"):
        ctx.temporal_constraint = str(arguments["period"])

    tool_session = PrivateToolSession(
        state=state,
        context=ctx,
        at=at,
        adapter=adapter,
        user_message=text,
    )
    plan = ExecutionPlan(
        planned_capabilities=(tool_name,),
        steps=({"name": tool_name, "arguments": arguments},),
    )
    exec_result = execute_private_tool(tool_session, tool_name, arguments)
    turn_items = [
        {**item, "correlation_id": corr} if item.get("correlation_id") is None else item
        for item in exec_result.turn_items
    ]

    _reduce_private_capsule(
        text=text,
        ctx=ctx,
        interp=interp,
        resolved=resolved,
        tool_name=tool_name,
        ok=exec_result.ok,
    )

    outcome = derive_turn_outcome(
        planned=plan,
        executed_names=[tool_name] if exec_result.ok else [],
        tool_results=[exec_result],
        misdispatched=tool_name == "world.explain",
    )

    trace = LlmTrace(
        path="intent_router",
        planner="private_calendar_read",
        user_message=text,
        conversation_state={
            "authority_ceiling": profile.authority_ceiling,
            "capability_contract": private_capability_contract(),
            "request_kind": _private_request_kind(
                text=text,
                resolved=resolved,
                interp=interp,
                ctx=ctx,
                tool_name=tool_name,
            ),
            "frame_inherited": interp.frame_inherited,
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
        calendar_facts_used=tool_session.last_calendar_facts,
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
    silence_attention: Any | None = None,
) -> TurnResult:
    """Unified kernel entry — dispatches by world profile."""
    if profile.world_id == "my_enigma":
        from personal_enigma.api import private_conversation as pc  # noqa: PLC0415

        return run_private_turn(
            text=text,
            at=at,
            adapter=adapter,
            conversation=conversation,
            context=context,
            silence_attention=silence_attention or pc._silence_attention,
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
