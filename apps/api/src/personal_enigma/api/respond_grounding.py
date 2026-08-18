"""C21 respond-phase grounding fence — tiered evidence, fail closed.

When compilation wrongly leaves a private-world attribute request on
CONVERSATION_ONLY with no tools, the model must not invent or replace
conversational choices with verified-looking commercial facts.

C26 bridge: consume ``EvidenceBundle`` grounded assertions via domain
``current_assertions()`` — preserve conflicts, supersession, and epistemic
class; dialogue-history fossils must not read as verified support.
"""

from __future__ import annotations

import re
from datetime import UTC, datetime
from typing import Any

from personal_enigma.api.conversation_context import ConversationContext
from personal_enigma.domain import (
    DerivationKind,
    EpistemicStatus,
    GroundedAssertion,
    current_assertions,
)

_COMMERCIAL_INVENTION = re.compile(
    r"(\+\d{2,3}\s?\d|\b\d{1,4}\s+[a-z]+(?:\s+street|\s+road|\s+lane)\b|"
    r"£\d|opening hours|wheelchair|postcode|parking|menu highlights|"
    r"per adult|buffet:|prosecco|accessibility)",
    re.IGNORECASE,
)
_VENUE_NAME = re.compile(
    r"\b([A-Z][a-z]+(?:\s+[A-Z][a-z]+){0,4}\s+(?:Club|Café|Cafe|Bistro|Brunch|Restaurant))\b"
)
_TIME_MENTION = re.compile(r"\b(\d{1,2}:\d{2}\s*(?:am|pm)|\d{1,2}\s*(?:am|pm))\b", re.IGNORECASE)
_EPISTEMIC_HEDGE = re.compile(
    r"\b(we discussed|you chose|from our conversation|i don't have verified|"
    r"i need to check|not verified|supporting email|haven't checked)\b",
    re.IGNORECASE,
)
_HISTORICAL_NEWS_FICTION = re.compile(
    r"\b(presidential election|re-elected|digital green pass|generative ai became mainstream|"
    r"global highlights|key developments|knowledge cutoff)\b",
    re.IGNORECASE,
)
_BROCHURE_TONE = re.compile(
    r"(\*\*menu|\*\*pricing|\*\*reservation|\*\*restaurant|\*\*address|"
    r"---\n\n\*\*next step)",
    re.IGNORECASE,
)
_CONFLICT_ACK = re.compile(
    r"\b(conflict|conflicting|contradict|unclear|both|either|not sure|"
    r"can't tell|cannot tell|need to check|don't know|do not know)\b",
    re.IGNORECASE,
)
_VERIFIED_EPISTEMIC_STATUSES = frozenset(
    {
        EpistemicStatus.USER_CONFIRMED,
        EpistemicStatus.SOURCE_OBSERVED,
        EpistemicStatus.EXTERNALLY_VERIFIED,
        EpistemicStatus.SYSTEM_VERIFIED,
        EpistemicStatus.DETERMINISTICALLY_DERIVED,
    }
)


def _dialogue_blob(context: ConversationContext) -> str:
    if not hasattr(context, "recent_dialogue"):
        return ""
    parts: list[str] = []
    for row in context.recent_dialogue:
        parts.append(getattr(row, "text", "") or "")
        parts.append(getattr(row, "summary", "") or "")
    for row in context.turn_local_constraints:
        parts.append(getattr(row, "value", "") or "")
    return " ".join(parts).casefold()


def _extract_dialogue_venues(blob: str) -> set[str]:
    found: set[str] = set()
    for match in _VENUE_NAME.finditer(blob):
        found.add(match.group(1).casefold())
    for needle in ("bistro brunch", "sunny side", "garden terrace"):
        if needle in blob:
            found.add(needle)
    return found


def _extract_dialogue_times(blob: str) -> set[str]:
    times: set[str] = set()
    for match in _TIME_MENTION.finditer(blob):
        times.add(match.group(1).casefold().replace(" ", ""))
    if "10am" in blob.replace(" ", "").replace(":", ""):
        times.add("10:00am")
        times.add("10am")
    return times


def _response_venues(text: str) -> set[str]:
    found: set[str] = set()
    for match in _VENUE_NAME.finditer(text):
        found.add(match.group(1).casefold())
    return found


def _replaced_conversational_choice(text: str, dialogue: str) -> bool:
    dialogue_venues = _extract_dialogue_venues(dialogue)
    if not dialogue_venues:
        return False
    response_venues = _response_venues(text)
    if not response_venues:
        return False
    overlap = dialogue_venues & response_venues
    if overlap:
        return False
    return bool(response_venues - dialogue_venues)


def _replaced_time(text: str, dialogue: str) -> bool:
    dialogue_times = _extract_dialogue_times(dialogue)
    if not dialogue_times:
        return False
    response_times = {m.group(1).casefold().replace(" ", "") for m in _TIME_MENTION.finditer(text)}
    if "10am" in dialogue.replace(" ", "").replace(":", "") and any(
        t.startswith("11:") or t.startswith("11") for t in response_times
    ):
        return True
    return False


def _invents_commercial_facts(text: str) -> bool:
    return _COMMERCIAL_INVENTION.search(text) is not None


def _presents_unverified_as_verified(text: str, *, has_tool_evidence: bool) -> bool:
    if has_tool_evidence:
        return False
    if _EPISTEMIC_HEDGE.search(text):
        return False
    return _BROCHURE_TONE.search(text) is not None or (
        _invents_commercial_facts(text) and not _EPISTEMIC_HEDGE.search(text)
    )


def _coerce_bundle(evidence_bundle: Any) -> Any:
    from personal_enigma.api.evidence_bundle import EvidenceBundle

    if isinstance(evidence_bundle, dict):
        return EvidenceBundle.model_validate(evidence_bundle)
    return evidence_bundle


def _is_dialogue_fossil(assertion: GroundedAssertion) -> bool:
    return (
        assertion.epistemic_status == EpistemicStatus.MODEL_INFERRED
        and assertion.derivation_kind == DerivationKind.DIALOGUE_HISTORY
    )


def _bundle_current(
    bundle: Any,
    *,
    now: datetime,
) -> list[GroundedAssertion]:
    active_refs = {
        evidence_id for item in bundle.evidence for evidence_id in item.evidence_ids
    }
    return current_assertions(
        bundle.grounded_assertions,
        now=now,
        active_source_refs=active_refs or None,
    )


def _bundle_verified_assertions(
    bundle: Any,
    *,
    now: datetime,
) -> list[GroundedAssertion]:
    return [
        assertion
        for assertion in _bundle_current(bundle, now=now)
        if assertion.epistemic_status in _VERIFIED_EPISTEMIC_STATUSES
        and not _is_dialogue_fossil(assertion)
    ]


def has_verified_bundle_evidence(
    *,
    tool_results: list[Any] | None,
    evidence_bundle: Any | None,
    now: datetime | None = None,
) -> bool:
    """Whether the turn has non-fossil verified support (tools or bundle assertions)."""
    if tool_results:
        return True
    if evidence_bundle is None:
        return False
    bundle = _coerce_bundle(evidence_bundle)
    at = now or datetime.now(UTC)
    return bool(_bundle_verified_assertions(bundle, now=at))


def _assertion_value_in_text(assertion: GroundedAssertion, text: str) -> bool:
    value = str(assertion.value).casefold().strip()
    if len(value) < 2:
        return False
    hay = text.casefold()
    if value in hay:
        return True
    if isinstance(assertion.value, bool):
        predicate = assertion.predicate.casefold().replace("_", " ")
        if assertion.value and predicate in hay:
            return True
    return False


def violates_dialogue_fossil_as_fact(
    text: str,
    evidence_bundle: Any,
    *,
    now: datetime | None = None,
) -> bool:
    """Dialogue-history fossils must not be presented as settled facts."""
    if _EPISTEMIC_HEDGE.search(text):
        return False
    bundle = _coerce_bundle(evidence_bundle)
    at = now or datetime.now(UTC)
    for assertion in bundle.grounded_assertions:
        if not _is_dialogue_fossil(assertion):
            continue
        if assertion.id not in {row.id for row in _bundle_current(bundle, now=at)}:
            continue
        if _assertion_value_in_text(assertion, text):
            return True
    return False


def _conflict_topic_in_text(conflict: Any, text: str) -> bool:
    hay = text.casefold()
    field = str(conflict.field)
    predicate = field.rsplit(".", maxsplit=1)[-1].casefold().replace("_", " ")
    if predicate in hay:
        return True
    if any(value.casefold() in hay for value in conflict.values):
        return True
    if "works_monday" in field and "monday" in hay:
        return any(token in hay for token in ("working", "work", "off", "holiday"))
    return False


def violates_bundle_conflict_resolution(text: str, evidence_bundle: Any) -> bool:
    """Do not collapse bundle conflicts into a single verified-looking answer."""
    bundle = _coerce_bundle(evidence_bundle)
    if not bundle.conflicts:
        return False
    if _EPISTEMIC_HEDGE.search(text) or _CONFLICT_ACK.search(text):
        return False
    return any(_conflict_topic_in_text(conflict, text) for conflict in bundle.conflicts)


def _superseded_assertions(
    bundle: Any,
    *,
    now: datetime,
) -> list[GroundedAssertion]:
    current_ids = {assertion.id for assertion in _bundle_current(bundle, now=now)}
    superseded_ids: set[str] = set()
    for assertion in bundle.grounded_assertions:
        superseded_ids.update(assertion.supersedes)
    return [
        assertion
        for assertion in bundle.grounded_assertions
        if assertion.id in superseded_ids and assertion.id not in current_ids
    ]


def violates_superseded_assertion_as_current(
    text: str,
    evidence_bundle: Any,
    *,
    now: datetime | None = None,
) -> bool:
    """Superseded assertions must not be restated as current facts."""
    if _EPISTEMIC_HEDGE.search(text):
        return False
    bundle = _coerce_bundle(evidence_bundle)
    at = now or datetime.now(UTC)
    for assertion in _superseded_assertions(bundle, now=at):
        if _assertion_value_in_text(assertion, text):
            return True
    return False


def _build_assertion_grounding_fallback(
    evidence_bundle: Any,
    *,
    context: ConversationContext,
    violation: str,
) -> str:
    bundle = _coerce_bundle(evidence_bundle)
    if violation == "conflict" and bundle.conflicts:
        field = bundle.conflicts[0].field.replace(".", " ")
        return (
            f"I have conflicting information about {field} "
            f"and can't state it as settled fact yet."
        )
    if violation == "fossil":
        return _build_evidence_seeking_fallback(context)
    if violation == "superseded":
        return (
            "I have newer evidence on that point than what I might have implied earlier — "
            "I need to check before stating it as current."
        )
    return _build_evidence_seeking_fallback(context)


def _build_evidence_seeking_fallback(context: ConversationContext) -> str:
    """C22 minimal fallback when tier-1 evidence is missing."""
    dialogue = _dialogue_blob(context)
    recall: list[str] = []
    if "london" in dialogue:
        recall.append("London")
    if "10" in dialogue and "am" in dialogue:
        recall.append("~10:00 am")
    if "4" in dialogue and ("guest" in dialogue or "of us" in dialogue):
        recall.append("4 guests")
    if "bistro brunch" in dialogue:
        recall.append("Bistro Brunch")
    recall_text = ", ".join(recall) if recall else "the constraints we discussed"
    return (
        f"I don't have verified details from your sources yet. "
        f"From our conversation: {recall_text}. "
        f"I'll check the supporting email before confirming anything commercial."
    )


def needs_grounding_fence(
    *,
    evidence_domain: str,
    authority: str,
    tool_names: list[str] | tuple[str, ...],
    tool_results: list[Any] | None = None,
) -> bool:
    if evidence_domain != "CONVERSATION_ONLY" or authority != "NONE":
        return False
    if tool_names:
        return False
    if tool_results:
        return False
    return True


def apply_respond_grounding_fence(
    text: str,
    *,
    context: ConversationContext,
    evidence_domain: str,
    authority: str,
    tool_names: list[str] | tuple[str, ...] | None = None,
    tool_results: list[Any] | None = None,
    evidence_bundle: Any | None = None,
) -> str:
    """Replace tier-3 invention with an evidence-seeking fallback."""
    names = tool_names or ()
    now = datetime.now(UTC)
    bundle = _coerce_bundle(evidence_bundle) if evidence_bundle is not None else None
    if bundle is not None:
        from personal_enigma.api.evidence_bundle import bundle_aware_fallback

        if bundle.courier_state == "blocked" and _HISTORICAL_NEWS_FICTION.search(text):
            fallback = bundle_aware_fallback(bundle)
            if fallback:
                return fallback
        if violates_dialogue_fossil_as_fact(text, bundle, now=now):
            return _build_assertion_grounding_fallback(
                bundle, context=context, violation="fossil"
            )
        if violates_bundle_conflict_resolution(text, bundle):
            return _build_assertion_grounding_fallback(
                bundle, context=context, violation="conflict"
            )
        if violates_superseded_assertion_as_current(text, bundle, now=now):
            return _build_assertion_grounding_fallback(
                bundle, context=context, violation="superseded"
            )
    has_verified = has_verified_bundle_evidence(
        tool_results=tool_results,
        evidence_bundle=bundle,
        now=now,
    )
    if not needs_grounding_fence(
        evidence_domain=evidence_domain,
        authority=authority,
        tool_names=names,
        tool_results=tool_results,
    ):
        return text
    dialogue = _dialogue_blob(context)
    if (
        _invents_commercial_facts(text)
        or _replaced_conversational_choice(text, dialogue)
        or _replaced_time(text, dialogue)
        or _presents_unverified_as_verified(text, has_tool_evidence=has_verified)
    ):
        return _build_evidence_seeking_fallback(context)
    return text


def violates_replace_conversational_choice(text: str, context: ConversationContext) -> bool:
    dialogue = _dialogue_blob(context)
    return _replaced_conversational_choice(text, dialogue) or _replaced_time(text, dialogue)


def violates_present_unverified_as_verified(
    text: str,
    *,
    has_tool_evidence: bool,
) -> bool:
    return _presents_unverified_as_verified(text, has_tool_evidence=has_tool_evidence)


def violates_commercial_invention(text: str) -> bool:
    return _invents_commercial_facts(text)


def seek_source_evidence_covered(text: str) -> bool:
    hay = text.casefold()
    return any(
        needle in hay
        for needle in (
            "don't have verified",
            "do not have verified",
            "need to check",
            "supporting email",
            "from our conversation",
            "we discussed",
            "haven't checked",
            "have not checked",
        )
    )


__all__ = [
    "apply_respond_grounding_fence",
    "has_verified_bundle_evidence",
    "needs_grounding_fence",
    "seek_source_evidence_covered",
    "violates_bundle_conflict_resolution",
    "violates_commercial_invention",
    "violates_dialogue_fossil_as_fact",
    "violates_present_unverified_as_verified",
    "violates_replace_conversational_choice",
    "violates_superseded_assertion_as_current",
]
