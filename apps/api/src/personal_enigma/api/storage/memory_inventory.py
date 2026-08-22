"""RECON-05B / C29 slice 4 — vault-backed MemoryInventory query and correction.

Brain reads this projection. Forget stays on the existing cascade.
Correction mints a new retained row with supersession lineage.
"""

from __future__ import annotations

from datetime import datetime
from sqlite3 import Connection as SqlCipherConnection

from personal_enigma.api.storage.retention_forget import list_current_retained_records
from personal_enigma.api.storage.retention_vault import (
    RetentionVaultError,
    VaultDurableAssertionStore,
)
from personal_enigma.domain.grounding import GroundedAssertion
from personal_enigma.domain.memory_inventory import (
    MemoryInventory,
    MemoryWhy,
    project_memory_inventory,
)
from personal_enigma.domain.retention_gate import RetentionOutcome, evaluate_retention


def list_memory_inventory(
    conn: SqlCipherConnection,
    *,
    subject: str | None = None,
    now: datetime | None = None,
) -> MemoryInventory:
    """Current retained life-memory about an optional subject.

    Forgotten vault rows are already absent (SQL DELETE). The projector also
    hides elapsed-TTL rows before ``expire_ttl()``; that hide is not GC.
    Superseded rows are filtered by the projector. Raw source bodies are never
    loaded.
    """
    records = list_current_retained_records(conn)
    return project_memory_inventory(records, subject=subject, now=now)


def inspect_memory_why(
    conn: SqlCipherConnection,
    assertion_id: str,
    *,
    now: datetime | None = None,
) -> MemoryWhy | None:
    """Inspectable 'why do you remember this?' — purpose, provenance, lineage."""
    inventory = list_memory_inventory(conn, now=now)
    return inventory.why(assertion_id)


def correct_retained_assertion(
    store: VaultDurableAssertionStore,
    prior_assertion_id: str,
    correction: GroundedAssertion,
    *,
    now: datetime | None = None,
) -> str:
    """Write a superseding retained assertion. Never mutates the prior payload."""
    prior = store.get_record(prior_assertion_id)
    if prior is None:
        msg = f"No current retained assertion {prior_assertion_id!r} to correct"
        raise RetentionVaultError(msg)
    if correction.id == prior_assertion_id:
        msg = (
            "Correction must mint a new assertion id; "
            "in-place history rewrite is forbidden"
        )
        raise RetentionVaultError(msg)

    supersedes = list(correction.supersedes)
    if prior_assertion_id not in supersedes:
        supersedes.append(prior_assertion_id)
    derived_from = [
        ref
        for ref in correction.derived_from
        if ref != f"assertion:{prior_assertion_id}"
    ]
    if prior_assertion_id not in derived_from:
        derived_from.insert(0, prior_assertion_id)

    linked = correction.model_copy(
        update={"supersedes": supersedes, "derived_from": derived_from}
    )
    decision = evaluate_retention(linked, now=now)
    if decision.outcome not in (RetentionOutcome.DURABLE, RetentionOutcome.TTL):
        msg = (
            f"Correction {linked.id!r} is not retainable "
            f"({decision.outcome.value})"
        )
        raise RetentionVaultError(msg)
    return store.store(linked, decision)
