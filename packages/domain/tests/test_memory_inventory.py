"""C29 slice 4 — MemoryInventory projection unit tests."""

from __future__ import annotations

from datetime import UTC, datetime, timedelta

from personal_enigma.domain.grounding import EpistemicStatus
from personal_enigma.domain.memory_inventory import (
    FORGET_RETAINED_ASSERTION_ACTION,
    RETAINED_ASSERTION_RECORD_KIND,
    MemoryInventoryStatus,
    MemoryReviewStatus,
    format_memory_claim,
    inventory_contains_profiling_claim,
    inventory_status_for,
    project_memory_inventory,
)
from personal_enigma.domain.retention import (
    DerivedRecord,
    DerivedRecordType,
    LineageMetadata,
    MemoryLayer,
    RetentionClass,
    RetentionPurpose,
)

_NOW = datetime(2026, 8, 18, tzinfo=UTC)


def _record(
    *,
    assertion_id: str,
    subject: str = "PERSON_Maya",
    predicate: str = "likes",
    value: object = "ceramics",
    epistemic_status: str = "user_confirmed",
    purpose: str = "user_explicit_recall",
    outcome: str = "durable",
    evidence_refs: list[str] | None = None,
    derived_from_assertion_ids: list[str] | None = None,
    supersedes: list[str] | None = None,
    valid_until: str | None = None,
    rationale: str = "Durable third-party concrete fact with purpose user_explicit_recall.",
    created_at: datetime | None = None,
    extra_payload: dict[str, object] | None = None,
) -> DerivedRecord:
    payload: dict[str, object] = {
        "record_kind": RETAINED_ASSERTION_RECORD_KIND,
        "assertion_id": assertion_id,
        "kind": "preference",
        "subject": subject,
        "predicate": predicate,
        "value": value,
        "epistemic_status": epistemic_status,
        "evidence_refs": list(evidence_refs or ["EV_CHAT_1"]),
        "derived_from_assertion_ids": list(derived_from_assertion_ids or []),
        "supersedes": list(supersedes or []),
        "valid_until": valid_until,
        "retention_decision": {
            "outcome": outcome,
            "purpose": purpose,
            "retention_class": (
                "active_until_resolved" if outcome == "ttl" else "durable_shadow"
            ),
            "rationale": rationale,
            "provenance_refs": list(evidence_refs or ["EV_CHAT_1"]),
        },
    }
    if extra_payload:
        payload.update(extra_payload)
    return DerivedRecord(
        id=assertion_id,
        record_type=DerivedRecordType.FACT,
        memory_layer=MemoryLayer.ACTIVE,
        payload=payload,
        lineage=LineageMetadata(
            derived_from=[f"assertion:{assertion_id}", *(derived_from_assertion_ids or [])],
            purpose=RetentionPurpose(purpose),
            retention_class=(
                RetentionClass.ACTIVE_UNTIL_RESOLVED
                if outcome == "ttl"
                else RetentionClass.DURABLE_SHADOW
            ),
        ),
        created_at=created_at or _NOW,
    )


def test_model_inferred_never_collapses_to_known() -> None:
    assert (
        inventory_status_for(EpistemicStatus.MODEL_INFERRED)
        == MemoryInventoryStatus.POSSIBLE
    )
    assert (
        inventory_status_for(EpistemicStatus.MODEL_INFERRED, ttl=True)
        == MemoryInventoryStatus.POSSIBLE
    )
    assert (
        inventory_status_for(EpistemicStatus.USER_CONFIRMED)
        == MemoryInventoryStatus.KNOWN
    )
    assert (
        inventory_status_for(EpistemicStatus.USER_CONFIRMED, ttl=True)
        == MemoryInventoryStatus.EXPIRING
    )


def test_inferred_row_projects_as_possible_not_known() -> None:
    inventory = project_memory_inventory(
        [
            _record(
                assertion_id="inferred-ceramics",
                epistemic_status="model_inferred",
                value="may like ceramics",
            )
        ],
        now=_NOW,
    )
    entry = inventory.get("inferred-ceramics")
    assert entry is not None
    assert entry.epistemic_status == EpistemicStatus.MODEL_INFERRED
    assert entry.inventory_status == MemoryInventoryStatus.POSSIBLE
    assert entry.inventory_status != MemoryInventoryStatus.KNOWN


def test_why_fields_are_inspectable() -> None:
    retained_at = datetime(2026, 1, 19, 10, 0, tzinfo=UTC)
    inventory = project_memory_inventory(
        [
            _record(
                assertion_id="maya-ceramics",
                derived_from_assertion_ids=["maya-studio-visit"],
                created_at=retained_at,
            )
        ],
        now=_NOW,
    )
    why = inventory.why("maya-ceramics")
    assert why is not None
    assert why.purpose == RetentionPurpose.USER_EXPLICIT_RECALL
    assert "EV_CHAT_1" in why.provenance_refs
    assert "maya-studio-visit" in why.derived_from
    assert why.retained_at == retained_at
    assert why.rationale
    assert "shrug" not in why.rationale.lower()


def test_about_subject_and_claim_shape() -> None:
    inventory = project_memory_inventory(
        [
            _record(assertion_id="maya-ceramics"),
            _record(
                assertion_id="self-prefers",
                subject="self",
                predicate="prefers",
                value="quiet mornings",
            ),
        ],
        now=_NOW,
    )
    maya = inventory.about("Maya")
    assert [entry.assertion_id for entry in maya] == ["maya-ceramics"]
    assert maya[0].claim == "Maya likes ceramics"
    assert format_memory_claim("PERSON_Maya", "likes", "ceramics") == "Maya likes ceramics"


def test_superseded_row_absent_from_current_inventory() -> None:
    inventory = project_memory_inventory(
        [
            _record(assertion_id="maya-ceramics-v1", value="ceramics"),
            _record(
                assertion_id="maya-ceramics-v2",
                value="pottery",
                supersedes=["maya-ceramics-v1"],
                derived_from_assertion_ids=["maya-ceramics-v1"],
            ),
        ],
        now=_NOW,
    )
    assert inventory.get("maya-ceramics-v1") is None
    current = inventory.get("maya-ceramics-v2")
    assert current is not None
    assert current.value == "pottery"
    assert "maya-ceramics-v1" in current.supersedes
    assert "maya-ceramics-v1" in current.derived_from


def test_missing_record_kind_is_ignored() -> None:
    record = _record(assertion_id="maya-ceramics")
    record.payload.pop("record_kind", None)
    inventory = project_memory_inventory([record], now=_NOW)
    assert inventory.entries == []


def test_expired_ttl_absent_even_if_row_still_present() -> None:
    past = _NOW - timedelta(days=1)
    inventory = project_memory_inventory(
        [
            _record(
                assertion_id="dinner-plan",
                predicate="plans_to",
                value="Bistro Saturday",
                purpose="temporary_case",
                outcome="ttl",
                valid_until=past.isoformat(),
            )
        ],
        now=_NOW,
    )
    assert inventory.entries == []


def test_ttl_at_exact_valid_until_is_still_current() -> None:
    now = _NOW
    inventory = project_memory_inventory(
        [
            _record(
                assertion_id="gift-plan",
                predicate="gift_history",
                value="mug 2024",
                purpose="temporary_case",
                outcome="ttl",
                valid_until=now.isoformat(),
            )
        ],
        now=now,
    )
    assert inventory.get("gift-plan") is not None

    later = now + timedelta(microseconds=1)
    inventory_later = project_memory_inventory(
        [
            _record(
                assertion_id="gift-plan",
                predicate="gift_history",
                value="mug 2024",
                purpose="temporary_case",
                outcome="ttl",
                valid_until=now.isoformat(),
            )
        ],
        now=later,
    )
    assert inventory_later.entries == []


def test_ttl_current_displays_as_expiring() -> None:
    future = _NOW + timedelta(days=30)
    inventory = project_memory_inventory(
        [
            _record(
                assertion_id="gift-plan",
                predicate="gift_history",
                value="mug 2024",
                purpose="temporary_case",
                outcome="ttl",
                valid_until=future.isoformat(),
            )
        ],
        now=_NOW,
    )
    entry = inventory.get("gift-plan")
    assert entry is not None
    assert entry.inventory_status == MemoryInventoryStatus.EXPIRING
    assert entry.review_status == MemoryReviewStatus.REVIEW_DUE
    assert entry.forget.action == FORGET_RETAINED_ASSERTION_ACTION
    assert entry.forget.available is True


def test_conflicted_claims_do_not_collapse() -> None:
    inventory = project_memory_inventory(
        [
            _record(assertion_id="likes-ceramics", value="ceramics"),
            _record(assertion_id="likes-painting", value="painting"),
        ],
        now=_NOW,
    )
    statuses = {entry.assertion_id: entry.inventory_status for entry in inventory.entries}
    assert statuses["likes-ceramics"] == MemoryInventoryStatus.CONFLICTED
    assert statuses["likes-painting"] == MemoryInventoryStatus.CONFLICTED


def test_profiling_payload_is_detectable_and_practical_facts_are_not() -> None:
    practical = project_memory_inventory(
        [_record(assertion_id="maya-ceramics")],
        now=_NOW,
    )
    dossier = project_memory_inventory(
        [
            _record(
                assertion_id="maya-profile",
                predicate="personality_type",
                value="anxious achiever",
            )
        ],
        now=_NOW,
    )
    assert inventory_contains_profiling_claim(practical) is False
    assert inventory_contains_profiling_claim(dossier) is True


def test_raw_source_body_in_payload_is_not_copied_into_inventory() -> None:
    body = "Maya spent the weekend throwing bowls at the studio on Maple Street."
    inventory = project_memory_inventory(
        [
            _record(
                assertion_id="maya-ceramics",
                extra_payload={"raw_email_body": body, "chat_transcript": body},
            )
        ],
        now=_NOW,
    )
    dumped = inventory.model_dump_json()
    assert body not in dumped
    assert "EV_CHAT_1" in dumped
    assert "Maya likes ceramics" in dumped
