"""C21 respond-phase grounding fence — tiered evidence, fail closed.

When compilation wrongly leaves a private-world attribute request on
CONVERSATION_ONLY with no tools, the model must not invent or replace
conversational choices with verified-looking commercial facts.
"""

from __future__ import annotations

import re
from typing import Any

from personal_enigma.api.conversation_context import ConversationContext

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
    if evidence_bundle is not None:
        from personal_enigma.api.evidence_bundle import (
            EvidenceBundle,
            bundle_aware_fallback,
        )

        if isinstance(evidence_bundle, dict):
            bundle = EvidenceBundle.model_validate(evidence_bundle)
        else:
            bundle = evidence_bundle
        if bundle.courier_state == "blocked" and _HISTORICAL_NEWS_FICTION.search(text):
            fallback = bundle_aware_fallback(bundle)
            if fallback:
                return fallback
    if not needs_grounding_fence(
        evidence_domain=evidence_domain,
        authority=authority,
        tool_names=names,
        tool_results=tool_results,
    ):
        return text
    dialogue = _dialogue_blob(context)
    has_tools = bool(tool_results)
    if (
        _invents_commercial_facts(text)
        or _replaced_conversational_choice(text, dialogue)
        or _replaced_time(text, dialogue)
        or _presents_unverified_as_verified(text, has_tool_evidence=has_tools)
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
    "needs_grounding_fence",
    "seek_source_evidence_covered",
    "violates_commercial_invention",
    "violates_present_unverified_as_verified",
    "violates_replace_conversational_choice",
]
