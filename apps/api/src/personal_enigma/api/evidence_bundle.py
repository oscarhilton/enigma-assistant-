"""C25 evidence coverage bundle — typed satchel for read turns (ADR-034).

Derived from compiler mission + tool trace. Never model self-report.
"""

from __future__ import annotations

from typing import Any, Literal

from pydantic import BaseModel, Field

from personal_enigma.api.conversation_context import RequestKind
from personal_enigma.domain import (
    AssertionChallenge,
    AssertionKind,
    AssertionSensitivity,
    ChallengeDisposition,
    EpistemicStatus,
    EvidenceUnknown,
    GroundedAssertion,
    RetentionClass,
    UnknownReason,
)

SourceName = Literal[
    "calendar",
    "attention",
    "next_actions",
    "world_changes",
    "world_blockers",
    "sources_email",
    "sources_chat",
    "weather",
    "news",
    "general_knowledge",
]

CourierState = Literal[
    "resting",
    "fetching",
    "returned",
    "empty_pawed",
    "partially_returned",
    "confused",
    "blocked",
]

TOOL_TO_SOURCE: dict[str, SourceName] = {
    "agenda.get": "calendar",
    "availability.check": "calendar",
    "availability.time_fit": "calendar",
    "attention.get_current": "attention",
    "attention.explain_why": "attention",
    "next_action.get": "next_actions",
    "next_action.get_alternatives": "next_actions",
    "next_action.reject": "next_actions",
    "world.get_changes": "world_changes",
    "world.get_blockers": "world_blockers",
    "world.explain": "attention",
    "source.recent": "sources_email",
    "source.quote": "sources_chat",
}

_KIND_PLANNED_TOOLS: dict[str, tuple[str, ...]] = {
    "agenda": ("agenda.get",),
    "next_work": (
        "attention.get_current",
        "next_action.get",
        "agenda.get",
    ),
    "catch_up": (
        "attention.get_current",
        "world.get_changes",
        "world.get_blockers",
        "agenda.get",
    ),
    "important_from_source": ("source.recent", "attention.get_current"),
    "support_explain": ("world.explain", "attention.get_current"),
    "subject_details": ("world.explain", "source.recent"),
    "attest": ("world.record_user_attestation",),
}

_SOURCE_LABELS: dict[SourceName, str] = {
    "calendar": "calendar",
    "attention": "attention",
    "next_actions": "next actions",
    "world_changes": "recent changes",
    "world_blockers": "blockers",
    "sources_email": "email",
    "sources_chat": "messages",
    "weather": "weather",
    "news": "live news",
    "general_knowledge": "general knowledge",
}


class FetchMission(BaseModel):
    question: str
    request_kind: RequestKind | None = None
    scope: Literal["work", "personal"] | None = None
    time_range: str | None = None
    authority: str = "NONE"
    planned_tools: list[str] = Field(default_factory=list)


class EvidenceItem(BaseModel):
    source: SourceName
    evidence_ids: list[str] = Field(default_factory=list)
    summary: str | None = None


class EvidenceConflict(BaseModel):
    field: str
    values: list[str] = Field(default_factory=list)
    source_ids: list[str] = Field(default_factory=list)


class EvidenceBundle(BaseModel):
    mission: FetchMission
    searched_sources: list[SourceName] = Field(default_factory=list)
    empty_sources: list[SourceName] = Field(default_factory=list)
    unsearched_sources: list[SourceName] = Field(default_factory=list)
    unavailable_sources: list[SourceName] = Field(default_factory=list)
    evidence: list[EvidenceItem] = Field(default_factory=list)
    grounded_assertions: list[GroundedAssertion] = Field(default_factory=list)
    unknowns: list[EvidenceUnknown] = Field(default_factory=list)
    unresolved_referents: list[str] = Field(default_factory=list)
    conflicts: list[EvidenceConflict] = Field(default_factory=list)
    challenges: list[AssertionChallenge] = Field(default_factory=list)
    coverage_adequate: bool = False
    courier_state: CourierState = "resting"


def planned_tools_for_kind(request_kind: RequestKind | None) -> list[str]:
    if request_kind is None:
        return []
    return list(_KIND_PLANNED_TOOLS.get(request_kind, ()))


def build_fetch_mission(
    *,
    question: str,
    working_set: dict[str, Any],
) -> FetchMission:
    kind = working_set.get("request_kind")
    planned = working_set.get("fetch_mission", {}).get("planned_tools")
    if not planned:
        planned = planned_tools_for_kind(kind)
    scope = working_set.get("scope")
    if scope not in {"work", "personal"}:
        scope = None
    return FetchMission(
        question=question,
        request_kind=kind,
        scope=scope,
        time_range=working_set.get("temporal_constraint"),
        authority=str(working_set.get("authority") or "NONE"),
        planned_tools=list(planned or []),
    )


def _tool_source(name: str, data: dict[str, Any] | None = None) -> SourceName | None:
    if name == "source.recent" and data:
        channel = str(data.get("channel") or "").casefold()
        if channel == "whatsapp":
            return "sources_chat"
    mapped = TOOL_TO_SOURCE.get(name)
    if mapped == "sources_email" and data:
        channel = str(data.get("channel") or "").casefold()
        if channel == "whatsapp":
            return "sources_chat"
    return mapped


def _collect_evidence_ids(data: dict[str, Any]) -> list[str]:
    ids: list[str] = []
    for key in (
        "evidence_ids",
        "calendar_evidence_ids",
        "recent_ids",
        "next_action_ids",
        "blocker_ids",
        "source_id",
        "subject_id",
    ):
        raw = data.get(key)
        if isinstance(raw, list):
            ids.extend(str(row) for row in raw if row)
        elif isinstance(raw, str) and raw:
            ids.append(raw)
    return ids


def _source_is_empty(source: SourceName, data: dict[str, Any]) -> bool:
    if data.get("denied"):
        return True
    if source == "calendar" and data.get("empty_horizon") is True:
        return True
    if source == "attention":
        count = data.get("needs_you_count")
        if count == 0 or (count is None and not _collect_evidence_ids(data)):
            if not data.get("facts"):
                return True
    if source == "next_actions" and not _collect_evidence_ids(data):
        return True
    if source in {"world_changes", "world_blockers"} and not _collect_evidence_ids(data):
        changes = data.get("changes") or data.get("blockers")
        if changes == [] or changes is None:
            return True
    if source in {"sources_email", "sources_chat"}:
        if not _collect_evidence_ids(data):
            return True
    if not _collect_evidence_ids(data) and source == "attention":
        facts = data.get("facts")
        if facts == [] or facts is None:
            return True
    return False


def _assertion(
    *,
    assertion_id: str,
    subject: str,
    predicate: str,
    value: Any,
    status: EpistemicStatus,
    evidence_refs: list[str],
    purpose_tags: list[str],
    confidence: float | None = None,
) -> GroundedAssertion:
    return GroundedAssertion(
        id=assertion_id,
        kind=AssertionKind.FACT,
        subject=subject,
        predicate=predicate,
        value=value,
        epistemic_status=status,
        confidence=confidence,
        evidence_refs=evidence_refs,
        sensitivity=AssertionSensitivity.PERSONAL,
        purpose_tags=purpose_tags,
        retention_class=RetentionClass.EPHEMERAL_ANSWER_ONLY,
    )


def _assertions_for_tool(
    name: str, data: dict[str, Any], evidence_refs: list[str]
) -> list[GroundedAssertion]:
    assertions: list[GroundedAssertion] = []
    if name in {"agenda.get", "availability.check", "availability.time_fit"}:
        if data.get("empty_horizon") is True:
            assertions.append(
                _assertion(
                    assertion_id=f"{name}:empty_horizon",
                    subject="calendar",
                    predicate="has_items",
                    value=False,
                    status=EpistemicStatus.SYSTEM_VERIFIED,
                    evidence_refs=evidence_refs,
                    purpose_tags=["coverage", "planning"],
                )
            )
        elif evidence_refs:
            assertions.append(
                _assertion(
                    assertion_id=f"{name}:item_count",
                    subject="calendar",
                    predicate="item_count",
                    value=len(evidence_refs),
                    status=EpistemicStatus.SYSTEM_VERIFIED,
                    evidence_refs=evidence_refs,
                    purpose_tags=["coverage", "planning"],
                )
            )
    elif name == "attention.get_current":
        count = data.get("needs_you_count")
        if isinstance(count, int):
            assertions.append(
                _assertion(
                    assertion_id="attention:needs_you_count",
                    subject="attention",
                    predicate="needs_you_count",
                    value=count,
                    status=EpistemicStatus.SYSTEM_VERIFIED,
                    evidence_refs=evidence_refs,
                    purpose_tags=["attention", "coverage"],
                )
            )
    elif name == "world.get_changes":
        changes = data.get("changes")
        if isinstance(changes, list):
            assertions.append(
                _assertion(
                    assertion_id="world_changes:count",
                    subject="world_changes",
                    predicate="change_count",
                    value=len(changes),
                    status=EpistemicStatus.SYSTEM_VERIFIED,
                    evidence_refs=evidence_refs,
                    purpose_tags=["catch_up", "coverage"],
                )
            )
    elif name == "world.get_blockers":
        blockers = data.get("blockers")
        if isinstance(blockers, list):
            assertions.append(
                _assertion(
                    assertion_id="world_blockers:count",
                    subject="world_blockers",
                    predicate="blocker_count",
                    value=len(blockers),
                    status=EpistemicStatus.SYSTEM_VERIFIED,
                    evidence_refs=evidence_refs,
                    purpose_tags=["catch_up", "coverage"],
                )
            )
    elif name == "source.recent":
        assertions.append(
            _assertion(
                assertion_id=f"source_recent:{data.get('channel') or 'unknown'}",
                subject=str(data.get("channel") or "source"),
                predicate="recent_item_count",
                value=len(evidence_refs),
                status=EpistemicStatus.SOURCE_OBSERVED,
                evidence_refs=evidence_refs,
                purpose_tags=["source_read", "coverage"],
            )
        )
    return assertions


def _build_unknowns(
    *,
    mission: FetchMission,
    unsearched: list[SourceName],
    unavailable: list[SourceName],
    unresolved: list[str],
) -> list[EvidenceUnknown]:
    unknowns: list[EvidenceUnknown] = []
    for ref in unresolved:
        unknowns.append(
            EvidenceUnknown(
                subject="question",
                predicate=ref,
                reason=UnknownReason.UNRESOLVED_REFERENT,
            )
        )
    if unsearched:
        unknowns.append(
            EvidenceUnknown(
                subject="question",
                predicate=mission.request_kind or "coverage",
                reason=UnknownReason.MISSING_EVIDENCE,
                missing_sources=list(unsearched),
            )
        )
    if unavailable:
        unknowns.append(
            EvidenceUnknown(
                subject="question",
                predicate=mission.request_kind or "capability",
                reason=UnknownReason.UNAVAILABLE_CAPABILITY,
                missing_sources=list(unavailable),
            )
        )
    return unknowns


def _build_challenges(
    *,
    mission: FetchMission,
    coverage_adequate: bool,
    evidence: list[EvidenceItem],
    unsearched: list[SourceName],
    unavailable: list[SourceName],
    unresolved: list[str],
) -> list[AssertionChallenge]:
    if coverage_adequate:
        return []
    evidence_refs = [evidence_id for item in evidence for evidence_id in item.evidence_ids]
    if unresolved:
        return [
            AssertionChallenge(
                subject="question",
                predicate=mission.request_kind or "referent",
                disposition=ChallengeDisposition.DOES_NOT_ADDRESS,
                summary="The request is not grounded to a stable referent yet.",
                evidence_refs=evidence_refs,
            )
        ]
    if unsearched or unavailable:
        return [
            AssertionChallenge(
                subject="question",
                predicate=mission.request_kind or "coverage",
                disposition=ChallengeDisposition.QUALIFIES,
                summary=(
                    "Current evidence is useful but does not resolve the question because "
                    "some required sources were not searched or were unavailable."
                ),
                evidence_refs=evidence_refs,
            )
        ]
    return []


def _implied_unavailable_sources(question: str, contract: dict[str, Any]) -> list[SourceName]:
    hay = question.casefold()
    unavailable: list[SourceName] = []
    if any(token in hay for token in ("weather", "forecast", "rain", "temperature")):
        unavailable.append("weather")
    if any(token in hay for token in ("news", "headlines", "the news")):
        unavailable.append("news")
    unavailable_names = set(contract.get("unavailable") or [])
    if "arbitrary network" in unavailable_names:
        if "weather" not in unavailable:
            if any(token in hay for token in ("weather", "forecast")):
                unavailable.append("weather")
        if "news" not in unavailable:
            if any(token in hay for token in ("news", "headlines")):
                unavailable.append("news")
    return unavailable


def _unresolved_referents(
    question: str,
    *,
    referent_resolution: list[dict[str, Any]] | None,
    current_subject_id: str | None,
) -> list[str]:
    unresolved: list[str] = []
    hay = question.casefold()
    if "brunch" in hay and not current_subject_id:
        unresolved.append("brunch")
    if referent_resolution:
        for row in referent_resolution:
            if row.get("source") == "unresolved":
                summary = str(row.get("summary") or "referent")
                unresolved.append(summary)
    return unresolved


def _compute_coverage_adequate(
    *,
    mission: FetchMission,
    searched: set[SourceName],
    unsearched: set[SourceName],
    unavailable: set[SourceName],
    unresolved: list[str],
    evidence_domain: str,
    authority: str,
) -> bool:
    if unresolved:
        return False
    if mission.request_kind in {"catch_up", "next_work"}:
        planned = {_tool_source(tool) for tool in mission.planned_tools}
        planned.discard(None)
        if not planned.issubset(searched):
            return False
    elif unsearched:
        return False
    if evidence_domain == "GENERAL_KNOWLEDGE" and authority == "NONE":
        if unavailable & {"news", "weather"}:
            return False
    if mission.request_kind in {"catch_up", "next_work", "agenda"}:
        if searched == {"calendar"} and mission.request_kind != "agenda":
            return False
    return True


def derive_courier_state(bundle: EvidenceBundle) -> CourierState:
    if bundle.unresolved_referents:
        return "confused"
    if bundle.unavailable_sources and not bundle.searched_sources:
        implied = set(bundle.unavailable_sources)
        if implied & {"news", "weather"}:
            return "blocked"
    if not bundle.searched_sources:
        if bundle.unavailable_sources:
            return "blocked"
        if not bundle.mission.planned_tools:
            return "resting"
        return "partially_returned"
    if not bundle.coverage_adequate:
        if bundle.unsearched_sources or bundle.unavailable_sources:
            return "partially_returned"
    if bundle.evidence:
        return "returned"
    if bundle.searched_sources and not bundle.empty_sources:
        return "returned"
    if bundle.searched_sources and set(bundle.searched_sources) == set(bundle.empty_sources):
        if bundle.coverage_adequate:
            return "empty_pawed"
        return "partially_returned"
    if bundle.searched_sources:
        return "partially_returned"
    return "resting"


def build_evidence_bundle(
    *,
    question: str,
    working_set: dict[str, Any],
    tool_results: list[dict[str, Any]] | None = None,
    referent_resolution: list[dict[str, Any]] | None = None,
    current_subject_id: str | None = None,
    evidence_domain: str = "CONVERSATION_ONLY",
    authority: str = "NONE",
) -> EvidenceBundle:
    mission = build_fetch_mission(question=question, working_set=working_set)
    contract = working_set.get("capability_contract") or {}
    planned_sources: set[SourceName] = set()
    for tool in mission.planned_tools:
        src = _tool_source(tool)
        if src:
            planned_sources.add(src)

    searched_sources: list[SourceName] = []
    empty_sources: list[SourceName] = []
    evidence: list[EvidenceItem] = []
    grounded_assertions: list[GroundedAssertion] = []
    executed_tools: set[str] = set()

    for row in tool_results or []:
        if not row.get("ok"):
            continue
        name = str(row.get("name") or "")
        executed_tools.add(name)
        data = row.get("data")
        if not isinstance(data, dict):
            data = {}
        source = _tool_source(name, data)
        if source is None:
            continue
        if source not in searched_sources:
            searched_sources.append(source)
        ids = _collect_evidence_ids(data)
        if ids:
            evidence.append(EvidenceItem(source=source, evidence_ids=ids))
        elif _source_is_empty(source, data) and source not in empty_sources:
            empty_sources.append(source)
        grounded_assertions.extend(_assertions_for_tool(name, data, ids))

    searched_set = set(searched_sources)
    unsearched: list[SourceName] = []
    for tool in mission.planned_tools:
        src = _tool_source(tool)
        if src and src not in searched_set and src not in unsearched:
            unsearched.append(src)

    unavailable = _implied_unavailable_sources(question, contract)
    for src in unavailable:
        if src not in unavailable:
            unavailable.append(src)

    unresolved = _unresolved_referents(
        question,
        referent_resolution=referent_resolution,
        current_subject_id=current_subject_id or working_set.get("current_subject_id"),
    )

    coverage = _compute_coverage_adequate(
        mission=mission,
        searched=searched_set,
        unsearched=set(unsearched),
        unavailable=set(unavailable),
        unresolved=unresolved,
        evidence_domain=evidence_domain,
        authority=authority,
    )
    unknowns = _build_unknowns(
        mission=mission,
        unsearched=unsearched,
        unavailable=unavailable,
        unresolved=unresolved,
    )
    challenges = _build_challenges(
        mission=mission,
        coverage_adequate=coverage,
        evidence=evidence,
        unsearched=unsearched,
        unavailable=unavailable,
        unresolved=unresolved,
    )

    bundle = EvidenceBundle(
        mission=mission,
        searched_sources=searched_sources,
        empty_sources=empty_sources,
        unsearched_sources=unsearched,
        unavailable_sources=unavailable,
        evidence=evidence,
        grounded_assertions=grounded_assertions,
        unknowns=unknowns,
        unresolved_referents=unresolved,
        conflicts=[],
        challenges=challenges,
        coverage_adequate=coverage,
    )
    bundle.courier_state = derive_courier_state(bundle)
    return bundle


def format_source_list(sources: list[SourceName]) -> str:
    if not sources:
        return ""
    labels = [_SOURCE_LABELS.get(src, src) for src in sources]
    if len(labels) == 1:
        return labels[0]
    if len(labels) == 2:
        return f"{labels[0]} and {labels[1]}"
    return ", ".join(labels[:-1]) + f", and {labels[-1]}"


def bundle_aware_fallback(bundle: EvidenceBundle) -> str | None:
    """Enigma voice — coverage-honest fallback when the model over-claims."""
    state = bundle.courier_state
    mission = bundle.mission

    if state == "blocked":
        if "news" in bundle.unavailable_sources:
            return (
                "I can't reach live news from here — I won't fill the gap with old headlines. "
                "If you want something specific, tell me the topic and I'll say what I don't know."
            )
        if "weather" in bundle.unavailable_sources:
            return "I don't have a tool that can look up weather information."

    if state == "confused":
        ref = bundle.unresolved_referents[0] if bundle.unresolved_referents else "that"
        return f"I'm not sure which {ref} you mean yet — can you point me to the thread or event?"

    if state == "partially_returned" or not bundle.coverage_adequate:
        searched = format_source_list(bundle.searched_sources)
        unsearched = format_source_list(bundle.unsearched_sources)
        unavailable = format_source_list(bundle.unavailable_sources)
        parts: list[str] = []
        if searched:
            parts.append(f"I checked {searched}")
        else:
            parts.append("I didn't run the reads this question needed")
        if unsearched:
            parts.append(f"but didn't check {unsearched}")
        if unavailable:
            parts.append(f"and this session can't reach {unavailable}")
        tail = " — so I can't conclude nothing needs you." if mission.request_kind in {
            "next_work",
            "catch_up",
            "agenda",
        } else "."
        return "".join(parts) + tail

    if state == "empty_pawed":
        searched = format_source_list(bundle.searched_sources)
        return f"I checked {searched} and didn't find anything that needs you right now."

    return None


__all__ = [
    "EvidenceBundle",
    "EvidenceConflict",
    "EvidenceItem",
    "FetchMission",
    "SourceName",
    "CourierState",
    "build_evidence_bundle",
    "build_fetch_mission",
    "bundle_aware_fallback",
    "derive_courier_state",
    "format_source_list",
    "planned_tools_for_kind",
]
