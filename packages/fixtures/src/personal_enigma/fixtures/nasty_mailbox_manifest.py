"""SEC-04 synthetic nasty test mailbox — fixture manifest.

Maps the **nasty mailbox matrix** (hostile MIME categories) to fixture references
for SEC-04 evaluation. All content is **FICTIONAL / SYNTHETIC** — the Google TEST
account mailbox is seeded from this manifest; Oscar's inbox is **never** in scope.

Success criterion: every matrix row survives the full private pipeline:

```text
gmail.readonly → hostile MIME → canonical records → encrypted vault only
  → transform → SEC-02 egress gate
```

Corpus modules:
- ``adversarial_email_cases`` — SEC-03 injection scenarios (Alex demo + SEC-04 re-run)
- ``alex_sensitive_canaries`` — HIGH-sensitivity canary secrets (egress / shadow crash-test)
- ``packages/ingestion/tests/fixtures/gmail/nasty/`` — Gmail API JSON fixtures (SEC-04)
"""

from __future__ import annotations

from dataclasses import dataclass
from enum import StrEnum

from personal_enigma.fixtures.adversarial_email_cases import CASE_BY_ID
from personal_enigma.fixtures.alex_sensitive_canaries import (
    ALEX_SENSITIVE_CANARIES,
    CANARY_BY_ID,
)

PACK_ID = "nasty-mailbox-v1"
PACK_DESCRIPTION = (
    "Synthetic hostile mailbox matrix for SEC-04 — Google TEST account only, "
    "NOT Oscar's inbox. Proves real external source enters without bypassing "
    "the private architecture."
)

GMAIL_NASTY_FIXTURE_ROOT = "packages/ingestion/tests/fixtures/gmail/nasty"


class NastyMailboxCategory(StrEnum):
    """Hostile-input categories required in SEC-04 acceptance."""

    PLAIN_TEXT_INJECTION = "plain_text_injection"
    HTML_HIDDEN_INJECTION = "html_hidden_injection"
    QUOTED_REPLY_CONTENT = "quoted_reply_content"
    MULTIPART_MIME = "multipart_mime"
    MALICIOUS_ATTACHMENT_METADATA = "malicious_attachment_metadata"
    FAKE_SYSTEM_INSTRUCTIONS = "fake_system_instructions"
    EMBEDDED_URLS_TRACKING = "embedded_urls_tracking"
    OVERSIZED_MALFORMED_BODIES = "oversized_malformed_bodies"
    CANARY_SECRETS = "canary_secrets"


class FixtureKind(StrEnum):
    """Where the matrix row's payload lives."""

    ADVERSARIAL_EMAIL = "adversarial_email"
    SENSITIVE_CANARY = "sensitive_canary"
    GMAIL_API_JSON = "gmail_api_json"


@dataclass(frozen=True, slots=True)
class NastyMailboxMatrixEntry:
    """One row in the SEC-04 nasty mailbox matrix."""

    category: NastyMailboxCategory
    description: str
    fixture_kind: FixtureKind
    fixture_id: str
    gmail_fixture: str | None = None
    adversarial_case_id: str | None = None
    canary_id: str | None = None


# Gmail API JSON fixtures under GMAIL_NASTY_FIXTURE_ROOT (SEC-04 implementation).
_SEC04_GMAIL_FIXTURES: dict[str, str] = {
    "nasty-quoted-reply": "quoted_reply.json",
    "nasty-malicious-attachment-metadata": "malicious_attachment_metadata.json",
    "nasty-embedded-urls-tracking": "embedded_urls_tracking.json",
    "nasty-oversized-malformed-body": "oversized_malformed_body.json",
}


def _adversarial(
    category: NastyMailboxCategory,
    description: str,
    case_id: str,
) -> NastyMailboxMatrixEntry:
    return NastyMailboxMatrixEntry(
        category=category,
        description=description,
        fixture_kind=FixtureKind.ADVERSARIAL_EMAIL,
        fixture_id=case_id,
        adversarial_case_id=case_id,
    )


def _canary(category: NastyMailboxCategory, canary_id: str) -> NastyMailboxMatrixEntry:
    canary = CANARY_BY_ID[canary_id]
    return NastyMailboxMatrixEntry(
        category=category,
        description=f"Synthetic {canary.category} canary — sentinels must stay local",
        fixture_kind=FixtureKind.SENSITIVE_CANARY,
        fixture_id=canary_id,
        canary_id=canary_id,
    )


def _gmail(
    category: NastyMailboxCategory,
    description: str,
    fixture_id: str,
) -> NastyMailboxMatrixEntry:
    filename = _SEC04_GMAIL_FIXTURES[fixture_id]
    return NastyMailboxMatrixEntry(
        category=category,
        description=description,
        fixture_kind=FixtureKind.GMAIL_API_JSON,
        fixture_id=fixture_id,
        gmail_fixture=f"{GMAIL_NASTY_FIXTURE_ROOT}/{filename}",
    )


NASTY_MAILBOX_MATRIX: tuple[NastyMailboxMatrixEntry, ...] = (
    _adversarial(
        NastyMailboxCategory.PLAIN_TEXT_INJECTION,
        "Classic override / tool-forgery / credential phish in text/plain",
        "inj-ignore-previous-instructions",
    ),
    _adversarial(
        NastyMailboxCategory.PLAIN_TEXT_INJECTION,
        "Forged tool_call JSON in plain body",
        "inj-tool-call-forgery",
    ),
    _adversarial(
        NastyMailboxCategory.PLAIN_TEXT_INJECTION,
        "OAuth / API key phish in plain body",
        "inj-credential-phish",
    ),
    _adversarial(
        NastyMailboxCategory.HTML_HIDDEN_INJECTION,
        "display:none and zero-size span injection in text/html",
        "inj-html-hidden-text",
    ),
    _gmail(
        NastyMailboxCategory.QUOTED_REPLY_CONTENT,
        "Nested quoted/reply blocks with hostile injection below the fold",
        "nasty-quoted-reply",
    ),
    _adversarial(
        NastyMailboxCategory.MULTIPART_MIME,
        "Conflicting text/plain vs text/html parts (MIME confusion)",
        "inj-multipart-plain-html",
    ),
    _gmail(
        NastyMailboxCategory.MALICIOUS_ATTACHMENT_METADATA,
        "Attachment filename / Content-Type / Content-ID injection (lazy-fetch metadata only)",
        "nasty-malicious-attachment-metadata",
    ),
    _adversarial(
        NastyMailboxCategory.FAKE_SYSTEM_INSTRUCTIONS,
        "Body mimics [SYSTEM] / developer role markers",
        "inj-system-prompt-leak",
    ),
    _gmail(
        NastyMailboxCategory.EMBEDDED_URLS_TRACKING,
        "Tracking pixels, redirect chains, and data-URI payloads in HTML",
        "nasty-embedded-urls-tracking",
    ),
    _gmail(
        NastyMailboxCategory.OVERSIZED_MALFORMED_BODIES,
        "Oversized body, truncated MIME, invalid charset, malformed boundaries",
        "nasty-oversized-malformed-body",
    ),
    *(
        _canary(NastyMailboxCategory.CANARY_SECRETS, canary.id)
        for canary in ALEX_SENSITIVE_CANARIES
    ),
)

MATRIX_BY_CATEGORY: dict[NastyMailboxCategory, tuple[NastyMailboxMatrixEntry, ...]] = {}
for _entry in NASTY_MAILBOX_MATRIX:
    prior = MATRIX_BY_CATEGORY.get(_entry.category, ())
    MATRIX_BY_CATEGORY[_entry.category] = (*prior, _entry)


REQUIRED_CATEGORIES: frozenset[NastyMailboxCategory] = frozenset(NastyMailboxCategory)


def assert_nasty_mailbox_manifest_complete() -> None:
    """Sanity check — every matrix category covered; refs resolve."""
    covered = {entry.category for entry in NASTY_MAILBOX_MATRIX}
    missing = REQUIRED_CATEGORIES - covered
    assert not missing, f"Nasty mailbox matrix missing categories: {sorted(missing)}"

    for entry in NASTY_MAILBOX_MATRIX:
        if entry.fixture_kind == FixtureKind.ADVERSARIAL_EMAIL:
            assert entry.adversarial_case_id in CASE_BY_ID, entry.fixture_id
        elif entry.fixture_kind == FixtureKind.SENSITIVE_CANARY:
            assert entry.canary_id in CANARY_BY_ID, entry.fixture_id
        elif entry.fixture_kind == FixtureKind.GMAIL_API_JSON:
            assert entry.gmail_fixture is not None, entry.fixture_id


def matrix_summary() -> list[dict[str, str]]:
    """Human-readable manifest rows for tickets and operator runbooks."""
    return [
        {
            "category": entry.category.value,
            "fixture_kind": entry.fixture_kind.value,
            "fixture_id": entry.fixture_id,
            "gmail_fixture": entry.gmail_fixture or "",
            "description": entry.description,
        }
        for entry in NASTY_MAILBOX_MATRIX
    ]


__all__ = [
    "GMAIL_NASTY_FIXTURE_ROOT",
    "FixtureKind",
    "NASTY_MAILBOX_MATRIX",
    "MATRIX_BY_CATEGORY",
    "NastyMailboxCategory",
    "NastyMailboxMatrixEntry",
    "PACK_DESCRIPTION",
    "PACK_ID",
    "REQUIRED_CATEGORIES",
    "assert_nasty_mailbox_manifest_complete",
    "matrix_summary",
]
