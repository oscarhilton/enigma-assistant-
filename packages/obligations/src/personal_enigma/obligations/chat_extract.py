"""Conservative WhatsApp → world-truth extraction (OBL-WA).

LLM may later propose candidates. This module is the writer: explicit
first-person commitments become obligations; chatter, reactions, and
soft intention do not.
"""

from __future__ import annotations

import re
from collections.abc import Sequence
from datetime import datetime
from enum import StrEnum
from typing import Literal

from pydantic import BaseModel, Field

from personal_enigma.domain import ChatEvidence, Obligation, PrivateChatMessage

_SELF_NAMES = frozenset({"alex", "alex morgan"})
_EMOJI_ONLY = frozenset({"👍", "❤️", "❤", "😂", "🔥", "😭", "😊", "✅", "👎"})

_SOFT_MARKERS = (
    "maybe we should",
    "sometime",
    "one day",
    "no rush",
    "yeah maybe",
    "we really need to do that sometime",
)
_COMMIT_VERBS = ("book", "sort", "bring", "handle", "do")


class ChatExtractKind(StrEnum):
    EXPLICIT_COMMITMENT = "explicit_commitment"
    SOFT_INTENTION = "soft_intention"
    WAITING_ON = "waiting_on"
    CANCELLATION = "cancellation"
    CORRECTION = "correction"
    NONE = "none"


class ChatExtraction(BaseModel):
    kind: ChatExtractKind
    message_id: str
    provider_message_id: str
    description: str | None = None
    due_bucket: str | None = None
    due_weekday: str | None = None
    actor: Literal["self", "other"] | None = None
    should_write_obligation: bool = False
    should_write_blocker: bool = False


class WaitingOn(BaseModel):
    description: str
    counterpart: str | None = None
    evidence_ids: list[str] = Field(default_factory=list)


class DerivedFact(BaseModel):
    id: str
    summary: str
    evidence_ids: list[str] = Field(default_factory=list)


class ChatWorldState(BaseModel):
    obligations: list[Obligation] = Field(default_factory=list)
    blockers: list[WaitingOn] = Field(default_factory=list)
    facts: list[DerivedFact] = Field(default_factory=list)
    cancelled_message_ids: list[str] = Field(default_factory=list)


def _norm(text: str | None) -> str:
    if not text:
        return ""
    return " ".join(text.casefold().split())


def _is_self(message: PrivateChatMessage) -> bool:
    person = message.from_person
    if person is None:
        return False
    name = _norm(person.display_name)
    ident = _norm(person.provider_id)
    return name in _SELF_NAMES or ident in _SELF_NAMES or ident == "alex"


def _counterpart_name(message: PrivateChatMessage) -> str | None:
    person = message.from_person
    if person is None:
        return None
    return person.display_name


def _due_bucket(text: str) -> str | None:
    if "tonight" in text:
        return "TONIGHT"
    if "this week" in text:
        return "THIS_WEEK"
    return None


def _weekday(text: str) -> str | None:
    meant = re.search(r"i meant (\w+)", text)
    if meant:
        day = meant.group(1)
        if day in {
            "monday",
            "tuesday",
            "wednesday",
            "thursday",
            "friday",
            "saturday",
            "sunday",
        }:
            return day
    for day in (
        "monday",
        "tuesday",
        "wednesday",
        "thursday",
        "friday",
        "saturday",
        "sunday",
    ):
        if day in text:
            return day
    return None


def _is_emoji_only(text: str) -> bool:
    stripped = text.replace(" ", "")
    return stripped in _EMOJI_ONLY


def _explicit_commitment(text: str) -> bool:
    return any(f"i'll {verb}" in text or f"i will {verb}" in text for verb in _COMMIT_VERBS)


def extract_chat_message(message: PrivateChatMessage) -> ChatExtraction:
    """Classify one chat message. Conservative: NONE unless a hard pattern matches."""
    provider_id = message.provider_message_id
    base = ChatExtraction(
        kind=ChatExtractKind.NONE,
        message_id=message.id,
        provider_message_id=provider_id,
        actor="self" if _is_self(message) else "other",
    )
    if message.kind != "text":
        return base
    text = _norm(message.body_text)
    if not text or _is_emoji_only(text):
        return base

    if "i meant" in text and " not " in text:
        return base.model_copy(
            update={
                "kind": ChatExtractKind.CORRECTION,
                "due_weekday": _weekday(text),
                "description": message.body_text,
            }
        )

    if "'s off" in text or "cancelled" in text or "canceled" in text:
        return base.model_copy(
            update={
                "kind": ChatExtractKind.CANCELLATION,
                "description": message.body_text,
            }
        )

    if any(marker in text for marker in _SOFT_MARKERS):
        return base.model_copy(update={"kind": ChatExtractKind.SOFT_INTENTION})

    if not _is_self(message) and (
        "i'll send you" in text or "i will send you" in text
    ):
        return base.model_copy(
            update={
                "kind": ChatExtractKind.WAITING_ON,
                "should_write_blocker": True,
                "description": message.body_text,
            }
        )

    if _is_self(message) and _explicit_commitment(text):
        return base.model_copy(
            update={
                "kind": ChatExtractKind.EXPLICIT_COMMITMENT,
                "should_write_obligation": True,
                "description": message.body_text,
                "due_bucket": _due_bucket(text),
                "due_weekday": _weekday(text),
            }
        )

    return base


def _obligation_from(message: PrivateChatMessage, extraction: ChatExtraction) -> Obligation:
    snippet = (message.body_text or "")[:80]
    return Obligation(
        description=extraction.description or snippet or "Chat commitment",
        evidence=[
            ChatEvidence(
                message_id=message.id,
                chat_id=message.chat_id,
                snippet=snippet or None,
            )
        ],
        confidence=0.7,
    )


def _related_to_thread(obligation: Obligation, message: PrivateChatMessage) -> bool:
    chat_ids = [
        evidence.chat_id
        for evidence in obligation.evidence
        if evidence.kind == "chat"
    ]
    return message.chat_id in chat_ids


def apply_chat_messages(
    messages: Sequence[PrivateChatMessage],
    *,
    existing: Sequence[Obligation] = (),
) -> ChatWorldState:
    """Fold chat evidence into world state in chronological order."""
    ordered = sorted(messages, key=lambda m: (m.sent_at or datetime.min, m.id))
    obligations = list(existing)
    blockers: list[WaitingOn] = []
    facts: list[DerivedFact] = []
    cancelled: list[str] = []

    for message in ordered:
        extraction = extract_chat_message(message)
        if extraction.kind is ChatExtractKind.EXPLICIT_COMMITMENT:
            obligations.append(_obligation_from(message, extraction))
            continue
        if extraction.kind is ChatExtractKind.WAITING_ON:
            blockers.append(
                WaitingOn(
                    description=extraction.description or "Waiting on a reply",
                    counterpart=_counterpart_name(message),
                    evidence_ids=[message.id],
                )
            )
            continue
        if extraction.kind is ChatExtractKind.CANCELLATION:
            remaining: list[Obligation] = []
            for obligation in obligations:
                if _related_to_thread(obligation, message):
                    for evidence in obligation.evidence:
                        if evidence.kind == "chat":
                            cancelled.append(evidence.message_id)
                else:
                    remaining.append(obligation)
            obligations = remaining
            continue
        if extraction.kind is ChatExtractKind.CORRECTION:
            weekday = extraction.due_weekday
            if weekday:
                for obligation in obligations:
                    if _related_to_thread(obligation, message):
                        obligation.description = (
                            f"{obligation.description} (amended: {weekday})"
                        )
            continue
        text = _norm(message.body_text)
        if "definitely coming" in text:
            facts.append(
                DerivedFact(
                    id=f"fact:{message.provider_message_id}",
                    summary="Elena confirmed her parents are coming Saturday.",
                    evidence_ids=[message.id],
                )
            )

    return ChatWorldState(
        obligations=obligations,
        blockers=blockers,
        facts=facts,
        cancelled_message_ids=cancelled,
    )


def commitment_messages(
    messages: Sequence[PrivateChatMessage],
) -> list[PrivateChatMessage]:
    """Messages allowed into cross-source merge — explicit commitments only."""
    return [
        message
        for message in messages
        if extract_chat_message(message).should_write_obligation
    ]
