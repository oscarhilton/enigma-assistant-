"""SEC-04 nasty mailbox message catalog — id, mime, body ref, containment layer.

Complements ``nasty_mailbox_manifest`` with per-message fields required for
operator seeding of the Google TEST account nasty mailbox.
"""

from __future__ import annotations

from dataclasses import dataclass
from enum import StrEnum

from personal_enigma.fixtures.adversarial_email_cases import CASE_BY_ID, ContainmentLayer
from personal_enigma.fixtures.nasty_mailbox_manifest import (
    NASTY_MAILBOX_MATRIX,
    FixtureKind,
    NastyMailboxMatrixEntry,
)


class BodyRefKind(StrEnum):
    """How to resolve message body content for TEST account seeding."""

    ADVERSARIAL_CASE = "adversarial_case"
    CANARY = "canary"
    GMAIL_JSON = "gmail_json"


@dataclass(frozen=True, slots=True)
class NastyMailboxMessage:
    """One hostile message in the synthetic TEST mailbox."""

    id: str
    mime_type: str
    body_ref: str
    body_ref_kind: BodyRefKind
    expected_containment_layers: tuple[ContainmentLayer, ...]
    category: str
    description: str


def _layers_for_entry(entry: NastyMailboxMatrixEntry) -> tuple[ContainmentLayer, ...]:
    if entry.adversarial_case_id:
        case = CASE_BY_ID[entry.adversarial_case_id]
        return case.expected_layers
    if entry.canary_id:
        return (ContainmentLayer.EGRESS,)
    return (ContainmentLayer.PROMPT_INJECTION, ContainmentLayer.EGRESS)


def _mime_for_entry(entry: NastyMailboxMatrixEntry) -> str:
    if entry.adversarial_case_id:
        case = CASE_BY_ID[entry.adversarial_case_id]
        if case.body_html:
            return "multipart/alternative"
        return "text/plain"
    if entry.canary_id:
        return "text/plain"
    if entry.gmail_fixture and entry.gmail_fixture.endswith("malicious_attachment_metadata.json"):
        return "multipart/mixed"
    if entry.gmail_fixture and entry.gmail_fixture.endswith("embedded_urls_tracking.json"):
        return "text/html"
    if entry.gmail_fixture and entry.gmail_fixture.endswith("oversized_malformed_body.json"):
        return "text/plain"
    return "text/plain"


def _body_ref_for_entry(entry: NastyMailboxMatrixEntry) -> tuple[str, BodyRefKind]:
    if entry.fixture_kind == FixtureKind.ADVERSARIAL_EMAIL:
        return entry.fixture_id, BodyRefKind.ADVERSARIAL_CASE
    if entry.fixture_kind == FixtureKind.SENSITIVE_CANARY:
        return entry.fixture_id, BodyRefKind.CANARY
    assert entry.gmail_fixture is not None
    return entry.gmail_fixture, BodyRefKind.GMAIL_JSON


NASTY_MAILBOX_MESSAGES: tuple[NastyMailboxMessage, ...] = tuple(
    NastyMailboxMessage(
        id=entry.fixture_id,
        mime_type=_mime_for_entry(entry),
        body_ref=_body_ref_for_entry(entry)[0],
        body_ref_kind=_body_ref_for_entry(entry)[1],
        expected_containment_layers=_layers_for_entry(entry),
        category=entry.category.value,
        description=entry.description,
    )
    for entry in NASTY_MAILBOX_MATRIX
)


def message_by_id(message_id: str) -> NastyMailboxMessage | None:
    for row in NASTY_MAILBOX_MESSAGES:
        if row.id == message_id:
            return row
    return None


__all__ = [
    "BodyRefKind",
    "NASTY_MAILBOX_MESSAGES",
    "NastyMailboxMessage",
    "message_by_id",
]
