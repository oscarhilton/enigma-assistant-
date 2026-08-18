"""LLM conversational orchestrator for Demo — interpreter, not truth (ADR-020)."""

from __future__ import annotations

import json
import os
from dataclasses import dataclass
from typing import Any, Literal, Protocol
from uuid import uuid4

from pydantic import BaseModel, Field

from personal_enigma.api.context_compilation import (
    CompiledRemoteContext,
    compile_remote_context,
)
from personal_enigma.api.conversation_context import (
    ConversationContext,
    DialogueTurn,
    apply_named_referent_focus,
    assess_request_satisfaction,
    assistant_visible_text,
    capture_turn_local_location,
    classify_assistant_dialogue_egress,
    project_recent_dialogue_for_egress,
    reduce_conversation_capsule,
    referent_candidates,
    remember_turn_local_constraint,
    update_context_from_turn_items,
)
from personal_enigma.api.demo_assist import AssistPlan
from personal_enigma.api.demo_attestation import ATTESTATION_TOOL
from personal_enigma.api.demo_intents import (
    build_intent_turn,
    format_attention_summary_text,
)
from personal_enigma.api.demo_tools import (
    DENIED_REMOTE_CAPABILITIES,
    DemoToolSession,
    ToolCallRecord,
    ToolExecutionResult,
    bind_authority_arguments,
    execute_tool,
    tool_schemas,
)
from personal_enigma.api.intent_router import (
    ConversationIntent,
    ConversationIntentKind,
    TimeExpression,
    compose_follow_up_intent,
    normalize_utterance,
)
from personal_enigma.api.respond_grounding import apply_respond_grounding_fence
from personal_enigma.api.semantic_bootstrap import (
    compile_with_bootstrap,
    get_semantic_bootstrap,
)
from personal_enigma.api.speech_acts import (
    SpeechAct,
    classify_speech_act,
    dialogue_act_for_speech,
    signals_difficulty,
)
from personal_enigma.attention.projection import AttentionState
from personal_enigma.privacy.egress import (
    CONVERSATION_EGRESS_EXCLUDED,
    CONVERSATION_EGRESS_INCLUDED,
    RemoteSafeContext,
    build_audited_egress_gate,
    get_audited_egress_gate,
)
from personal_enigma.privacy.remote import RemoteInferenceConfig

_PRIVACY_EXCLUDED: tuple[str, ...] = CONVERSATION_EGRESS_EXCLUDED
_ROUTER_UNKNOWN = "I'm not sure I follow."

TracePath = Literal["intent_router", "llm", "fireworks", "openai"]


def _llm_explicitly_disabled() -> bool:
    if os.environ.get("LLM_DISABLED", "").lower() in ("1", "true", "yes"):
        return True
    flag = os.environ.get("ENIGMA_DEMO_LLM_CONVERSATION", "").lower()
    return flag in ("0", "false", "no")


def configured_conversation_provider() -> str | None:
    """Fireworks preferred, OpenAI fallback. None when LLM is forced off or no key."""
    if _llm_explicitly_disabled():
        return None
    if os.environ.get("FIREWORKS_API_KEY"):
        return "fireworks"
    if os.environ.get("OPENAI_API_KEY"):
        return "openai"
    return None


def demo_llm_conversation_enabled() -> bool:
    """True when Demo conversation should route through the C09 orchestrator.

    A configured provider is enough for the live demo front door — no extra flag.
    CI / no-key stays on intent_router unless ENIGMA_DEMO_LLM_CONVERSATION=1.
    ENIGMA_DEMO_LLM_CONVERSATION=0 or LLM_DISABLED=1 forces the router.
    """
    if _llm_explicitly_disabled():
        return False
    flag = os.environ.get("ENIGMA_DEMO_LLM_CONVERSATION", "").lower()
    if flag in ("1", "true", "yes"):
        return True
    return configured_conversation_provider() is not None


def trace_path_for_planner(planner: ConversationLLM) -> TracePath:
    """One fact, derived from the planner — not a parallel debug string."""
    provider = getattr(planner, "_provider", None)
    if provider == "fireworks":
        return "fireworks"
    if provider == "openai":
        return "openai"
    return "llm"


class LlmTrace(BaseModel):
    """Deterministic turn trace — not chain-of-thought (C09 under-bonnet)."""

    path: TracePath
    planner: str
    user_message: str
    conversation_state: dict[str, Any]
    tools_available: list[str] = Field(default_factory=list)
    remote_context_sent: dict[str, Any] | None = None
    model_tool_request: list[dict[str, Any]] = Field(default_factory=list)
    referent_resolution: list[dict[str, Any]] = Field(default_factory=list)
    executed_tool_request: list[dict[str, Any]] = Field(default_factory=list)
    tool_results: list[dict[str, Any]] = Field(default_factory=list)
    model_response: list[dict[str, Any]] = Field(default_factory=list)
    intent_name: str | None = None
    router_fallback: bool = False
    disclosure_id: str | None = None
    disclosure: dict[str, Any] | None = None
    included: list[str] = Field(default_factory=list)
    excluded: list[str] = Field(default_factory=lambda: list(_PRIVACY_EXCLUDED))
    correlation_id: str | None = None


@dataclass(frozen=True)
class OrchestratorTurn:
    turn_items: list[dict[str, Any]]
    tool_calls: list[ToolCallRecord]
    tool_results: list[ToolExecutionResult]
    assist_plan: AssistPlan | None = None
    llm_trace: LlmTrace | None = None


class ConversationLLM(Protocol):
    def select_tools(
        self,
        *,
        user_message: str,
        context_summary: dict[str, Any],
        tools: list[dict[str, Any]],
        correlation_id: str | None = None,
    ) -> list[ToolCallRecord]: ...


def _tools_available() -> list[str]:
    names: list[str] = []
    for schema in tool_schemas():
        fn = schema.get("function") if isinstance(schema, dict) else None
        name = fn.get("name") if isinstance(fn, dict) else None
        if name:
            names.append(str(name))
    return names


def _subject_state(context: ConversationContext) -> dict[str, Any]:
    return {
        "current_subject_id": context.current_subject_id,
        "current_subject_kind": context.current_subject_kind,
        "focus_reason": context.focus_reason,
        "temporal_constraint": context.temporal_constraint,
    }


def _response_preview(turn_items: list[dict[str, Any]]) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    for item in turn_items:
        kind = str(item.get("kind") or "")
        if kind in {"source_quote", "source_quotation", "quoted_message", "note_excerpt"}:
            rows.append({"kind": kind, "text": "[quoted locally]"})
            continue
        text = item.get("text") or item.get("message")
        if text is None and kind == "next_action":
            text = (item.get("action") or {}).get("title")
        if text is None and kind == "assist_proposal":
            text = (item.get("proposal") or {}).get("title")
        if text is None and kind == "attention_item":
            text = (item.get("item") or {}).get("title")
        if text is None and kind == "attention_summary":
            text = _attention_summary_preview(item)
        rows.append({"kind": kind, "text": text})
    return rows


def _attention_summary_preview(item: dict[str, Any]) -> str:
    raw = item.get("text")
    if isinstance(raw, str) and raw.strip() and raw.strip() != "attention_summary":
        return raw.strip()
    state = item.get("state")
    if isinstance(state, dict):
        try:
            return format_attention_summary_text(AttentionState.model_validate(state))
        except (TypeError, ValueError):
            return "Nothing needs you."
    return "Nothing needs you."


def _compact_tool_data(data: dict[str, Any]) -> dict[str, Any]:
    """Structured tool output for debug — ids and scalars, never PRIVATE_RAW."""
    compact: dict[str, Any] = {
        key: value
        for key, value in data.items()
        if key
        not in {
            "turn_items",
            "state",
            "blockers",
            "next_actions",
            "proposal",
            "alternate",
            "calendar_items",
            "attention",
            "body_text",
            "body",
            "text",
            "snippet",
            "quote",
            "raw",
        }
    }
    if "subject_id" in data:
        compact["subject_id"] = data["subject_id"]
    if isinstance(data.get("next_actions"), list):
        compact["next_action_ids"] = [
            row.get("source_candidate_id") or row.get("id")
            for row in data["next_actions"]
            if isinstance(row, dict)
        ]
    if isinstance(data.get("alternate"), dict):
        alternate = data["alternate"]
        compact["alternate_id"] = alternate.get("source_candidate_id") or alternate.get("id")
    elif "alternate" in data:
        compact["alternate"] = data["alternate"]
    if isinstance(data.get("state"), dict):
        state = data["state"]
        compact["needs_you_ids"] = [
            row.get("id") for row in state.get("needs_you", []) if isinstance(row, dict)
        ]
        compact["context_ids"] = [
            row.get("id") for row in state.get("context", []) if isinstance(row, dict)
        ]
        compact["next_action_ids"] = [
            row.get("source_candidate_id") or row.get("id")
            for row in state.get("next_actions", [])
            if isinstance(row, dict)
        ]
    if isinstance(data.get("proposal"), dict):
        compact["proposal_id"] = data["proposal"].get("id")
        compact["proposal_title"] = data["proposal"].get("title")
    if data.get("target_id"):
        compact["target_id"] = data["target_id"]
    if data.get("proposal_id") and "proposal_id" not in compact:
        compact["proposal_id"] = data["proposal_id"]
    if isinstance(data.get("blockers"), list):
        compact["blocker_ids"] = [
            row.get("id") for row in data["blockers"] if isinstance(row, dict)
        ]
    if isinstance(data.get("calendar_items"), list):
        compact["calendar_evidence_ids"] = [
            row.get("evidence_id") for row in data["calendar_items"] if isinstance(row, dict)
        ]
    if data.get("quoted_locally") is not None:
        compact["quoted_locally"] = data["quoted_locally"]
    if data.get("source_id"):
        compact["source_id"] = data["source_id"]
    if data.get("expired") is not None:
        compact["expired"] = data["expired"]
    if data.get("recent_ids"):
        compact["recent_ids"] = data["recent_ids"]
    if data.get("channel"):
        compact["channel"] = data["channel"]
    return compact


def build_llm_trace(
    *,
    path: TracePath,
    planner: str,
    user_message: str,
    conversation_state: dict[str, Any],
    turn_items: list[dict[str, Any]],
    tool_calls: list[ToolCallRecord] | None = None,
    tool_results: list[ToolExecutionResult] | None = None,
    intent_name: str | None = None,
    router_fallback: bool = False,
    remote_context_sent: dict[str, Any] | None = None,
    disclosure: dict[str, Any] | None = None,
    disclosure_id: str | None = None,
    correlation_id: str | None = None,
    referent_resolution: list[dict[str, Any]] | None = None,
    executed_tool_request: list[ToolCallRecord] | None = None,
    tools_available: list[str] | None = None,
) -> LlmTrace:
    included: list[str] = []
    excluded: list[str] = list(_PRIVACY_EXCLUDED)
    if isinstance(disclosure, dict):
        if disclosure.get("included"):
            included = [str(item) for item in disclosure["included"]]
        if disclosure.get("excluded"):
            excluded = [str(item) for item in disclosure["excluded"]]
    if not included:
        included = list(CONVERSATION_EGRESS_INCLUDED) if remote_context_sent else []
    return LlmTrace(
        path=path,
        planner=planner,
        user_message=user_message,
        conversation_state=conversation_state,
        tools_available=(
            list(tools_available) if tools_available is not None else _tools_available()
        ),
        remote_context_sent=remote_context_sent,
        model_tool_request=[call.model_dump(mode="json") for call in tool_calls or []],
        referent_resolution=list(referent_resolution or []),
        executed_tool_request=[
            call.model_dump(mode="json") for call in executed_tool_request or []
        ],
        tool_results=[
            {
                "name": result.name,
                "ok": result.ok,
                "data": _compact_tool_data(result.data),
            }
            for result in tool_results or []
        ],
        model_response=_response_preview(turn_items),
        intent_name=intent_name,
        router_fallback=router_fallback,
        disclosure_id=disclosure_id,
        disclosure=disclosure,
        included=included,
        excluded=excluded,
        correlation_id=correlation_id,
    )


def build_intent_router_trace(
    *,
    user_message: str,
    conversation_state: dict[str, Any],
    last_intent: ConversationIntent | None,
    turn_items: list[dict[str, Any]],
    correlation_id: str | None = None,
) -> LlmTrace:
    resolved = compose_follow_up_intent(user_message, last_intent)
    return build_llm_trace(
        path="intent_router",
        planner="intent_router",
        user_message=user_message,
        conversation_state=conversation_state,
        turn_items=turn_items,
        intent_name=resolved.kind.value,
        router_fallback=True,
        correlation_id=correlation_id,
    )


def context_summary(
    context: ConversationContext,
    state: AttentionState | None = None,
) -> dict[str, Any]:
    last = context.last_intent
    summary: dict[str, Any] = {
        "current_attention_item_id": context.current_attention_item_id,
        "current_next_action_id": context.current_next_action_id,
        "current_subject_id": context.current_subject_id,
        "current_subject_kind": context.current_subject_kind,
        "focus_reason": context.focus_reason,
        "temporal_constraint": context.temporal_constraint,
        "current_assist_proposal_id": context.current_assist_proposal_id,
        "pending_dialogue_act": context.pending_dialogue_act,
        "pending_confirmation": (
            {
                "kind": context.pending_confirmation.kind,
                "subject_id": context.pending_confirmation.subject_id,
            }
            if context.pending_confirmation is not None
            else None
        ),
        "turn_local_constraints": [
            {
                "key": row.key,
                "value": row.value,
                "applies_to": row.applies_to,
            }
            for row in context.turn_local_constraints
        ],
        "suppressed_next_action_ids": list(context.suppressed_next_action_ids),
        "last_intent_kind": last.kind.value if last is not None else None,
        "last_period": last.period.value if last is not None and last.period else None,
        "recent_dialogue": project_recent_dialogue_for_egress(context.recent_dialogue),
    }
    if state is not None:
        summary["referent_candidates"] = referent_candidates(state)
        summary["simulated_time"] = state.simulated_time
        summary["attention_count"] = len(state.needs_you) + len(state.context)
    return summary


def _planner_wire_context(
    user_message: str,
    session: DemoToolSession,
    *,
    bootstrap: Any | None = None,
) -> tuple[CompiledRemoteContext, dict[str, Any]]:
    """Compile the remote working set; keep last_intent locally for the oracle."""
    interpreter = bootstrap if bootstrap is not None else get_semantic_bootstrap()
    if interpreter is not None:
        compiled = compile_with_bootstrap(user_message, session, interpreter)
    else:
        compiled = compile_remote_context(user_message, session)
    local = context_summary(session.context, session.state)
    wire = compiled.wire_context()
    wire["last_intent_kind"] = local.get("last_intent_kind")
    wire["last_period"] = local.get("last_period")
    wire["context_manifest"] = compiled.manifest.model_dump(mode="json")
    return compiled, wire




def _reduce_capsule_after_turn(
    session: DemoToolSession,
    compiled: CompiledRemoteContext,
    results: list[ToolExecutionResult],
) -> None:
    ok_names = [row.name for row in results if row.ok]
    kind = compiled.working_set.get("request_kind")
    satisfaction = assess_request_satisfaction(kind, ok_names)
    reduce_conversation_capsule(
        session.context,
        evidence_domain=compiled.evidence_domain,
        authority=compiled.authority,
        request_kind=kind,
        satisfaction=satisfaction,
        temporal_constraint=compiled.working_set.get("temporal_constraint"),
        scope=compiled.working_set.get("scope"),
        source=compiled.working_set.get("source"),
        last_capability=ok_names[-1] if ok_names else None,
        repair=bool(compiled.working_set.get("frame_inherited") and satisfaction != "SATISFIED"),
    )

def _matches_start_todays_action(normalized: str) -> bool:
    return (
        "start" in normalized
        and ("today" in normalized or "todays" in normalized)
        and "action" in normalized
    )


def _matches_subject_why(normalized: str) -> bool:
    return "why" in normalized and "do this" in normalized


def _matches_wrong_referent_correction(normalized: str) -> bool:
    return "different task" in normalized or "completely different" in normalized


def _matches_anything_else(normalized: str) -> bool:
    return normalized in {"anything else", "something else"} or normalized.startswith(
        "anything else"
    )


def _last_intent_from_summary(summary: dict[str, Any]) -> ConversationIntent | None:
    kind_raw = summary.get("last_intent_kind")
    if not kind_raw:
        return None
    period_raw = summary.get("last_period")
    period = TimeExpression(period_raw) if period_raw else None
    return ConversationIntent(kind=ConversationIntentKind(kind_raw), period=period)


def _period_from_intent(period: TimeExpression | None) -> str | None:
    return period.value if period is not None else None


def tool_calls_from_intent(
    text: str,
    last_intent: ConversationIntent | None = None,
) -> list[ToolCallRecord]:
    """Map utterance → tools using frozen intent_router plus orchestrator paraphrases."""
    if classify_speech_act(text) == "USER_ATTESTATION":
        return [ToolCallRecord(name=ATTESTATION_TOOL)]
    act = classify_speech_act(text)
    if act == "SUPPORT":
        return [ToolCallRecord(name="world.explain")]
    if act in {"PREPARE", "ACTION_REQUEST"}:
        return [ToolCallRecord(name="assist.propose")]
    normalized = normalize_utterance(text)

    # C09 subject-referent phrases — orchestrator only; intent_router stays frozen.
    if _matches_start_todays_action(normalized):
        return [ToolCallRecord(name="assist.propose")]
    if _matches_subject_why(normalized):
        return [ToolCallRecord(name="world.explain")]
    if _matches_wrong_referent_correction(normalized):
        return [ToolCallRecord(name="world.explain", arguments={"recover": True})]
    if _matches_anything_else(normalized):
        return [ToolCallRecord(name="next_action.get_alternatives")]

    resolved_preview = compose_follow_up_intent(text, last_intent)
    if resolved_preview.requested_count is not None:
        # Cardinality-honest priorities — deterministic handler, not attention.get_current.
        return []

    # Orchestrator-only paraphrases — intent_router stays frozen.
    if normalized in {"anything urgent", "what needs me"}:
        return [ToolCallRecord(name="attention.get_current")]
    if normalized.startswith("how long") and "take" in normalized:
        return [ToolCallRecord(name="referent.get_duration")]

    resolved = compose_follow_up_intent(text, last_intent)
    kind = resolved.kind

    if kind == ConversationIntentKind.GREETING:
        return []

    if kind == ConversationIntentKind.ATTENTION_QUERY:
        if resolved.period is not None:
            return [
                ToolCallRecord(
                    name="agenda.get",
                    arguments={"period": resolved.period.value},
                )
            ]
        return [ToolCallRecord(name="attention.get_current")]

    if kind == ConversationIntentKind.NEXT_ACTION_QUERY:
        if resolved.period is not None:
            return [
                ToolCallRecord(
                    name="agenda.get",
                    arguments={"period": resolved.period.value},
                )
            ]
        return [ToolCallRecord(name="next_action.get")]

    if kind == ConversationIntentKind.REJECT_NEXT_ACTION:
        return [ToolCallRecord(name="next_action.reject")]

    if kind == ConversationIntentKind.ALTERNATE_TASK_QUERY:
        return [ToolCallRecord(name="next_action.get_alternatives")]

    if kind == ConversationIntentKind.DURATION_QUERY:
        return [ToolCallRecord(name="referent.get_duration")]

    if kind == ConversationIntentKind.TIME_FIT_QUERY:
        return [ToolCallRecord(name="availability.check", arguments={"duration_minutes": 30})]

    if kind == ConversationIntentKind.AVAILABILITY_QUERY:
        return [
            ToolCallRecord(
                name="availability.check",
                arguments={"period": _period_from_intent(resolved.period)},
            )
        ]

    if kind == ConversationIntentKind.CHANGES_QUERY:
        return [ToolCallRecord(name="world.get_changes")]

    if kind == ConversationIntentKind.WAITING_ON_QUERY:
        return [ToolCallRecord(name="world.get_blockers")]

    if kind == ConversationIntentKind.HELP_QUERY:
        return [ToolCallRecord(name="assist.propose")]

    if kind == ConversationIntentKind.WHY_QUERY:
        return [ToolCallRecord(name="attention.get_current")]

    if kind == ConversationIntentKind.CAN_WAIT_QUERY:
        return [ToolCallRecord(name="world.get_blockers")]

    return []


class IntentOracleLLM:
    """Deterministic tool planner — uses intent_router, not remote inference."""

    uses_router_for_empty_tools = True

    def select_tools(
        self,
        *,
        user_message: str,
        context_summary: dict[str, Any],
        tools: list[dict[str, Any]],
        correlation_id: str | None = None,
    ) -> list[ToolCallRecord]:
        last = _last_intent_from_summary(context_summary)
        del tools, correlation_id
        return tool_calls_from_intent(user_message, last_intent=last)


class CompromisedLLM:
    """Test hook — simulates a compromised remote model returning attacker tool calls."""

    def __init__(self, *, malicious_calls: list[tuple[str, dict[str, Any]]]) -> None:
        self._malicious_calls = malicious_calls

    def select_tools(
        self,
        *,
        user_message: str,
        context_summary: dict[str, Any],
        tools: list[dict[str, Any]],
        correlation_id: str | None = None,
    ) -> list[ToolCallRecord]:
        del user_message, context_summary, tools, correlation_id
        return [
            ToolCallRecord.model_construct(name=name, arguments=arguments)
            for name, arguments in self._malicious_calls
        ]


class EgressConversationLLM:
    """Provider-neutral tool planner via AuditedEgressGate (ADR-020 / SEC-02).

    Live C09 proof uses Fireworks through the same gate *and* disclosure store
    as ``GET /private/disclosure/recent``. OpenAI remains an explicit fallback.
    """

    def __init__(
        self,
        *,
        provider: str = "fireworks",
        api_key: str | None = None,
        model: str | None = None,
        fallback_to_oracle: bool = True,
        gate: Any | None = None,
    ) -> None:
        self._provider = provider
        if api_key is not None:
            self._api_key = api_key
        elif provider == "fireworks":
            self._api_key = os.environ.get("FIREWORKS_API_KEY", "")
        else:
            self._api_key = os.environ.get("OPENAI_API_KEY", "")
        if model is not None:
            self._model = model
        elif provider == "fireworks":
            self._model = os.environ.get(
                "FIREWORKS_MODEL", "accounts/fireworks/models/gpt-oss-120b"
            )
        else:
            self._model = os.environ.get("ENIGMA_DEMO_LLM_MODEL", "gpt-4o-mini")
        self._fallback_to_oracle = fallback_to_oracle
        self._gate = gate
        self.last_gate: Any | None = None
        self.last_trace_egress: dict[str, Any] | None = None
        self.last_conversational_text: str | None = None

    def _resolve_gate(self) -> Any:
        if self._gate is not None:
            return self._gate
        shared = get_audited_egress_gate()
        kwargs: dict[str, Any] = {
            "remote_config": RemoteInferenceConfig(enabled=True),
            "disclosure_store": shared.disclosure_store,
        }
        if self._provider == "fireworks":
            kwargs["fireworks_api_key"] = self._api_key
        else:
            kwargs["openai_api_key"] = self._api_key
        return build_audited_egress_gate(**kwargs)

    def _record_egress(self, remote_ctx: RemoteSafeContext, egress: Any) -> None:
        disclosure = getattr(egress, "disclosure", None)
        user_content = _user_content_from_wire(remote_ctx.wire_body)
        if disclosure is None:
            self.last_trace_egress = {"remote_context_sent": user_content}
            return
        self.last_trace_egress = {
            "disclosure_id": disclosure.id,
            "disclosure": disclosure.model_dump(mode="json"),
            "remote_context_sent": user_content,
            "correlation_id": disclosure.correlation_id,
        }

    def _oracle_or_empty(
        self,
        user_message: str,
        summary: dict[str, Any],
    ) -> list[ToolCallRecord]:
        if not self._fallback_to_oracle:
            return []
        last = _last_intent_from_summary(summary)
        return tool_calls_from_intent(user_message, last_intent=last)

    def select_tools(
        self,
        *,
        user_message: str,
        context_summary: dict[str, Any],
        tools: list[dict[str, Any]],
        correlation_id: str | None = None,
    ) -> list[ToolCallRecord]:
        self.last_trace_egress = None
        self.last_gate = None
        self.last_conversational_text = None
        if not self._api_key:
            return self._oracle_or_empty(user_message, context_summary)

        remote_ctx = RemoteSafeContext.for_conversation_orchestrator(
            user_message=user_message,
            context_summary=context_summary,
            tools=tools,
            model=self._model,
            provider=self._provider,
            denied_capabilities=list(DENIED_REMOTE_CAPABILITIES),
            system_prompt=(
                context_summary.get("system_prompt")
                if isinstance(context_summary.get("system_prompt"), str)
                else None
            ),
            request_profile=(
                context_summary.get("request_profile")
                if isinstance(context_summary.get("request_profile"), str)
                else None
            ),
            context_manifest=(
                context_summary.get("context_manifest")
                if isinstance(context_summary.get("context_manifest"), dict)
                else None
            ),
        )
        gate = self._resolve_gate()
        self.last_gate = gate
        egress = gate.submit(
            remote_ctx,
            purpose="conversation.orchestrate",
            correlation_id=correlation_id,
            max_output_tokens=1024,
        )
        self._record_egress(remote_ctx, egress)
        if not egress.sent or egress.response is None:
            return self._oracle_or_empty(user_message, context_summary)

        try:
            message = json.loads(egress.response.text)
        except json.JSONDecodeError:
            return self._oracle_or_empty(user_message, context_summary)

        raw_calls = message.get("tool_calls") or []
        if not raw_calls:
            legacy = message.get("function_call")
            if isinstance(legacy, dict):
                raw_calls = [{"function": legacy}]
        calls: list[ToolCallRecord] = []
        for row in raw_calls:
            fn = row.get("function") or {}
            name = fn.get("name")
            if not name:
                continue
            args_raw = fn.get("arguments") or "{}"
            try:
                arguments = json.loads(args_raw) if isinstance(args_raw, str) else dict(args_raw)
            except json.JSONDecodeError:
                arguments = {}
            calls.append(ToolCallRecord(name=name, arguments=arguments))  # type: ignore[arg-type]
        self.last_conversational_text = _message_content_text(message)
        if not calls:
            # Successful model turn with no tools = ordinary conversation, not oracle.
            return []
        return calls


class OpenAIConversationLLM(EgressConversationLLM):
    """OpenAI Chat Completions with function calling — demo-safe tool payloads only."""

    def __init__(
        self,
        *,
        api_key: str | None = None,
        model: str | None = None,
        base_url: str = "https://api.openai.com/v1",
        timeout_s: float = 45.0,
        fallback_to_oracle: bool = True,
        gate: Any | None = None,
    ) -> None:
        del base_url, timeout_s
        super().__init__(
            provider="openai",
            api_key=api_key,
            model=model,
            fallback_to_oracle=fallback_to_oracle,
            gate=gate,
        )


def _default_llm() -> ConversationLLM:
    if not demo_llm_conversation_enabled():
        return IntentOracleLLM()
    if os.environ.get("FIREWORKS_API_KEY"):
        return EgressConversationLLM(provider="fireworks")
    if os.environ.get("OPENAI_API_KEY"):
        return OpenAIConversationLLM()
    return IntentOracleLLM()


_LLM_OVERRIDE: ConversationLLM | None = None


def set_conversation_llm(llm: ConversationLLM | None) -> None:
    global _LLM_OVERRIDE
    _LLM_OVERRIDE = llm


def get_conversation_llm() -> ConversationLLM:
    if _LLM_OVERRIDE is not None:
        return _LLM_OVERRIDE
    return _default_llm()


def _no_tool_turn(at: str, text: str) -> list[dict[str, Any]]:
    return [{"kind": "enigma_message", "text": text, "at": at}]


def _planner_egress(planner: ConversationLLM) -> dict[str, Any]:
    raw = getattr(planner, "last_trace_egress", None)
    return raw if isinstance(raw, dict) else {}


def _user_content_from_wire(wire_body: dict[str, Any]) -> dict[str, Any]:
    for message in wire_body.get("messages") or []:
        if not isinstance(message, dict) or message.get("role") != "user":
            continue
        raw = message.get("content")
        if isinstance(raw, dict):
            return raw
        if isinstance(raw, str):
            try:
                parsed = json.loads(raw)
            except json.JSONDecodeError:
                return {"text": raw}
            if isinstance(parsed, dict):
                return parsed
    return {}


def _message_content_text(message: dict[str, Any]) -> str | None:
    content = message.get("content")
    if isinstance(content, str) and content.strip():
        return content.strip()
    if isinstance(content, list):
        parts: list[str] = []
        for part in content:
            if isinstance(part, str) and part.strip():
                parts.append(part.strip())
            elif isinstance(part, dict) and isinstance(part.get("text"), str):
                text = part["text"].strip()
                if text:
                    parts.append(text)
        blob = " ".join(parts).strip()
        return blob or None
    return None


def _ordinary_conversation_turn(
    at: str,
    text: str | None,
    *,
    session: DemoToolSession | None = None,
    compiled: CompiledRemoteContext | None = None,
) -> list[dict[str, Any]]:
    body = text.strip() if isinstance(text, str) and text.strip() else "Okay."
    if body == _ROUTER_UNKNOWN:
        body = "Okay."
    if session is not None and compiled is not None:
        body = apply_respond_grounding_fence(
            body,
            context=session.context,
            evidence_domain=compiled.evidence_domain,
            authority=compiled.authority,
            tool_names=compiled.tool_names,
        )
    return _no_tool_turn(at, body)


def _duration_is_the_answer(normalized: str) -> bool:
    return "how long" in normalized or "how much time" in normalized


def _schedule_utterance_kind(normalized: str) -> str | None:
    """when / now — duration is evidence, not the answer. None = do not compose."""
    compact = normalized.replace("...", " ").replace("…", " ")
    compact = " ".join(compact.split())
    if _duration_is_the_answer(compact):
        return None
    if compact in {"like now", "like now?", "now", "now?"} or "like now" in compact:
        return "now"
    if "when should" in compact or "when can" in compact or "when do i" in compact:
        return "when"
    return None


def compose_follow_up_tools(
    user_message: str,
    context: ConversationContext,
    results: list[ToolExecutionResult],
) -> list[ToolCallRecord]:
    """Continue after an intermediate fact until the user's question is answered.

    Duration estimates how long; they asked when / whether now. Enigma composes
    availability.check — not a second LLM personality, not a prompt hint.
    """
    if any(result.name == "availability.check" for result in results):
        return []
    duration = next(
        (result for result in results if result.name == "referent.get_duration" and result.ok),
        None,
    )
    if duration is None:
        return []
    minutes = duration.data.get("estimated_minutes")
    if not isinstance(minutes, int) or minutes <= 0:
        return []
    kind = _schedule_utterance_kind(normalize_utterance(user_message))
    if kind is None:
        return []
    arguments: dict[str, Any] = {"duration_minutes": minutes}
    if kind == "when" and context.temporal_constraint:
        arguments["period"] = context.temporal_constraint
    return [ToolCallRecord(name="availability.check", arguments=arguments)]


def _empty_horizon_result(result: ToolExecutionResult) -> bool:
    if result.name != "agenda.get":
        return False
    data = result.data
    return bool(data.get("empty_horizon")) or (
        not data.get("calendar_items")
        and not data.get("attention")
        and not data.get("next_actions")
    )


def _stamp_correlation(items: list[dict[str, Any]], correlation_id: str) -> list[dict[str, Any]]:
    stamped: list[dict[str, Any]] = []
    for item in items:
        if item.get("correlation_id"):
            stamped.append(item)
        else:
            stamped.append({**item, "correlation_id": correlation_id})
    return stamped


def _enigma_actions(results: list[ToolExecutionResult]) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    for result in results:
        denied = bool(result.data.get("denied")) if isinstance(result.data, dict) else False
        if denied:
            rows.append(
                {
                    "name": result.name,
                    "effect": "denied",
                    "reason": result.data.get("reason") if isinstance(result.data, dict) else None,
                    "side_effect": False,
                    "ok": False,
                }
            )
            continue
        side_effect = result.ok and result.name in {ATTESTATION_TOOL, "assist.approve"}
        rows.append(
            {
                "name": result.name,
                "effect": "allowed" if result.ok else "no_side_effect",
                "side_effect": side_effect,
                "ok": result.ok,
            }
        )
    return rows


def _attach_turn_outcome(
    planner: ConversationLLM,
    *,
    disclosure_id: str | None,
    tool_calls: list[ToolCallRecord],
    tool_results: list[ToolExecutionResult],
) -> None:
    if not disclosure_id:
        return
    gate = getattr(planner, "last_gate", None) or get_audited_egress_gate()
    attach = getattr(gate, "attach_turn_outcome", None)
    if attach is None:
        return
    tool_trace = [
        {
            "request": call.model_dump(mode="json"),
            "result": {
                "name": result.name,
                "ok": result.ok,
                "data": _compact_tool_data(result.data),
            },
        }
        for call, result in zip(tool_calls, tool_results, strict=False)
    ]
    attach(
        disclosure_id,
        tool_trace=tool_trace,
        enigma_actions=_enigma_actions(tool_results),
    )
    egress = _planner_egress(planner)
    disclosure = egress.get("disclosure")
    if isinstance(disclosure, dict):
        for row in gate.recent_disclosures(limit=50):
            if row.id == disclosure_id:
                egress["disclosure"] = row.model_dump(mode="json")
                break


def apply_speech_act_constitution(
    calls: list[ToolCallRecord],
    speech_act: SpeechAct,
    utterance: str,
) -> list[ToolCallRecord]:
    """Enforce the Assist funnel. Never skip toward more authority.

    UNDERSTAND → SUPPORT → PREPARE → PROPOSE → APPROVE → EXECUTE

    Distress may increase supportiveness, never authority.
    Ambiguous help requests default to the least-authoritative useful
    interpretation.
    """
    if speech_act == "USER_ATTESTATION":
        attest = [call for call in calls if call.name == ATTESTATION_TOOL]
        return attest or [ToolCallRecord(name=ATTESTATION_TOOL)]

    propose_approve = frozenset({"assist.propose", "assist.approve"})
    if speech_act == "SUPPORT" or (
        signals_difficulty(utterance) and speech_act not in {"PREPARE", "ACTION_REQUEST"}
    ):
        remaining = [call for call in calls if call.name not in propose_approve]
        return remaining or [ToolCallRecord(name="world.explain")]

    if speech_act == "PREPARE":
        remaining = [call for call in calls if call.name != "assist.approve"]
        if any(call.name == "assist.propose" for call in remaining):
            return remaining
        return [ToolCallRecord(name="assist.propose")]

    if speech_act == "ACTION_REQUEST":
        remaining = [call for call in calls if call.name != "assist.approve"]
        if any(call.name == "assist.propose" for call in remaining):
            return remaining
        return remaining or [ToolCallRecord(name="assist.propose")]

    return calls


def apply_attestation_constitution(
    calls: list[ToolCallRecord],
    speech_act: SpeechAct,
    utterance: str = "",
) -> list[ToolCallRecord]:
    """Back-compat wrapper — full funnel lives in ``apply_speech_act_constitution``."""
    return apply_speech_act_constitution(calls, speech_act, utterance)


def _assistant_dialogue_act(tool_names: list[str], speech_act: SpeechAct) -> str:
    if ATTESTATION_TOOL in tool_names:
        return "acknowledgement"
    if "assist.propose" in tool_names:
        return "prepare"
    if "assist.approve" in tool_names:
        return "approval"
    if any(
        name.startswith(("next_action.", "attention.", "agenda.", "availability.", "world."))
        for name in tool_names
    ):
        return "world_answer"
    if speech_act == "QUESTION":
        return "answer"
    return "ordinary_conversation"


def record_turn_dialogue(
    session: DemoToolSession,
    *,
    user_message: str,
    turn_items: list[dict[str, Any]],
    speech_act: SpeechAct,
    tool_names: list[str],
) -> None:
    """Append this exchange to bounded recent_dialogue after the turn is done.

    The current user_message is sent separately; recent_dialogue is *prior* working
    memory on the next turn.
    """
    subject = session.context.current_subject_id
    session.context.remember_dialogue_turn(
        DialogueTurn(
            role="user",
            text=user_message,
            act=dialogue_act_for_speech(speech_act),
            subject_id=subject,
            egress_classification="remote_safe",
        )
    )
    visible = assistant_visible_text(turn_items)
    classification, summary = classify_assistant_dialogue_egress(turn_items, visible)
    session.context.remember_dialogue_turn(
        DialogueTurn(
            role="assistant",
            text=visible,
            act=_assistant_dialogue_act(tool_names, speech_act),
            subject_id=subject,
            egress_classification=classification,
            summary=summary,
        )
    )


def run_orchestrator_turn(
    *,
    user_message: str,
    session: DemoToolSession,
    llm: ConversationLLM | None = None,
    correlation_id: str | None = None,
    bootstrap: Any | None = None,
) -> OrchestratorTurn:
    """Plan tools via LLM, execute against Enigma core, return structured turn items."""
    at = session.at
    corr = correlation_id or f"corr-{uuid4().hex}"
    session.user_message = user_message
    session.context.begin_user_turn()
    apply_named_referent_focus(
        session.context,
        user_message,
        referent_candidates(session.state),
    )
    location = capture_turn_local_location(user_message)
    if location:
        remember_turn_local_constraint(
            session.context,
            key="location",
            value=location,
            applies_to=session.context.current_subject_id,
        )
    normalized = normalize_utterance(user_message)
    conversation_state = _subject_state(session.context)
    resolved = compose_follow_up_intent(user_message, session.context.last_intent)
    if resolved.period is not None:
        session.context.temporal_constraint = resolved.period.value
    speech_act = classify_speech_act(user_message)
    compiled, wire = _planner_wire_context(user_message, session, bootstrap=bootstrap)

    if normalized in {"hey", "hi", "hello"}:
        turn_items = _stamp_correlation(_no_tool_turn(at, "Hey. What's up?"), corr)
        record_turn_dialogue(
            session,
            user_message=user_message,
            turn_items=turn_items,
            speech_act=speech_act,
            tool_names=[],
        )
        return OrchestratorTurn(
            turn_items=turn_items,
            tool_calls=[],
            tool_results=[],
            llm_trace=build_llm_trace(
                path="llm",
                planner="greeting",
                user_message=user_message,
                conversation_state=conversation_state,
                turn_items=turn_items,
                intent_name=resolved.kind.value,
                correlation_id=corr,
                tools_available=compiled.tool_names,
            ),
        )

    planner = llm or get_conversation_llm()
    planner_path = trace_path_for_planner(planner)
    calls = planner.select_tools(
        user_message=user_message,
        context_summary=wire,
        tools=compiled.tools,
        correlation_id=corr,
    )
    calls = apply_speech_act_constitution(calls, speech_act, user_message)
    egress = _planner_egress(planner)

    if not calls:
        use_router = getattr(planner, "uses_router_for_empty_tools", False)
        if use_router:
            turn_items, assist_plan = build_intent_turn(
                user_message,
                session.state,
                at=at,
                checkpoint_id=session.checkpoint_id,
                prior_state=session.prior_state,
                conversation=session.conversation,
                completed_item_ids=session.completed_item_ids,
                conversation_context=session.context,
            )
            router_fallback = True
        else:
            model_text = getattr(planner, "last_conversational_text", None)
            turn_items = _ordinary_conversation_turn(
                at,
                model_text if isinstance(model_text, str) else None,
                session=session,
                compiled=compiled,
            )
            assist_plan = None
            router_fallback = False
        turn_items = _stamp_correlation(turn_items, corr)
        update_context_from_turn_items(session.context, turn_items)
        record_turn_dialogue(
            session,
            user_message=user_message,
            turn_items=turn_items,
            speech_act=speech_act,
            tool_names=[],
        )
        _reduce_capsule_after_turn(session, compiled, [])
        _attach_turn_outcome(
            planner,
            disclosure_id=egress.get("disclosure_id"),
            tool_calls=[],
            tool_results=[],
        )
        egress = _planner_egress(planner)
        return OrchestratorTurn(
            turn_items=turn_items,
            tool_calls=[],
            tool_results=[],
            assist_plan=assist_plan,
            llm_trace=build_llm_trace(
                path=planner_path,
                planner=type(planner).__name__,
                user_message=user_message,
                conversation_state=conversation_state,
                turn_items=turn_items,
                intent_name=resolved.kind.value,
                router_fallback=router_fallback,
                remote_context_sent=egress.get("remote_context_sent"),
                disclosure=egress.get("disclosure"),
                disclosure_id=egress.get("disclosure_id"),
                correlation_id=corr,
                tools_available=compiled.tool_names,
            ),
        )

    turn_items: list[dict[str, Any]] = []
    results: list[ToolExecutionResult] = []
    assist_plan: AssistPlan | None = None
    executed_calls: list[ToolCallRecord] = []
    resolutions: list[dict[str, Any]] = []

    for call in calls:
        executed_args, resolution = bind_authority_arguments(
            session, call.name, call.arguments, user_message=user_message
        )
        if resolution is not None:
            resolutions.append(resolution)
        executed_call = call.model_copy(update={"arguments": executed_args})
        executed_calls.append(executed_call)
        result = execute_tool(session, executed_call.name, executed_call.arguments)  # type: ignore[arg-type]
        results.append(result)
        turn_items.extend(result.turn_items)
        if result.assist_plan is not None:
            proposal_id = result.assist_plan["proposal_id"]
            assist_plan = session.pending_assists.get(proposal_id)
        if result.name == "assist.approve" and result.ok:
            break

    composed = compose_follow_up_tools(user_message, session.context, results)
    for call in composed:
        executed_args, resolution = bind_authority_arguments(
            session, call.name, call.arguments, user_message=user_message
        )
        if resolution is not None:
            resolutions.append(resolution)
        executed_call = call.model_copy(update={"arguments": executed_args})
        executed_calls.append(executed_call)
        result = execute_tool(session, executed_call.name, executed_call.arguments)  # type: ignore[arg-type]
        results.append(result)
        turn_items.extend(result.turn_items)
        if result.assist_plan is not None:
            proposal_id = result.assist_plan["proposal_id"]
            assist_plan = session.pending_assists.get(proposal_id)

    if any(_empty_horizon_result(result) for result in results):
        turn_items = [
            item
            for item in turn_items
            if item.get("kind") not in {"attention_item", "next_action", "attention_summary"}
        ]

    turn_items = _stamp_correlation(turn_items, corr)
    session.context.remember_intent(resolved)
    update_context_from_turn_items(session.context, turn_items)
    record_turn_dialogue(
        session,
        user_message=user_message,
        turn_items=turn_items,
        speech_act=speech_act,
        tool_names=[call.name for call in executed_calls],
    )
    _reduce_capsule_after_turn(session, compiled, results)
    _attach_turn_outcome(
        planner,
        disclosure_id=egress.get("disclosure_id"),
        tool_calls=executed_calls,
        tool_results=results,
    )
    egress = _planner_egress(planner)
    return OrchestratorTurn(
        turn_items=turn_items,
        tool_calls=calls + composed,
        tool_results=results,
        assist_plan=assist_plan,
        llm_trace=build_llm_trace(
            path=planner_path,
            planner=type(planner).__name__,
            user_message=user_message,
            conversation_state=conversation_state,
            turn_items=turn_items,
            tool_calls=calls + composed,
            tool_results=results,
            intent_name=resolved.kind.value,
            remote_context_sent=egress.get("remote_context_sent"),
            disclosure=egress.get("disclosure"),
            disclosure_id=egress.get("disclosure_id"),
            correlation_id=corr,
            referent_resolution=resolutions,
            executed_tool_request=executed_calls,
            tools_available=compiled.tool_names,
        ),
    )


__all__ = [
    "CompromisedLLM",
    "ConversationLLM",
    "EgressConversationLLM",
    "IntentOracleLLM",
    "LlmTrace",
    "OpenAIConversationLLM",
    "OrchestratorTurn",
    "apply_attestation_constitution",
    "apply_speech_act_constitution",
    "build_intent_router_trace",
    "build_llm_trace",
    "compose_follow_up_tools",
    "configured_conversation_provider",
    "context_summary",
    "demo_llm_conversation_enabled",
    "get_conversation_llm",
    "run_orchestrator_turn",
    "set_conversation_llm",
    "tool_calls_from_intent",
    "trace_path_for_planner",
]
