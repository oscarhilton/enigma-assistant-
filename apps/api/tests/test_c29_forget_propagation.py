"""C29 slice 3 — forget propagation and TTL expiry freeze tests."""

from __future__ import annotations

from datetime import UTC, datetime, timedelta
from pathlib import Path

import pytest

from personal_enigma.api.storage.retention_forget import (
    current_memory_record_ids_mentioning,
    expire_retained_assertions,
    find_current_retained_by_content,
    list_current_memory_records,
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


def _assert_no_ceramics_in_current_memory(vault: PrivateVault) -> None:
    hits = current_memory_record_ids_mentioning(vault._conn, "ceramics")
    assert hits == [], f"current memory still exposes ceramics via {hits}"


def _assert_no_negation_of_ceramics(vault: PrivateVault) -> None:
    """Forget removes recoverability; it must not assert the proposition is false."""
    for record in list_current_memory_records(vault._conn):
        payload = record.payload
        blob = str(payload).lower()
        assert "does_not_like" not in blob
        assert "not ceramics" not in blob
        if payload.get("predicate") == "likes" and payload.get("subject") == "PERSON_Maya":
            assert payload.get("value") != "ceramics"
            assert payload.get("value") not in (False, "false", "no")
        assert payload.get("epistemic_status") not in (
            EpistemicStatus.CONFLICTED.value,
            EpistemicStatus.STALE.value,
        )


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
        ceramics = _assertion(id="maya-pref")
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

            # B: recommendation justified only by ceramics (dangling EV_* must not save it).
            vault.store_derived_new(
                record_id="rec-gift",
                record_type=DerivedRecordType.FEATURE,
                payload={
                    "recommendation": "gift_ceramics_for_maya",
                    "basis": "maya_likes_ceramics",
                },
                derived_from=[
                    assertion_lineage_ref("maya-pref"),
                    "EV_CHAT_1",
                ],
                purpose=RetentionPurpose.TEMPORARY_CASE,
            )
            # Transitive grandchild justified only by B.
            vault.store_derived_new(
                record_id="rec-gift-embed",
                record_type=DerivedRecordType.EMBEDDING,
                payload={"hint": "ceramics_gift_vector"},
                derived_from=["rec-gift"],
                purpose=RetentionPurpose.RETRIEVAL_INDEX,
            )

            assert store.list_retained_ids() == ["maya-birthday", "maya-pref"]
            assert vault.get_derived_record("rec-gift") is not None
            assert vault.get_derived_record("rec-gift-embed") is not None

            result = store.forget("maya-pref")

            assert "maya-pref" in result.deleted_assertion_ids
            assert "rec-gift" in result.deleted_derived_ids
            assert "rec-gift-embed" in result.deleted_derived_ids
            assert "maya-birthday" not in result.deleted_assertion_ids
            assert store.list_retained_ids() == ["maya-birthday"]
            assert vault.get_derived_record("maya-pref") is None
            assert vault.get_derived_record("rec-gift") is None
            assert vault.get_derived_record("rec-gift-embed") is None
            assert vault.get_derived_record("maya-birthday") is not None
            assert vault.count_orphaned_derivatives() == 0

            ceramics_hits = find_current_retained_by_content(
                vault._conn,
                subject="PERSON_Maya",
                predicate="likes",
                value="ceramics",
            )
            assert ceramics_hits == []
            assert not retained_assertion_is_current(vault._conn, "maya-pref")
            _assert_no_ceramics_in_current_memory(vault)
            _assert_no_negation_of_ceramics(vault)

            current_ids = {record.id for record in store.list_current_memory()}
            assert current_ids == {"maya-birthday"}

            audit = vault.list_forget_audit(limit=1)
            assert len(audit) == 1
            haystack = str(audit[0])
            assert "gift_ceramics_for_maya" not in haystack
            assert "maya_likes_ceramics" not in haystack

    def test_independent_evidence_survives_executed_forget(
        self, vault_root: Path, memory_keychain
    ) -> None:
        """Shared fact with a live source survives; forgotten parent is stripped from lineage."""
        with PrivateVault.open(root=vault_root, keychain=memory_keychain) as vault:
            vault.store_raw_source(
                source="gmail",
                external_id="msg-b",
                raw_content=b"also mentions ceramics",
                record_id="EMAIL_B",
            )
            ceramics = _assertion(id="maya-pref")
            store = VaultDurableAssertionStore(vault)
            store.store(ceramics, evaluate_retention(ceramics))

            vault.store_derived_new(
                record_id="shared-fact",
                record_type=DerivedRecordType.FACT,
                payload={"label": "maya_ceramics_interest"},
                derived_from=[
                    assertion_lineage_ref("maya-pref"),
                    "EMAIL_B",
                ],
                purpose=RetentionPurpose.LIFE_FACT,
            )

            to_delete, to_survive = resolve_retained_assertion_forget_plan(
                vault._conn, "maya-pref"
            )
            assert "shared-fact" in to_survive
            assert "shared-fact" not in to_delete

            result = store.forget("maya-pref")
            assert "maya-pref" in result.deleted_assertion_ids
            assert "shared-fact" not in result.deleted_derived_ids
            shared = vault.get_derived_record("shared-fact")
            assert shared is not None
            assert "EMAIL_B" in shared.lineage.derived_from
            assert assertion_lineage_ref("maya-pref") not in shared.lineage.derived_from
            assert vault.get_derived_record("maya-pref") is None

    def test_assertion_forget_does_not_invalidate_same_id_source_record(
        self, vault_root: Path, memory_keychain
    ) -> None:
        """Assertion ids and SourceRecord ids must not collide in forget graphs."""
        shared_id = "EMAIL_MAYA"
        with PrivateVault.open(root=vault_root, keychain=memory_keychain) as vault:
            vault.store_raw_source(
                source="gmail",
                external_id="msg-maya",
                raw_content=b"Maya likes ceramics",
                record_id=shared_id,
            )
            assertion = _assertion(id=shared_id, evidence_refs=[shared_id])
            store = VaultDurableAssertionStore(vault)
            store.store(assertion, evaluate_retention(assertion))

            vault.store_derived_new(
                record_id="shared-fact",
                record_type=DerivedRecordType.FACT,
                payload={"label": "maya_ceramics_interest"},
                derived_from=[assertion_lineage_ref(shared_id), shared_id],
                purpose=RetentionPurpose.LIFE_FACT,
            )

            to_delete, to_survive = resolve_retained_assertion_forget_plan(
                vault._conn, shared_id
            )
            assert "shared-fact" in to_survive
            assert "shared-fact" not in to_delete

            result = store.forget(shared_id)
            assert shared_id in result.deleted_assertion_ids
            assert "shared-fact" not in result.deleted_derived_ids
            assert vault.get_source_record(shared_id) is not None
            shared = vault.get_derived_record("shared-fact")
            assert shared is not None
            assert shared_id in shared.lineage.derived_from
            assert assertion_lineage_ref(shared_id) not in shared.lineage.derived_from

    def test_child_retained_assertion_falls_with_only_parent(
        self, vault_root: Path, memory_keychain
    ) -> None:
        """Self lineage refs on a child assertion are identity, not independent evidence."""
        parent = _assertion(id="maya-pref")
        child = _assertion(
            id="maya-gift-plan",
            kind=AssertionKind.FACT,
            predicate="gift_history",
            value="ceramics mug plan",
            derived_from=["maya-pref"],
            purpose_tags=["temporary_case"],
            validity_kind=AssertionValidityKind.TTL,
            temporal_scope="gift_planning_2026",
            valid_until=datetime(2026, 12, 1, tzinfo=UTC),
        )
        with PrivateVault.open(root=vault_root, keychain=memory_keychain) as vault:
            store = VaultDurableAssertionStore(vault)
            store.store(parent, evaluate_retention(parent))
            child_decision = evaluate_retention(child)
            assert child_decision.outcome in (RetentionOutcome.DURABLE, RetentionOutcome.TTL)
            store.store(child, child_decision)

            result = store.forget("maya-pref")
            assert "maya-pref" in result.deleted_assertion_ids
            assert "maya-gift-plan" in result.deleted_assertion_ids
            assert store.list_retained_ids() == []
            assert vault.get_derived_record("maya-gift-plan") is None
            _assert_no_ceramics_in_current_memory(vault)


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

    def test_ttl_expiry_matches_forget_cascade_with_independent_survivor(
        self, vault_root: Path, memory_keychain
    ) -> None:
        """Expire is forget(trigger=ttl_expiry), not a row-cleanup shortcut."""
        expired_at = datetime(2026, 1, 1, tzinfo=UTC)
        now = datetime(2026, 1, 3, tzinfo=UTC)

        ceramics = _assertion(
            id="maya-pref-ttl",
            purpose_tags=["temporary_case"],
            validity_kind=AssertionValidityKind.TTL,
            temporal_scope="gift_planning",
            valid_until=expired_at,
        )
        birthday = _assertion(
            id="maya-birthday-ttl",
            kind=AssertionKind.FACT,
            predicate="birthday",
            value="14 March",
            evidence_refs=["EV_CALENDAR_1"],
            purpose_tags=["user_explicit_recall"],
        )
        with PrivateVault.open(root=vault_root, keychain=memory_keychain) as vault:
            store = VaultDurableAssertionStore(vault)
            ceramics_decision = evaluate_retention(ceramics)
            assert ceramics_decision.outcome == RetentionOutcome.TTL
            store.store(ceramics, ceramics_decision)
            store.store(birthday, evaluate_retention(birthday))
            vault.store_derived_new(
                record_id="rec-gift-ttl",
                record_type=DerivedRecordType.FEATURE,
                payload={"recommendation": "gift_ceramics_for_maya"},
                derived_from=[assertion_lineage_ref("maya-pref-ttl"), "EV_CHAT_1"],
                purpose=RetentionPurpose.TEMPORARY_CASE,
            )

            planned_delete, planned_survive = resolve_retained_assertion_forget_plan(
                vault._conn, "maya-pref-ttl"
            )
            assert "rec-gift-ttl" in planned_delete
            assert "maya-birthday-ttl" not in planned_delete

            results = expire_retained_assertions(vault._conn, now=now)
            assert len(results) == 1
            assert results[0].trigger == "ttl_expiry"
            assert set(results[0].deleted_assertion_ids) == {"maya-pref-ttl"}
            assert "rec-gift-ttl" in results[0].deleted_derived_ids
            assert store.list_retained_ids() == ["maya-birthday-ttl"]
            assert vault.get_derived_record("rec-gift-ttl") is None
            _assert_no_ceramics_in_current_memory(vault)
            _assert_no_negation_of_ceramics(vault)
            assert planned_survive.isdisjoint(set(results[0].deleted_derived_ids))

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
        original = _assertion(id="maya-pref-v1", evidence_refs=["EV_CHAT_1"])
        with PrivateVault.open(root=vault_root, keychain=memory_keychain) as vault:
            store = VaultDurableAssertionStore(vault)
            store.store(original, evaluate_retention(original))
            first_audit_count = len(vault.list_forget_audit())

            forget_result = store.forget("maya-pref-v1")
            assert "maya-pref-v1" in forget_result.deleted_assertion_ids
            assert store.list_retained_ids() == []
            _assert_no_ceramics_in_current_memory(vault)
            _assert_no_negation_of_ceramics(vault)

            reestablished = _assertion(
                id="maya-pref-v2",
                evidence_refs=["EV_CHAT_99"],
                epistemic_status=EpistemicStatus.SOURCE_OBSERVED,
            )
            re_decision = evaluate_retention(reestablished)
            assert re_decision.outcome == RetentionOutcome.DURABLE
            stored_id = store.store(reestablished, re_decision)

            assert stored_id == "maya-pref-v2"
            assert store.list_retained_ids() == ["maya-pref-v2"]
            record = store.get_record("maya-pref-v2")
            assert record is not None
            assert record.payload["epistemic_status"] == EpistemicStatus.SOURCE_OBSERVED.value
            assert "EV_CHAT_99" in record.lineage.derived_from
            assert assertion_lineage_ref("maya-pref-v1") not in record.lineage.derived_from

            hits = find_current_retained_by_content(
                vault._conn,
                subject="PERSON_Maya",
                predicate="likes",
                value="ceramics",
            )
            assert len(hits) == 1
            assert hits[0].id == "maya-pref-v2"

            assert len(vault.list_forget_audit()) == first_audit_count + 1

    def test_forget_does_not_mutate_epistemic_class(
        self, vault_root: Path, memory_keychain
    ) -> None:
        """Unavailable after forget ≠ false — re-established row keeps its status."""
        with PrivateVault.open(root=vault_root, keychain=memory_keychain) as vault:
            store = VaultDurableAssertionStore(vault)
            assertion = _assertion(
                id="maya-pref-v1",
                epistemic_status=EpistemicStatus.USER_CONFIRMED,
            )
            store.store(assertion, evaluate_retention(assertion))
            derived_count_before = len(list_current_memory_records(vault._conn))
            store.forget("maya-pref-v1")

            assert store.get_record("maya-pref-v1") is None
            assert list_current_memory_records(vault._conn) == []
            assert derived_count_before == 1
            _assert_no_negation_of_ceramics(vault)

            reestablished = _assertion(
                id="maya-pref-v2",
                epistemic_status=EpistemicStatus.USER_REPORTED,
                evidence_refs=["EV_NEW"],
            )
            store.store(reestablished, evaluate_retention(reestablished))
            record = store.get_record("maya-pref-v2")
            assert record is not None
            assert record.payload["epistemic_status"] == EpistemicStatus.USER_REPORTED.value
            assert record.id != "maya-pref-v1"
