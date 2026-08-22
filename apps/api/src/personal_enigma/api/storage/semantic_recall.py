"""RECON-05C / C32 — vault / MemoryInventory authority for semantic recall.

Recall does not write. This adapter only answers: is this assertion id
currently retained and visible in inventory?

Constitutional rule (ADR-037):

    index ≠ authority

Approximate candidate IDs may be proposed by any ``CandidateAssertionIndex``
(scripted or embeddings). Only current MemoryInventory + vault payload may
establish recall eligibility. Embeddings integration is a separate slice.
"""

from __future__ import annotations

from datetime import UTC, datetime
from sqlite3 import Connection as SqlCipherConnection

from pydantic import ValidationError

from personal_enigma.api.storage.memory_inventory import list_memory_inventory
from personal_enigma.api.storage.retention_vault import VaultDurableAssertionStore
from personal_enigma.domain.grounding import GroundedAssertion
from personal_enigma.domain.retention import DerivedRecord


def _aware_utc(raw: object) -> datetime | None:
    """Parse validity timestamps the same way inventory does — naive means UTC."""
    if raw is None:
        return None
    if isinstance(raw, datetime):
        parsed = raw
    elif isinstance(raw, str) and raw:
        parsed = datetime.fromisoformat(raw)
    else:
        return None
    if parsed.tzinfo is None:
        return parsed.replace(tzinfo=UTC)
    return parsed


def assertion_from_retained_record(record: DerivedRecord) -> GroundedAssertion:
    """Rebuild the governed assertion from a vault payload. No status upgrade."""
    payload = record.payload
    assertion_id = payload.get("assertion_id")
    if not isinstance(assertion_id, str) or not assertion_id:
        msg = "Retained record missing assertion_id"
        raise ValueError(msg)
    return GroundedAssertion.model_validate(
        {
            "id": assertion_id,
            "kind": payload.get("kind") or "fact",
            "subject": payload.get("subject"),
            "predicate": payload.get("predicate"),
            "value": payload.get("value"),
            "scope": payload.get("scope"),
            "epistemic_status": payload.get("epistemic_status") or "unknown",
            "confidence": payload.get("confidence"),
            "evidence_refs": payload.get("evidence_refs") or [],
            "derived_from": payload.get("derived_from_assertion_ids") or [],
            "supersedes": payload.get("supersedes") or [],
            "purpose_tags": payload.get("purpose_tags") or [],
            "validity_kind": payload.get("validity_kind") or "stable",
            "temporal_scope": payload.get("temporal_scope"),
            "valid_from": _aware_utc(payload.get("valid_from")),
            "valid_until": _aware_utc(payload.get("valid_until")),
            "invalidated_by": payload.get("invalidated_by") or [],
        }
    )


class VaultInventoryAuthority:
    """Governed-memory lookup: inventory first, then vault payload.

    Inventory absence (forgotten, elapsed TTL, superseded) means not current,
    even if a vault row or stale embedding still exists.
    """

    def __init__(
        self,
        conn: SqlCipherConnection,
        store: VaultDurableAssertionStore,
        *,
        now: datetime | None = None,
    ) -> None:
        self._conn = conn
        self._store = store
        self._now = now

    def current_retained(self, assertion_id: str) -> GroundedAssertion | None:
        inventory = list_memory_inventory(self._conn, now=self._now)
        if inventory.get(assertion_id) is None:
            return None
        record = self._store.get_record(assertion_id)
        if record is None:
            return None
        try:
            return assertion_from_retained_record(record)
        except (TypeError, ValueError, ValidationError):
            # Fail this candidate closed. A reconstructable sibling must still
            # be judged independently — reconstruction errors are not writes.
            return None
