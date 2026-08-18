"""C29 slice 3 — forget propagation and TTL expiry freeze tests."""

from __future__ import annotations

from datetime import UTC, datetime, timedelta
from pathlib import Path

import pytest

from personal_enigma.api.storage.retention_forget import (
    find_current_retained_by_content,
    forget_retained_assertion_with_propagation,
    resolve_retained_assertion_forget_plan,
    retained_assertion_is_current,
)
from personal_enigma.api.storage.retention_vault import (
    VaultDurableAssertionStore,
    assertion_lineage_ref,
)
from personal_enigma.api.storage.vault import PrivateVault
from personal_enigma.domain.grounding import (
    AssertionKind,
    AssertionValidityKind,
    EpistemicStatus,
    GroundedAssertion,
)
from personal_enigma.domain.retention import DerivedRecordType, RetentionPurpose
from personal_enigma.domain.retention_gate import RetentionOutcome, evaluate_retention


def _assertion(**overrides: object) -> GroundedAssertion:
    base: dict[str, object] = {
        "id": "A-ceramics",
        "kind": AssertionKind.PREFERENCE,
        "subject": "PERSON_Maya",
        "predicate": "likes",
        "value": "ceramics",
        "epistemic_status": EpistemicStatus.USER_CONFIRMED,
        "purpose_tags": ["user_explicit_recall"],
        "evidence_refs": ["EV_CHAT_1"],
    }
    base.update(overrides)
    return GroundedAssertion.model_validate(base)


@pytest.fixture
def memory_keychain(monkeypatch: pytest.MonkeyPatch):
    from personal_enigma.api.storage.keychain import MemoryKeychain

    monkeypatch.setenv("ENIGMA_KEYCHAIN_BACKEND", "memory")
    chain = MemoryKeychain()
    yield chain
    chain.clear()


@pytest.fixture
def vault_root(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> Path:
    root = tmp_path / "private"
    monkeypatch.setenv("ENIGMA_PRIVATE_STORAGE_ROOT", str(root))
    return root


class TestMayaCeramicsCascade:
    """Nastiest cascade: forget ceramics preference, keep independent birthday."""

    def test_forget_ceramics_invalidates_derived_keeps_independent(
        self, vault_root: Path, memory_keychain
    ) -> None:
        ceramics = _assertion(id="maya-ceramics")
        ceramics_decision = evaluate_retention(ceramics)

        birthday = _assertion(
            id="maya-birthday",
            kind=AssertionKind.FACT,
            predicate="birthday",
            value="14 March",
            evidence_refs=["EV_CALENDAR_1"],
            purpose_tags=["user_explicit_recall"],
        )
        birthday_decision = evaluate_retention(birthday)

        with PrivateVault.open(root=vault_root, keychain=memory_keychain) as vault:
            store = VaultDurableAssertionStore(vault)
            store.store(ceramics, ceramics_decision)
            store.store(birthday, birthday_decision)

            # B: recommendation justified only by ceramics (non-retained derived row).
            vault.store_derived_new(
                record_id="rec-ceramics-gift",
                record_type=DerivedRecordType.FEATURE,
                payload={
                    "recommendation": "gift_ceramics_for_maya",
                    "basis": "maya_likes_ceramics",
                },
                derived_from=[assertion_lineage_ref("maya-ceramics")],
                purpose=RetentionPurpose.TEMPORARY_CASE,
            )

            assert store.list_retained_ids() == ["maya-birthday", "maya-ceramics"]
            assert vault.get_derived_record("rec-ceramics-gift") is not None

            result = store.forget("maya-ceramics")

            assert "maya-ceramics" in result.deleted_assertion_ids
            assert "rec-ceramics-gift" in result.deleted_derived_ids
            assert "maya-birthday" not in result.deleted_assertion_ids
            assert store.list_retained_ids() == ["maya-birthday"]
            assert vault.get_derived_record("maya-ceramics") is None
            assert vault.get_derived_record("rec-ceramics-gift") is None
            assert vault.get_derived_record("maya-birthday") is not None
            assert vault.count_orphaned_derivatives() == 0

            ceramics_hits = find_current_retained_by_content(
                vault._conn,
                subject="PERSON_Maya",
                predicate="likes",
                value="ceramics",
            )
            assert ceramics_hits == []
            assert not retained_assertion_is_current(vault._conn, "maya-ceramics")

            audit = vault.list_forget_audit(limit=1)
            assert len(audit) == 1
            haystack = str(audit[0])
            assert "gift_ceramics_for_maya" not in haystack
            assert "maya_likes_ceramics" not in haystack

    def test_independent_evidence_survives_partial_forget_plan(
        self, vault_root: Path, memory_keychain
    ) -> None:
        """Shared fact with two evidence refs survives when one parent is forgotten."""
        with PrivateVault.open(root=vault_root, keychain=memory_keychain) as vault:
            vault.store_raw_source(
                source="gmail",
                external_id="msg-b",
                raw_content=b"also mentions ceramics",
                record_id="EMAIL_B",
            )
            ceramics = _assertion(id="maya-ceramics")
            store = VaultDurableAssertionStore(vault)
            store.store(ceramics, evaluate_retention(ceramics))

            vault.store_derived_new(
                record_id="shared-fact",
                record_type=DerivedRecordType.FACT,
                payload={"label": "maya_ceramics_interest"},
                derived_from=[
                    assertion_lineage_ref("maya-ceramics"),
                    "EMAIL_B",
                ],
                purpose=RetentionPurpose.LIFE_FACT,
            )

            to_delete, to_survive = resolve_retained_assertion_forget_plan(
                vault._conn, "maya-ceramics"
            )
            assert "shared-fact" in to_survive
            assert "shared-fact" not in to_delete


class TestTtlExpiry:
    """TTL expiry uses the same governed-forgetting cascade as explicit forget."""

    def test_expired_ttl_assertion_and_exclusive_derivative_removed(
        self, vault_root: Path, memory_keychain
    ) -> None:
        past = datetime(2026, 1, 1, tzinfo=UTC)
        expired_at = past - timedelta(days=1)
        now = past + timedelta(days=1)

        availability = _assertion(
            id="restaurant-avail",
            kind=AssertionKind.FACT,
            subject="self",
            predicate="plans_to",
            value="dine at Bistro Saturday 7pm",
            purpose_tags=["temporary_case"],
            validity_kind=AssertionValidityKind.TTL,
            temporal_scope="dinner_planning",
            valid_until=expired_at,
            evidence_refs=["EV_BOOKING_1"],
        )
        availability_decision = evaluate_retention(availability)
        assert availability_decision.outcome == RetentionOutcome.TTL

        with PrivateVault.open(root=vault_root, keychain=memory_keychain) as vault:
            store = VaultDurableAssertionStore(vault)
            store.store(availability, availability_decision)

            vault.store_derived_new(
                record_id="dinner-rec",
                record_type=DerivedRecordType.FEATURE,
                payload={"recommendation": "book_bistro_saturday"},
                derived_from=[assertion_lineage_ref("restaurant-avail")],
                purpose=RetentionPurpose.TEMPORARY_CASE,
            )

            results = store.expire_ttl(now=now)

            assert len(results) == 1
            assert results[0].trigger == "ttl_expiry"
            assert "restaurant-avail" in results[0].deleted_assertion_ids
            assert "dinner-rec" in results[0].deleted_derived_ids
            assert store.list_retained_ids() == []
            assert vault.get_derived_record("restaurant-avail") is None
            assert vault.get_derived_record("dinner-rec") is None
            assert not retained_assertion_is_current(vault._conn, "restaurant-avail")

    def test_unexpired_ttl_not_swept(self, vault_root: Path, memory_keychain) -> None:
        future = datetime(2026, 12, 1, tzinfo=UTC)
        availability = _assertion(
            id="restaurant-future",
            kind=AssertionKind.FACT,
            subject="self",
            predicate="plans_to",
            value="dine at Bistro in December",
            purpose_tags=["temporary_case"],
            validity_kind=AssertionValidityKind.TTL,
            valid_until=future,
        )
        with PrivateVault.open(root=vault_root, keychain=memory_keychain) as vault:
            store = VaultDurableAssertionStore(vault)
            store.store(availability, evaluate_retention(availability))
            results = store.expire_ttl(now=datetime(2026, 6, 1, tzinfo=UTC))
            assert results == []
            assert store.list_retained_ids() == ["restaurant-future"]


class TestReestablishment:
    """Deletion history does not permanently blacklist a proposition."""

    def test_independent_reestablishment_after_forget(
        self, vault_root: Path, memory_keychain
    ) -> None:
        original = _assertion(id="maya-ceramics-v1", evidence_refs=["EV_CHAT_1"])
        with PrivateVault.open(root=vault_root, keychain=memory_keychain) as vault:
            store = VaultDurableAssertionStore(vault)
            store.store(original, evaluate_retention(original))
            first_audit_count = len(vault.list_forget_audit())

            forget_result = store.forget("maya-ceramics-v1")
            assert "maya-ceramics-v1" in forget_result.deleted_assertion_ids
            assert store.list_retained_ids() == []

            reestablished = _assertion(
                id="maya-ceramics-v2",
                evidence_refs=["EV_CHAT_99"],
                epistemic_status=EpistemicStatus.SOURCE_OBSERVED,
            )
            re_decision = evaluate_retention(reestablished)
            assert re_decision.outcome == RetentionOutcome.DURABLE
            stored_id = store.store(reestablished, re_decision)

            assert stored_id == "maya-ceramics-v2"
            assert store.list_retained_ids() == ["maya-ceramics-v2"]
            record = store.get_record("maya-ceramics-v2")
            assert record is not None
            assert record.payload["epistemic_status"] == EpistemicStatus.SOURCE_OBSERVED.value
            assert "EV_CHAT_99" in record.lineage.derived_from
            assert assertion_lineage_ref("maya-ceramics-v1") not in record.lineage.derived_from

            hits = find_current_retained_by_content(
                vault._conn,
                subject="PERSON_Maya",
                predicate="likes",
                value="ceramics",
            )
            assert len(hits) == 1
            assert hits[0].id == "maya-ceramics-v2"

            assert len(vault.list_forget_audit()) == first_audit_count + 1

    def test_forget_does_not_mutate_epistemic_class(
        self, vault_root: Path, memory_keychain
    ) -> None:
        """Unavailable after forget ≠ false — re-established row keeps its status."""
        with PrivateVault.open(root=vault_root, keychain=memory_keychain) as vault:
            store = VaultDurableAssertionStore(vault)
            assertion = _assertion(
                id="maya-ceramics-v1",
                epistemic_status=EpistemicStatus.USER_CONFIRMED,
            )
            store.store(assertion, evaluate_retention(assertion))
            store.forget("maya-ceramics-v1")

            assert store.get_record("maya-ceramics-v1") is None

            reestablished = _assertion(
                id="maya-ceramics-v2",
                epistemic_status=EpistemicStatus.USER_REPORTED,
                evidence_refs=["EV_NEW"],
            )
            store.store(reestablished, evaluate_retention(reestablished))
            record = store.get_record("maya-ceramics-v2")
            assert record is not None
            assert record.payload["epistemic_status"] == EpistemicStatus.USER_REPORTED.value
