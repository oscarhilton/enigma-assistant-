"""RECON-05B / C29 slice 3 — retained-assertion forget propagation and TTL expiry.

Uses SEC-06 ``derived_source_deps`` lineage. TTL expiry invokes the same
cascade as explicit forget — governed forgetting, not a side-channel cleanup.

Forgetting is semantic: unjustified rows are deleted from ``derived_records``.
Survivors lose forgotten lineage refs. Forget never writes a negation.

Current memory is the vault derived table after that cascade — not a hide-filter.
Cryptographic page-shredding of SQLCipher ciphertext is a later storage layer.
"""

from __future__ import annotations

import json
from datetime import UTC, datetime
from sqlite3 import Connection as SqlCipherConnection

from personal_enigma.api.storage.derived import (
    append_forget_audit,
    delete_derived_record,
    get_derived_record,
    insert_derived_record,
    list_all_derived_records,
    list_derived_records_for_source,
)
from personal_enigma.api.storage.forget import _existing_source_ids
from personal_enigma.api.storage.retention_vault import (
    assertion_lineage_ref,
    is_retained_assertion_record,
    list_retained_assertion_ids,
    retention_decision_lineage_ref,
)
from personal_enigma.domain.retention import DerivedRecord
from personal_enigma.domain.retention_gate import ForgetCascadeResult

_TRIGGER_FORGET = "forget"
_TRIGGER_TTL = "ttl_expiry"


def refs_for_assertion(assertion_id: str) -> frozenset[str]:
    """Lineage refs removed when an assertion is forgotten."""
    return frozenset(
        {
            assertion_id,
            assertion_lineage_ref(assertion_id),
            retention_decision_lineage_ref(assertion_id),
        }
    )


def _assertion_id_from_lineage_ref(ref: str) -> str | None:
    if ref.startswith("assertion:"):
        return ref[len("assertion:") :]
    if ref.startswith("retention_decision:"):
        return ref[len("retention_decision:") :]
    return None


def _is_self_ref(ref: str, record_id: str) -> bool:
    if ref == record_id:
        return True
    assertion_id = _assertion_id_from_lineage_ref(ref)
    return assertion_id == record_id


def _remaining_lineage_sources(
    *,
    record_id: str,
    derived_from: list[str],
    forgotten_refs: frozenset[str],
    active_assertion_ids: frozenset[str],
    active_source_ids: frozenset[str],
    active_derived_ids: frozenset[str],
) -> list[str]:
    """Sources that still justify a derived row after forgetting.

    Independent justification is a live retained assertion, a live source
    record, or another live derived row. Self-refs and dangling evidence
    tokens (``EV_*`` strings with no backing row) are not justification.
    """
    remaining: list[str] = []
    for ref in derived_from:
        if ref in forgotten_refs:
            if ref in active_source_ids:
                remaining.append(ref)
            continue
        if ref.startswith("retention_decision:"):
            continue
        if _is_self_ref(ref, record_id):
            continue
        assertion_id = _assertion_id_from_lineage_ref(ref)
        if assertion_id is not None:
            if assertion_id in active_assertion_ids:
                remaining.append(ref)
            continue
        if ref in active_assertion_ids:
            remaining.append(ref)
            continue
        if ref in active_source_ids:
            remaining.append(ref)
            continue
        if ref in active_derived_ids:
            remaining.append(ref)
            continue
    return remaining


def _collect_dependent_record_ids(
    conn: SqlCipherConnection,
    root_refs: frozenset[str],
) -> set[str]:
    """Records transitively depending on any ref in ``root_refs``."""
    dependents: set[str] = set()
    queue = list(root_refs)
    seen_refs: set[str] = set(root_refs)

    while queue:
        ref = queue.pop()
        for record in list_derived_records_for_source(conn, ref):
            if record.id in dependents:
                continue
            dependents.add(record.id)
            for dep_ref in (record.id, assertion_lineage_ref(record.id)):
                if dep_ref not in seen_refs:
                    seen_refs.add(dep_ref)
                    queue.append(dep_ref)
    return dependents


def _forgotten_refs_for(assertion_id: str, deleted_ids: set[str]) -> frozenset[str]:
    refs: set[str] = set(refs_for_assertion(assertion_id))
    for deleted_id in deleted_ids:
        refs.update(refs_for_assertion(deleted_id))
    return frozenset(refs)


def resolve_retained_assertion_forget_plan(
    conn: SqlCipherConnection,
    assertion_id: str,
) -> tuple[set[str], set[str]]:
    """Compute derived rows to delete vs survive when forgetting a retained assertion."""
    root_refs = refs_for_assertion(assertion_id)
    candidates = _collect_dependent_record_ids(conn, root_refs)
    forgotten_refs: set[str] = set(root_refs)
    to_delete: set[str] = set()

    changed = True
    while changed:
        changed = False
        active_assertions = frozenset(
            aid
            for aid in list_retained_assertion_ids(conn)
            if aid not in to_delete and aid != assertion_id
        )
        active_sources = frozenset(_existing_source_ids(conn))
        active_derived = frozenset(
            record.id
            for record in list_all_derived_records(conn)
            if record.id not in to_delete and record.id != assertion_id
        )

        for record in list_all_derived_records(conn):
            if record.id not in candidates or record.id in to_delete:
                continue
            remaining = _remaining_lineage_sources(
                record_id=record.id,
                derived_from=record.lineage.derived_from,
                forgotten_refs=frozenset(forgotten_refs),
                active_assertion_ids=active_assertions,
                active_source_ids=active_sources,
                active_derived_ids=active_derived,
            )
            if not remaining:
                to_delete.add(record.id)
                forgotten_refs.update(refs_for_assertion(record.id))
                changed = True

    if assertion_id in list_retained_assertion_ids(conn):
        to_delete.add(assertion_id)

    to_survive: set[str] = set()
    for record in list_all_derived_records(conn):
        if record.id in candidates and record.id not in to_delete:
            to_survive.add(record.id)

    return to_delete, to_survive


def _classify_record_id(
    conn: SqlCipherConnection,
    record_id: str,
) -> str:
    record = get_derived_record(conn, record_id)
    if record is not None and is_retained_assertion_record(record):
        return "assertion"
    return "derivative"


def _strip_forgotten_justification(
    conn: SqlCipherConnection,
    *,
    to_delete: set[str],
    forgotten_refs: frozenset[str],
) -> None:
    """Survivors keep independent evidence and lose forgotten lineage refs."""
    active_sources = frozenset(_existing_source_ids(conn))
    for record in list_all_derived_records(conn):
        if record.id in to_delete:
            continue
        remaining = [
            ref
            for ref in record.lineage.derived_from
            if ref not in forgotten_refs or ref in active_sources
        ]
        if remaining == record.lineage.derived_from:
            continue
        updated = record.model_copy(
            update={
                "lineage": record.lineage.model_copy(update={"derived_from": remaining}),
            }
        )
        insert_derived_record(conn, updated)


def forget_retained_assertion_with_propagation(
    conn: SqlCipherConnection,
    assertion_id: str,
    *,
    trigger: str = _TRIGGER_FORGET,
) -> ForgetCascadeResult:
    """Forget a retained assertion and invalidate unjustified derivatives.

    Deletes unjustified rows. Does not insert a contradictory assertion —
    unavailable is not false, and later independent evidence may re-establish
    the same proposition with a new id and lineage.
    """
    to_delete, to_survive = resolve_retained_assertion_forget_plan(conn, assertion_id)

    deleted_assertions: list[str] = []
    deleted_derivatives: list[str] = []
    for record_id in sorted(to_delete):
        kind = _classify_record_id(conn, record_id)
        if kind == "assertion":
            deleted_assertions.append(record_id)
        else:
            deleted_derivatives.append(record_id)

    forgotten_refs = _forgotten_refs_for(assertion_id, to_delete)
    _strip_forgotten_justification(
        conn, to_delete=to_delete, forgotten_refs=forgotten_refs
    )

    for record_id in sorted(to_delete, reverse=True):
        delete_derived_record(conn, record_id)

    audit_id = append_forget_audit(
        conn,
        source_id=assertion_lineage_ref(assertion_id),
        deleted_derived_ids=sorted(to_delete),
        surviving_derived_ids=sorted(to_survive),
        blob_ref=None,
    )

    if assertion_id in deleted_assertions:
        deleted_assertions.remove(assertion_id)
        deleted_assertions.insert(0, assertion_id)

    return ForgetCascadeResult(
        root_assertion_id=assertion_id,
        deleted_assertion_ids=deleted_assertions,
        deleted_derived_ids=deleted_derivatives,
        audit_id=audit_id,
        trigger=trigger,
    )


def find_expired_retained_assertion_ids(
    conn: SqlCipherConnection,
    *,
    now: datetime | None = None,
) -> list[str]:
    """Return retained assertion ids whose TTL ``valid_until`` has elapsed."""
    current = now or datetime.now(tz=UTC)
    expired: list[str] = []
    for record in list_all_derived_records(conn):
        if not is_retained_assertion_record(record):
            continue
        decision = record.payload.get("retention_decision")
        if not isinstance(decision, dict):
            continue
        if decision.get("outcome") != "ttl":
            continue
        valid_until_raw = record.payload.get("valid_until")
        if not isinstance(valid_until_raw, str):
            continue
        valid_until = datetime.fromisoformat(valid_until_raw)
        if valid_until.tzinfo is None:
            valid_until = valid_until.replace(tzinfo=UTC)
        if valid_until <= current:
            assertion_id = record.payload.get("assertion_id")
            if isinstance(assertion_id, str):
                expired.append(assertion_id)
    return sorted(expired)


def expire_retained_assertions(
    conn: SqlCipherConnection,
    *,
    now: datetime | None = None,
) -> list[ForgetCascadeResult]:
    """TTL expiry — same forget cascade as explicit deletion, not a cleanup DELETE."""
    results: list[ForgetCascadeResult] = []
    for assertion_id in find_expired_retained_assertion_ids(conn, now=now):
        results.append(
            forget_retained_assertion_with_propagation(
                conn,
                assertion_id,
                trigger=_TRIGGER_TTL,
            )
        )
    return results


def list_current_memory_records(conn: SqlCipherConnection) -> list[DerivedRecord]:
    """Every derived row still in the vault.

    Forgotten/expired rows are deleted from ``derived_records``. This is the
    current-memory surface — not a filtered projection that hides live rows.
    """
    return list_all_derived_records(conn)


def list_current_retained_records(conn: SqlCipherConnection) -> list[DerivedRecord]:
    """Retained assertion vault rows still recoverable as current memory."""
    return [
        record
        for record in list_current_memory_records(conn)
        if is_retained_assertion_record(record)
    ]


def retained_assertion_is_current(
    conn: SqlCipherConnection,
    assertion_id: str,
) -> bool:
    """True when the assertion exists in vault and is not forgotten/expired."""
    return assertion_id in list_retained_assertion_ids(conn)


def find_current_retained_by_content(
    conn: SqlCipherConnection,
    *,
    subject: str | None = None,
    predicate: str | None = None,
    value: str | None = None,
) -> list[DerivedRecord]:
    """Search current retained assertions — returns empty after forget/expiry."""
    matches: list[DerivedRecord] = []
    for record in list_current_retained_records(conn):
        payload = record.payload
        if subject is not None and payload.get("subject") != subject:
            continue
        if predicate is not None and payload.get("predicate") != predicate:
            continue
        if value is not None and payload.get("value") != value:
            continue
        matches.append(record)
    return matches


def _record_search_blob(record: DerivedRecord) -> str:
    return json.dumps(
        {
            "id": record.id,
            "payload": record.payload,
            "derived_from": record.lineage.derived_from,
        },
        sort_keys=True,
        default=str,
    )


def current_memory_record_ids_mentioning(
    conn: SqlCipherConnection,
    needle: str,
) -> list[str]:
    """Ids of current derived rows whose payload or lineage mentions ``needle``."""
    lowered = needle.lower()
    hits: list[str] = []
    for record in list_current_memory_records(conn):
        if lowered in _record_search_blob(record).lower():
            hits.append(record.id)
    return hits
