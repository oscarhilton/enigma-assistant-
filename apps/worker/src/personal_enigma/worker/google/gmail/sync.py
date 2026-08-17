"""Gmail sync job for the worker (ticket M11 / SEC-04).

Runs local Gmail ingestion via ``GmailSource``; persists to encrypted PrivateVault
when a vault is supplied. Never requires remote LLM.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from personal_enigma.api.google.gmail.pipeline import GmailIngestResult, ingest_gmail_to_vault
from personal_enigma.api.storage.vault import PrivateVault
from personal_enigma.ingestion.gmail_persistence import assert_gmail_encrypted_vault_persistence
from personal_enigma.ingestion.protocol import ChangeBatch, SyncCursor
from personal_enigma.ingestion.sources.gmail import GmailSource


@dataclass(frozen=True, slots=True)
class GmailSyncRequest:
    """Parameters for a single Gmail sync pass."""

    access_token: str
    cursor_value: str | None = None
    remote_llm_enabled: bool = False


@dataclass(frozen=True, slots=True)
class GmailSyncResult:
    """Outcome of a Gmail sync job."""

    message_count: int
    next_cursor: str | None
    remote_llm_enabled: bool
    vault_records: int = 0


async def run_gmail_sync(
    request: GmailSyncRequest,
    *,
    source: GmailSource | None = None,
    vault: PrivateVault | None = None,
    skip_persistence_guard: bool = False,
    **source_kwargs: Any,
) -> GmailSyncResult:
    """Execute read-only Gmail ingestion (inject ``source`` / ``vault`` in tests)."""
    if not skip_persistence_guard:
        assert_gmail_encrypted_vault_persistence()
    gmail = source or GmailSource(
        access_token=request.access_token,
        remote_llm_enabled=request.remote_llm_enabled,
        enforce_encrypted_vault=not skip_persistence_guard,
        **source_kwargs,
    )
    cursor = (
        SyncCursor(value=request.cursor_value, source="gmail")
        if request.cursor_value
        else None
    )

    if vault is not None:
        ingest: GmailIngestResult = await ingest_gmail_to_vault(gmail, vault, cursor=cursor)
        return GmailSyncResult(
            message_count=ingest.message_count,
            next_cursor=ingest.next_cursor,
            remote_llm_enabled=request.remote_llm_enabled,
            vault_records=ingest.message_count,
        )

    batch: ChangeBatch = await gmail.get_changes(cursor)
    next_value = batch.next_cursor.value if batch.next_cursor else None
    return GmailSyncResult(
        message_count=len(batch.items),
        next_cursor=next_value,
        remote_llm_enabled=request.remote_llm_enabled,
    )
