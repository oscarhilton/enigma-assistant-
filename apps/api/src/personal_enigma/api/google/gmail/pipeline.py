"""SEC-04 Gmail ingestion pipeline — encrypted vault, transform, egress boundary."""

from __future__ import annotations

import json
import os
from dataclasses import dataclass
from datetime import UTC, datetime
from typing import Any

from personal_enigma.api.storage.source_record import SourceRecord
from personal_enigma.api.storage.vault import PrivateVault, search_directory_for_plaintext
from personal_enigma.domain import PrivateMessage, SourceType
from personal_enigma.ingestion.gmail_mime import ParsedGmailBody
from personal_enigma.ingestion.gmail_persistence import assert_gmail_encrypted_vault_persistence
from personal_enigma.ingestion.protocol import SyncCursor
from personal_enigma.ingestion.sources.gmail import GmailSource
from personal_enigma.privacy import PrivacyLevel, default_level_for_source
from personal_enigma.privacy.egress import PrivateRaw, build_audited_egress_gate
from personal_enigma.privacy.remote import RemoteInferenceConfig
from personal_enigma.transformation import TransformedContext

ENV_GMAIL_LIVE = "ENIGMA_GMAIL_LIVE"


@dataclass(frozen=True, slots=True)
class GmailVaultRecord:
    """One ingested Gmail message persisted to encrypted vault."""

    message: PrivateMessage
    parsed: ParsedGmailBody
    source_record: SourceRecord


@dataclass(frozen=True, slots=True)
class GmailIngestResult:
    """Outcome of a Gmail → vault ingest pass."""

    records: tuple[GmailVaultRecord, ...]
    next_cursor: str | None
    message_count: int


def gmail_live_sync_enabled() -> bool:
    """Return True when live Google Gmail sync is explicitly enabled."""
    return os.environ.get(ENV_GMAIL_LIVE, "").strip().lower() in {"1", "true", "yes"}


def build_private_raw_envelope(
    message: PrivateMessage,
    parsed: ParsedGmailBody,
    *,
    raw_gmail: dict[str, Any] | None = None,
) -> bytes:
    """Canonical PRIVATE_RAW JSON stored as encrypted blob (not plaintext SQLite)."""
    envelope = {
        "classification": "PRIVATE_RAW",
        "source": "gmail",
        "provider_message_id": message.provider_message_id,
        "thread_id": message.thread_id,
        "subject": message.subject,
        "snippet": message.snippet,
        "body_text": message.body_text,
        "body_plain": parsed.plain_text,
        "body_html": parsed.html_text,
        "mime_type": parsed.mime_type,
        "untrusted": parsed.untrusted,
        "parse_warnings": list(parsed.parse_warnings),
        "attachments": [
            {
                "filename": att.filename,
                "mime_type": att.mime_type,
                "attachment_id": att.attachment_id,
                "size": att.size,
                "content_id": att.content_id,
            }
            for att in parsed.attachments
        ],
        "labels": message.labels,
        "sent_at": message.sent_at.isoformat() if message.sent_at else None,
        "received_at": message.received_at.isoformat() if message.received_at else None,
    }
    if raw_gmail is not None:
        envelope["gmail_api_snapshot"] = raw_gmail
    return json.dumps(envelope, ensure_ascii=False).encode("utf-8")


def transform_message_for_remote(message: PrivateMessage) -> TransformedContext:
    """Privacy transform — snippet/summary only; wholesale body never transmitted."""
    return TransformedContext(
        summary=message.snippet or (message.subject or "Email message"),
        entities=[],
        metadata={
            "source_type": SourceType.EMAIL.value,
            "record_id": message.id,
            "provider": message.provider,
            "wholesale_body_included": False,
            "untrusted": True,
            "privacy_level": default_level_for_source(SourceType.EMAIL).value,
        },
        may_transmit_remotely=True,
    )


async def ingest_gmail_to_vault(
    source: GmailSource,
    vault: PrivateVault,
    *,
    cursor: SyncCursor | None = None,
    raw_messages: dict[str, dict[str, Any]] | None = None,
) -> GmailIngestResult:
    """Fetch Gmail changes and persist PRIVATE_RAW envelopes to encrypted vault only."""
    assert_gmail_encrypted_vault_persistence(
        persistence_backend="encrypted_vault",
        database_path=vault.paths.vault_db,
    )
    batch = await source.get_changes(cursor)
    records: list[GmailVaultRecord] = []

    for item in batch.items:
        message = PrivateMessage.model_validate(item)
        raw = raw_messages.get(message.provider_message_id) if raw_messages else None
        if raw is None:
            raw = await source._fetch_message_raw(message.provider_message_id)
        payload = raw.get("payload") if isinstance(raw, dict) else None
        parsed = source.parse_payload(payload if isinstance(payload, dict) else None)
        message = source.message_from_gmail(raw, parsed=parsed)

        body_bytes = build_private_raw_envelope(message, parsed, raw_gmail=raw)
        source_record = vault.store_raw_source(
            source="gmail",
            external_id=message.provider_message_id,
            raw_content=body_bytes,
            received_at=message.received_at or datetime.now(tz=UTC),
        )
        records.append(
            GmailVaultRecord(message=message, parsed=parsed, source_record=source_record)
        )

    next_value = batch.next_cursor.value if batch.next_cursor else None
    return GmailIngestResult(
        records=tuple(records),
        next_cursor=next_value,
        message_count=len(records),
    )


def assert_no_plaintext_source_persistence(
    vault: PrivateVault,
    needles: tuple[str, ...],
) -> None:
    """Hard FAIL if sensitive plaintext appears outside encrypted blobs."""
    hits = search_directory_for_plaintext(vault.paths.root, needles)
    # vault.db and blob files are encrypted — plaintext must not appear on disk.
    readable_hits = [
        (path, needle)
        for path, needle in hits
        if path.name not in {vault.paths.vault_db.name} and "blobs" not in path.parts
    ]
    if readable_hits:
        detail = ", ".join(f"{path}:{needle!r}" for path, needle in readable_hits[:5])
        raise AssertionError(f"Plaintext source persistence detected: {detail}")


def assert_canaries_blocked_at_egress(
    gate: Any,
    *,
    sentinel_strings: tuple[str, ...],
) -> None:
    """Hard FAIL if canary sentinels would cross the SEC-02 egress gate."""
    for sentinel in sentinel_strings:
        result = gate.send(sentinel, purpose="conversation.orchestrate")
        if result.sent:
            raise AssertionError(f"Canary sentinel crossed egress gate: {sentinel!r}")
        raw = gate.send(
            PrivateRaw({"body": sentinel, "source_id": "gmail-canary-test"}),
            purpose="conversation.orchestrate",
        )
        if raw.sent:
            raise AssertionError(f"PrivateRaw canary crossed egress gate: {sentinel!r}")


def build_test_egress_gate() -> Any:
    """Audited egress gate for SEC-04 integration tests."""
    return build_audited_egress_gate(remote_config=RemoteInferenceConfig(enabled=True))


def assert_transform_excludes_body(
    message: PrivateMessage,
    *,
    forbidden_substrings: tuple[str, ...],
) -> TransformedContext:
    """Verify privacy transform never includes wholesale body or canary sentinels."""
    remote_view = transform_message_for_remote(message)
    blob = json.dumps(remote_view.model_dump(mode="json"))
    if message.body_text and message.body_text in blob:
        raise AssertionError("Wholesale body_text leaked into transformed context")
    for needle in forbidden_substrings:
        if needle in blob:
            raise AssertionError(f"Forbidden substring in transformed context: {needle!r}")
    assert remote_view.metadata.get("wholesale_body_included") is False
    assert remote_view.metadata.get("untrusted") is True
    assert default_level_for_source(SourceType.EMAIL) == PrivacyLevel.MEDIUM
    return remote_view


__all__ = [
    "GmailIngestResult",
    "GmailVaultRecord",
    "assert_canaries_blocked_at_egress",
    "assert_no_plaintext_source_persistence",
    "assert_transform_excludes_body",
    "build_private_raw_envelope",
    "build_test_egress_gate",
    "gmail_live_sync_enabled",
    "ingest_gmail_to_vault",
    "transform_message_for_remote",
]
