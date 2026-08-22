"""RECON-05A / C29 slice 2 — retention gate → SEC-06 vault bridge.

Legal write path::

    GroundedAssertion
      → evaluate_retention()
      → RetentionDecision (DURABLE | TTL)
      → map_retention_to_derived_record()
      → PrivateVault.store_derived()

Direct ``GroundedAssertion → vault`` writes are forbidden: only gated retained-assertion
records (``record_kind=retained_assertion``) count as life-memory retention.
"""

from __future__ import annotations

from datetime import UTC, datetime
from sqlite3 import Connection as SqlCipherConnection

from personal_enigma.api.storage.derived import list_all_derived_records
from personal_enigma.api.storage.vault import PrivateVault
from personal_enigma.domain.grounding import AssertionKind, EpistemicStatus, GroundedAssertion
from personal_enigma.domain.memory_inventory import RETAINED_ASSERTION_RECORD_KIND
from personal_enigma.domain.retention import (
    DerivedRecord,
    DerivedRecordType,
    LineageMetadata,
    MemoryLayer,
    RetentionPurpose,
)
from personal_enigma.domain.retention_gate import (
    RetentionDecision,
    RetentionOutcome,
    evaluate_retention,
)

_ASSERTION_LINEAGE_PREFIX = "assertion:"
_RETENTION_DECISION_PREFIX = "retention_decision:"

_INFERENCE_NOT_DURABLE_STATUSES = frozenset({EpistemicStatus.MODEL_INFERRED})


class RetentionVaultError(Exception):
    """Raised when a vault write violates C29 retention invariants."""


def assertion_lineage_ref(assertion_id: str) -> str:
    """Lineage ref pointing back to the grounded assertion."""

    return f"{_ASSERTION_LINEAGE_PREFIX}{assertion_id}"


def retention_decision_lineage_ref(assertion_id: str) -> str:
    """Lineage ref pointing back to the retention decision."""

    return f"{_RETENTION_DECISION_PREFIX}{assertion_id}"


def is_retained_assertion_record(record: DerivedRecord) -> bool:
    return record.payload.get("record_kind") == RETAINED_ASSERTION_RECORD_KIND


def assert_retention_write_allowed(
    assertion: GroundedAssertion,
    decision: RetentionDecision,
) -> None:
    """Enforce C29 invariants before any vault write."""

    if decision.assertion_id != assertion.id:
        msg = (
            f"RetentionDecision assertion_id {decision.assertion_id!r} "
            f"does not match assertion {assertion.id!r}"
        )
        raise RetentionVaultError(msg)

    if decision.outcome not in (RetentionOutcome.DURABLE, RetentionOutcome.TTL):
        raise RetentionVaultError(
            f"Vault write rejected for outcome {decision.outcome.value}"
        )

    if assertion.epistemic_status in _INFERENCE_NOT_DURABLE_STATUSES:
        raise RetentionVaultError(
            "Vault write rejected: epistemic status "
            f"{assertion.epistemic_status.value} cannot become durable"
        )

    if decision.rejection_reason is not None:
        raise RetentionVaultError(
            "Vault write rejected: decision carries rejection reason "
            f"{decision.rejection_reason.value}"
        )


def build_retained_assertion_payload(
    assertion: GroundedAssertion,
    decision: RetentionDecision,
) -> dict[str, object]:
    """Serialize assertion + decision metadata. Epistemic status is never upgraded."""

    return {
        "record_kind": RETAINED_ASSERTION_RECORD_KIND,
        "assertion_id": assertion.id,
        "kind": assertion.kind.value,
        "subject": assertion.subject,
        "predicate": assertion.predicate,
        "value": GroundedAssertion._normalize_value(assertion.value),
        "scope": assertion.scope,
        "epistemic_status": assertion.epistemic_status.value,
        "confidence": assertion.confidence,
        "evidence_refs": list(assertion.evidence_refs),
        "derived_from_assertion_ids": list(assertion.derived_from),
        "supersedes": list(assertion.supersedes),
        "purpose_tags": list(assertion.purpose_tags),
        "validity_kind": assertion.validity_kind.value,
        "temporal_scope": assertion.temporal_scope,
        "valid_from": assertion.valid_from.isoformat() if assertion.valid_from else None,
        "valid_until": assertion.valid_until.isoformat() if assertion.valid_until else None,
        "retention_decision_id": retention_decision_lineage_ref(assertion.id),
        "retention_decision": {
            "outcome": decision.outcome.value,
            "purpose": decision.purpose.value if decision.purpose is not None else None,
            "retention_class": decision.retention_class.value,
            "lifetime": decision.lifetime,
            "provenance_refs": list(decision.provenance_refs),
            "rejection_reason": (
                decision.rejection_reason.value if decision.rejection_reason else None
            ),
            "rationale": decision.rationale,
        },
    }


def _assertion_kind_to_record_type(kind: AssertionKind) -> DerivedRecordType:
    if kind in (AssertionKind.PREFERENCE, AssertionKind.FACT, AssertionKind.DELEGATION):
        return DerivedRecordType.FACT
    return DerivedRecordType.AGGREGATE


def _lineage_refs(assertion: GroundedAssertion, decision: RetentionDecision) -> list[str]:
    refs: list[str] = [
        assertion_lineage_ref(assertion.id),
        retention_decision_lineage_ref(assertion.id),
    ]
    for ref in assertion.evidence_refs:
        if ref not in refs:
            refs.append(ref)
    for parent_id in assertion.derived_from:
        parent_ref = assertion_lineage_ref(parent_id)
        if parent_ref not in refs:
            refs.append(parent_ref)
        if parent_id not in refs:
            refs.append(parent_id)
    for ref in decision.provenance_refs:
        if ref not in refs:
            refs.append(ref)
    return refs


def map_retention_to_derived_record(
    assertion: GroundedAssertion,
    decision: RetentionDecision,
) -> DerivedRecord:
    """Map a gated retention decision to a SEC-06 DerivedRecord row."""

    assert_retention_write_allowed(assertion, decision)
    payload = build_retained_assertion_payload(assertion, decision)

    stored_status = payload.get("epistemic_status")
    if stored_status != assertion.epistemic_status.value:
        raise RetentionVaultError("Epistemic status upgrade blocked at vault boundary")

    purpose = decision.purpose or RetentionPurpose.LIFE_FACT
    return DerivedRecord(
        id=assertion.id,
        record_type=_assertion_kind_to_record_type(assertion.kind),
        memory_layer=MemoryLayer.ACTIVE,
        payload=payload,
        lineage=LineageMetadata(
            derived_from=_lineage_refs(assertion, decision),
            purpose=purpose,
            retention_class=decision.retention_class,
            expires_after_resolution=decision.lifetime,
        ),
        confidence=assertion.confidence if assertion.confidence is not None else 1.0,
        created_at=datetime.now(tz=UTC),
    )


def list_retained_assertion_ids(conn: SqlCipherConnection) -> list[str]:
    """Return assertion ids for retained-assertion rows in the vault."""

    ids: list[str] = []
    for record in list_all_derived_records(conn):
        if not is_retained_assertion_record(record):
            continue
        assertion_id = record.payload.get("assertion_id")
        if isinstance(assertion_id, str) and assertion_id:
            ids.append(assertion_id)
    return sorted(ids)


class VaultDurableAssertionStore:
    """Vault-backed durable assertion store — only gated outcomes may persist."""

    def __init__(self, vault: PrivateVault) -> None:
        self._vault = vault

    def store(self, assertion: GroundedAssertion, decision: RetentionDecision) -> str:
        existing = self.get_record(assertion.id)
        if existing is not None:
            raise RetentionVaultError(
                f"In-place rewrite of retained assertion {assertion.id!r} is forbidden; "
                "mint a new assertion id and supersede instead"
            )
        record = map_retention_to_derived_record(assertion, decision)
        self._vault.store_derived(record)
        return record.id

    def evaluate_and_store(
        self,
        assertion: GroundedAssertion,
        *,
        now: datetime | None = None,
    ) -> str | None:
        decision = evaluate_retention(assertion, now=now)
        if decision.outcome not in (RetentionOutcome.DURABLE, RetentionOutcome.TTL):
            return None
        return self.store(assertion, decision)

    def list_retained_ids(self) -> list[str]:
        return list_retained_assertion_ids(self._vault._conn)

    def get_record(self, assertion_id: str) -> DerivedRecord | None:
        record = self._vault.get_derived_record(assertion_id)
        if record is None or not is_retained_assertion_record(record):
            return None
        return record

