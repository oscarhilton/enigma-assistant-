"""Semantic bootstrap — the model interprets language; the compiler grants context.

ADR-031. This layer is not an amendment to the ADR-029 independent-axes compiler
and not a new ``interpret_request`` phrasebook. Capsule continuity is ADR-030.

The capsule carries continuity.
The bootstrap interprets language.
The compiler grants context.
The world establishes truth.

The bootstrap may improve comprehension. It may not improve its own authority.
"""

from __future__ import annotations

import json
import os
from dataclasses import dataclass
from typing import Any, Literal, Protocol

from personal_enigma.api.conversation_context import ConversationCapsule
from personal_enigma.privacy.egress.assert_remote_safe import assert_remote_safe
from personal_enigma.privacy.egress.classification import RemoteSafeContext
from personal_enigma.transformation import TransformedContext

EvidenceDomain = Literal[
    "PRIVATE_WORLD",
    "GENERAL_KNOWLEDGE",
    "EXTERNAL_WORLD",
    "CONVERSATION_ONLY",
]

Authority = Literal[
    "NONE",
    "READ",
    "SUPPORT",
    "ATTEST",
    "PREPARE",
    "APPROVE",
    "EXECUTE",
]

_AUTHORITY_RANK: dict[str, int] = {
    "NONE": 0,
    "READ": 1,
    "SUPPORT": 2,
    "ATTEST": 3,
    "PREPARE": 3,
    "APPROVE": 4,
    "EXECUTE": 5,
}
_ACTION_AUTHORITY = frozenset({"ATTEST", "PREPARE", "APPROVE", "EXECUTE"})
_SEMANTIC_CONFIDENCE_FLOOR = 0.5

_KNOWN_PERIODS = frozenset(
    {
        "this_week",
        "next_week",
        "this_weekend",
        "later_today",
        "this_afternoon",
        "this_evening",
        "tomorrow",
        "today",
        "saturday",
        "friday_night",
    }
)
_GOAL_FAMILIES: dict[str, tuple[str, ...]] = {
    "agenda": ("agenda",),
    "review_upcoming_commitments": ("agenda",),
    "next_work": ("attention", "agenda"),
    "review_attention": ("attention",),
    "important_from_source": ("source", "attention"),
    "review_sources": ("source",),
    "support_explain": ("explain", "attention"),
    "explain_subject": ("explain",),
    "attest": ("attestation",),
}

_BOOTSTRAP_SYSTEM_PROMPT = (
    "You interpret a user utterance for Enigma. "
    "You do not receive the user's private world. "
    "Return JSON only with keys: evidence_domain, authority, "
    "candidate_families, temporal_constraint, scope, inherit_capsule, "
    "active_goal, confidence. "
    "evidence_domain is PRIVATE_WORLD, GENERAL_KNOWLEDGE, or CONVERSATION_ONLY. "
    "Do not use EXTERNAL_WORLD. "
    "authority is NONE, READ, or SUPPORT unless the utterance is an explicit "
    "prepare/approve/execute command. "
    "Never invent PRIVATE_WORLD for public-world questions "
    "(why is the sky blue, why is rain wet). "
    "Elliptical follow-ups (and?, what else?, what about work?) should set "
    "inherit_capsule true and may add scope. "
    "You do not decide which tools exist."
)

_FORBIDDEN_BOOTSTRAP_CONVERSATION_KEYS = frozenset(
    {
        "obligations",
        "attention",
        "attention_working_set",
        "needs_you",
        "names",
        "people",
        "source",
        "source_raw",
        "calendar",
        "referent_candidates",
        "current_subject_id",
        "title",
    }
)


@dataclass(frozen=True)
class SemanticInterpretation:
    """Constrained language interpretation. Not a capability grant."""

    evidence_domain: EvidenceDomain | None = None
    authority: Authority | None = None
    candidate_families: tuple[str, ...] = ()
    temporal_constraint: str | None = None
    scope: str | None = None
    source_scope: str | None = None
    active_goal: str | None = None
    inherit_capsule: bool = False
    unresolved_goal: bool = False
    confidence: float = 0.0


class SemanticBootstrap(Protocol):
    """Interpret an utterance without Alex's private world."""

    def interpret(
        self,
        utterance: str,
        capsule: ConversationCapsule | None,
    ) -> SemanticInterpretation | None:
        """Return a constrained interpretation, or None to abstain."""
        ...


def empty_capsule_view() -> dict[str, str | None]:
    return {
        "active_goal": None,
        "temporal_frame": None,
        "scope": None,
        "source_scope": None,
        "unresolved_request": None,
    }


def bootstrap_conversation_view(capsule: ConversationCapsule | None) -> dict[str, Any]:
    """Slim capsule for the bootstrap model. Not the compiler's public_view."""
    if capsule is None:
        return empty_capsule_view()
    unresolved = None
    if capsule.unresolved_request is not None:
        unresolved = capsule.unresolved_request.status
    return {
        "active_goal": capsule.active_goal,
        "temporal_frame": capsule.temporal_constraint,
        "scope": capsule.scope,
        "source_scope": capsule.source,
        "unresolved_request": unresolved,
    }


def build_bootstrap_payload(
    utterance: str,
    capsule: ConversationCapsule | None,
) -> dict[str, Any]:
    """Utterance + public capsule only. No private-world modules."""
    return {
        "utterance": utterance,
        "conversation": bootstrap_conversation_view(capsule),
    }


def build_bootstrap_transformed_context(
    utterance: str,
    capsule: ConversationCapsule | None,
) -> TransformedContext:
    """REMOTE_SAFE TransformedContext for the bootstrap model."""
    payload = build_bootstrap_payload(utterance, capsule)
    conversation = payload.get("conversation") or {}
    extra = set(conversation) - {
        "active_goal",
        "temporal_frame",
        "scope",
        "source_scope",
        "unresolved_request",
    }
    if extra:
        raise ValueError(f"semantic bootstrap conversation has non-public keys: {sorted(extra)}")
    forbidden = set(conversation) & _FORBIDDEN_BOOTSTRAP_CONVERSATION_KEYS
    if forbidden:
        raise ValueError(
            f"semantic bootstrap conversation must not contain "
            f"private-world keys {sorted(forbidden)}"
        )
    # source_type is required by the TransformedContext remote-safe gate.
    # Bootstrap is not a source record; REMINDER is MEDIUM so identity checks run
    # without claiming a HIGH/VERY_HIGH source body.
    context = TransformedContext(
        summary=json.dumps(payload, default=str),
        entities=[],
        metadata={"source_type": "reminder"},
        may_transmit_remotely=True,
    )
    return assert_remote_safe(context)


def build_bootstrap_remote_context(
    utterance: str,
    capsule: ConversationCapsule | None,
    *,
    model: str,
    provider: str = "fireworks",
) -> RemoteSafeContext:
    """Wire payload for a remote bootstrap call. Tools are not included."""
    safe = build_bootstrap_transformed_context(utterance, capsule)
    payload = json.loads(safe.summary)
    body: dict[str, Any] = {
        "model": model,
        "messages": [
            {"role": "system", "content": _BOOTSTRAP_SYSTEM_PROMPT},
            {"role": "user", "content": json.dumps(payload, default=str)},
        ],
        "response_format": {"type": "json_object"},
    }
    return RemoteSafeContext(
        transformation_profile="semantic_bootstrap_v1",
        provider=provider,
        model=model,
        prompt=utterance,
        wire_body=body,
        may_transmit_remotely=True,
        included=["utterance", "conversation capsule (public fields only)"],
        excluded=[
            "PRIVATE_RAW",
            "obligations",
            "names",
            "attention items",
            "source bodies",
            "calendar",
            "permitted tool schemas",
        ],
        field_summary={
            "message_word_count": len(utterance.split()),
            "capsule_keys": sorted((payload.get("conversation") or {}).keys()),
            "tool_count": 0,
        },
    )


def _rank(authority: str | None) -> int:
    if authority is None:
        return _AUTHORITY_RANK["NONE"]
    return _AUTHORITY_RANK.get(authority, 0)


def _safer_authority(*authorities: str | None) -> Authority:
    present = [row for row in authorities if row is not None]
    if not present:
        return "NONE"
    return min(present, key=_rank)  # type: ignore[arg-type]


def _semantic_counts(semantic: SemanticInterpretation | None) -> bool:
    if semantic is None:
        return False
    if semantic.inherit_capsule:
        return True
    return semantic.confidence >= _SEMANTIC_CONFIDENCE_FLOOR


def _action_authority_allowed(deterministic: Authority, candidate: Authority | None) -> bool:
    if candidate is None:
        return False
    if candidate in _ACTION_AUTHORITY and deterministic not in _ACTION_AUTHORITY:
        return False
    return True


def merge_request_interpretation(
    utterance: str,
    deterministic: Any,
    semantic: SemanticInterpretation | None,
    capsule: ConversationCapsule | None,
) -> Any:
    """Conservative merge: semantic cannot casually increase authority.

    Domain: semantic may add PRIVATE_WORLD for elliptical private questions.
    It must not privatize generic public-world questions.
    Families remain suggestions — the compiler still applies floor ∩ fence.
    """
    from personal_enigma.api.context_compilation import (
        RequestConstraints,
        RequestInterpretation,
        is_generic_knowledge_utterance,
        profile_for_axes,
    )

    det_domain: EvidenceDomain = deterministic.evidence_domain
    det_authority: Authority = deterministic.authority
    inherit = bool(semantic and semantic.inherit_capsule and capsule is not None)
    semantic_live = _semantic_counts(semantic)

    domain: EvidenceDomain = det_domain
    if semantic_live and semantic is not None:
        sem_domain = semantic.evidence_domain
        if sem_domain == "EXTERNAL_WORLD":
            sem_domain = "GENERAL_KNOWLEDGE"
        if (
            det_domain == "GENERAL_KNOWLEDGE"
            and sem_domain == "PRIVATE_WORLD"
            and not is_generic_knowledge_utterance(utterance)
        ):
            domain = "PRIVATE_WORLD"
        elif det_domain == "PRIVATE_WORLD":
            domain = "PRIVATE_WORLD"
        elif inherit and capsule is not None and capsule.evidence_domain == "PRIVATE_WORLD":
            if det_domain in {"GENERAL_KNOWLEDGE", "CONVERSATION_ONLY"}:
                domain = "PRIVATE_WORLD"
        elif sem_domain in {"GENERAL_KNOWLEDGE", "CONVERSATION_ONLY", "PRIVATE_WORLD"}:
            if det_domain != "PRIVATE_WORLD":
                domain = sem_domain if sem_domain != "PRIVATE_WORLD" else domain

    if inherit and capsule is not None and capsule.evidence_domain == "PRIVATE_WORLD":
        if det_domain in {"GENERAL_KNOWLEDGE", "CONVERSATION_ONLY"}:
            domain = "PRIVATE_WORLD"

    sem_authority = semantic.authority if semantic_live and semantic is not None else None
    if sem_authority is not None and not _action_authority_allowed(det_authority, sem_authority):
        sem_authority = None
    # Evidence may inherit. Authority must be re-earned — capsule authority is not a grant.
    authority = _safer_authority(det_authority, sem_authority)
    if domain == "PRIVATE_WORLD" and authority == "NONE":
        authority = "READ"
    if domain in {"GENERAL_KNOWLEDGE", "CONVERSATION_ONLY"}:
        authority = "NONE"

    families = list(deterministic.capability_families)
    if semantic_live and semantic is not None:
        families.extend(semantic.candidate_families)
    if inherit and capsule is not None and capsule.active_goal:
        from personal_enigma.api.conversation_context import families_for_request_kind

        families.extend(families_for_request_kind(capsule.active_goal))  # type: ignore[arg-type]
        families.extend(_GOAL_FAMILIES.get(str(capsule.active_goal), ()))
    if inherit and capsule is not None and capsule.temporal_constraint and "agenda" not in families:
        families.append("agenda")
    if domain in {"GENERAL_KNOWLEDGE", "CONVERSATION_ONLY"}:
        families = []
    families = list(dict.fromkeys(families))

    period = deterministic.constraints.period
    scope = deterministic.constraints.scope
    source = deterministic.constraints.source
    if semantic_live and semantic is not None:
        if semantic.temporal_constraint in _KNOWN_PERIODS and period is None:
            period = semantic.temporal_constraint
        if semantic.scope:
            scope = semantic.scope
        if semantic.source_scope:
            source = semantic.source_scope
    if inherit and capsule is not None:
        if period is None:
            period = capsule.temporal_constraint
        if scope is None:
            scope = capsule.scope
        if source is None:
            source = capsule.source or getattr(capsule, "source_scope", None)

    request_kind = getattr(deterministic, "request_kind", None)
    if inherit and request_kind is None and capsule is not None:
        request_kind = capsule.active_goal or (
            "agenda" if capsule.temporal_constraint else None
        )

    return RequestInterpretation(
        evidence_domain=domain,
        authority=authority,
        profile=profile_for_axes(domain, authority),
        speech_act=deterministic.speech_act,
        constraints=RequestConstraints(period=period, scope=scope, source=source),
        capability_families=tuple(families),
        request_kind=request_kind,
        frame_inherited=inherit or bool(getattr(deterministic, "frame_inherited", False)),
    )


def compile_with_bootstrap(
    utterance: str,
    session: Any,
    bootstrap: SemanticBootstrap | None,
    *,
    profile: str | None = None,
    semantic: SemanticInterpretation | None = None,
) -> Any:
    """Deterministic baseline + optional semantic + capsule → compiler."""
    from personal_enigma.api.context_compilation import (
        RequestProfileName,
        compile_remote_context,
        interpret_request,
    )

    deterministic = interpret_request(utterance, session)
    resolved = semantic
    if resolved is None and bootstrap is not None:
        resolved = bootstrap.interpret(utterance, session.context.live_capsule())
    merged = merge_request_interpretation(
        utterance,
        deterministic,
        resolved,
        session.context.live_capsule(),
    )
    typed_profile: RequestProfileName | None = None
    if profile in {
        "CONVERSATION",
        "GENERAL_KNOWLEDGE",
        "PRIVATE_QUERY",
        "SUPPORT",
        "USER_ATTESTATION",
        "PREPARE_ACTION",
        "AUTHORITATIVE_ACTION",
    }:
        typed_profile = profile  # type: ignore[assignment]
    return compile_remote_context(
        utterance,
        session,
        profile=typed_profile,
        interpretation=merged,
    )


class FixtureSemanticBootstrap:
    """Deterministic test oracle. Not production routing and not interpret_request."""

    def interpret(
        self,
        utterance: str,
        capsule: ConversationCapsule | None,
    ) -> SemanticInterpretation | None:
        del capsule
        hay = utterance.strip().casefold()
        if hay in {"why is the sky blue?", "why is rain wet?", "whats the colour of the sky"}:
            return SemanticInterpretation(
                evidence_domain="GENERAL_KNOWLEDGE",
                authority="NONE",
                confidence=0.96,
            )
        if hay in {"anything coming up?", "anything coming up"}:
            return SemanticInterpretation(
                evidence_domain="PRIVATE_WORLD",
                authority="READ",
                candidate_families=("agenda",),
                temporal_constraint="near_future",
                active_goal="agenda",
                confidence=0.91,
            )
        if hay in {"what about work?", "what about work"}:
            return SemanticInterpretation(
                evidence_domain="PRIVATE_WORLD",
                authority="READ",
                candidate_families=("agenda",),
                scope="work",
                inherit_capsule=True,
                confidence=0.88,
            )
        if hay in {"and?", "and", "what else?", "what else"}:
            return SemanticInterpretation(
                inherit_capsule=True,
                unresolved_goal=True,
                confidence=0.84,
            )
        return SemanticInterpretation(confidence=0.0)


class RemoteSemanticBootstrap:
    """Optional Fireworks bootstrap. Default tests never require a key."""

    def __init__(
        self,
        *,
        gate: Any | None = None,
        model: str | None = None,
        provider: str = "fireworks",
    ) -> None:
        self._gate = gate
        self._provider = provider
        self._model = model or os.environ.get(
            "FIREWORKS_MODEL", "accounts/fireworks/models/gpt-oss-120b"
        )

    def interpret(
        self,
        utterance: str,
        capsule: ConversationCapsule | None,
    ) -> SemanticInterpretation | None:
        from personal_enigma.privacy.egress import get_audited_egress_gate
        from personal_enigma.privacy.remote import RemoteInferenceConfig

        remote_ctx = build_bootstrap_remote_context(
            utterance,
            capsule,
            model=self._model,
            provider=self._provider,
        )
        gate = self._gate
        if gate is None:
            shared = get_audited_egress_gate()
            gate = shared
            if not getattr(gate, "remote_config", None) or not gate.remote_config.enabled:
                from personal_enigma.privacy.egress import build_audited_egress_gate

                gate = build_audited_egress_gate(
                    remote_config=RemoteInferenceConfig(enabled=True),
                    disclosure_store=shared.disclosure_store,
                    fireworks_api_key=os.environ.get("FIREWORKS_API_KEY", ""),
                )
        try:
            egress = gate.submit(
                remote_ctx,
                purpose="conversation.semantic_bootstrap",
                transformed_context=build_bootstrap_transformed_context(utterance, capsule),
                max_output_tokens=256,
            )
        except Exception:
            return SemanticInterpretation(confidence=0.0)
        if not getattr(egress, "sent", False) or egress.response is None:
            return SemanticInterpretation(confidence=0.0)
        return _parse_semantic_response(egress.response.text)


def _parse_semantic_response(raw: str) -> SemanticInterpretation:
    try:
        message = json.loads(raw)
    except json.JSONDecodeError:
        try:
            data = json.loads(raw)
        except json.JSONDecodeError:
            return SemanticInterpretation(confidence=0.0)
        else:
            message = data if isinstance(data, dict) else {}
    content = message.get("content") if isinstance(message, dict) else None
    if isinstance(content, str):
        try:
            data = json.loads(content)
        except json.JSONDecodeError:
            return SemanticInterpretation(confidence=0.0)
    elif isinstance(content, dict):
        data = content
    elif isinstance(message, dict) and "evidence_domain" in message:
        data = message
    else:
        return SemanticInterpretation(confidence=0.0)
    if not isinstance(data, dict):
        return SemanticInterpretation(confidence=0.0)
    families_raw = data.get("candidate_families") or ()
    families = tuple(str(row) for row in families_raw if row)
    domain = data.get("evidence_domain")
    if domain == "EXTERNAL_WORLD":
        domain = "GENERAL_KNOWLEDGE"
    authority = data.get("authority")
    try:
        confidence = float(data.get("confidence") or 0.0)
    except (TypeError, ValueError):
        confidence = 0.0
    allowed_domains = {"PRIVATE_WORLD", "GENERAL_KNOWLEDGE", "CONVERSATION_ONLY"}
    allowed_authorities = {
        "NONE",
        "READ",
        "SUPPORT",
        "ATTEST",
        "PREPARE",
        "APPROVE",
        "EXECUTE",
    }
    return SemanticInterpretation(
        evidence_domain=domain if domain in allowed_domains else None,
        authority=authority if authority in allowed_authorities else None,
        candidate_families=families,
        temporal_constraint=str(data["temporal_constraint"])
        if data.get("temporal_constraint")
        else None,
        scope=str(data["scope"]) if data.get("scope") else None,
        source_scope=str(data["source_scope"]) if data.get("source_scope") else None,
        active_goal=str(data["active_goal"]) if data.get("active_goal") else None,
        inherit_capsule=bool(data.get("inherit_capsule")),
        unresolved_goal=bool(data.get("unresolved_goal")),
        confidence=confidence,
    )


def semantic_bootstrap_enabled() -> bool:
    flag = os.environ.get("ENIGMA_SEMANTIC_BOOTSTRAP", "").lower()
    return flag in {"1", "true", "yes"}


_BOOTSTRAP_OVERRIDE: SemanticBootstrap | None = None


def set_semantic_bootstrap(bootstrap: SemanticBootstrap | None) -> None:
    global _BOOTSTRAP_OVERRIDE
    _BOOTSTRAP_OVERRIDE = bootstrap


def get_semantic_bootstrap() -> SemanticBootstrap | None:
    if _BOOTSTRAP_OVERRIDE is not None:
        return _BOOTSTRAP_OVERRIDE
    if semantic_bootstrap_enabled() and os.environ.get("FIREWORKS_API_KEY"):
        return RemoteSemanticBootstrap()
    return None


__all__ = [
    "FixtureSemanticBootstrap",
    "RemoteSemanticBootstrap",
    "SemanticBootstrap",
    "SemanticInterpretation",
    "build_bootstrap_payload",
    "build_bootstrap_remote_context",
    "build_bootstrap_transformed_context",
    "compile_with_bootstrap",
    "get_semantic_bootstrap",
    "merge_request_interpretation",
    "set_semantic_bootstrap",
]
