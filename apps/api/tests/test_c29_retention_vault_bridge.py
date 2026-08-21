"""C29 slice 2 — retention gate → SEC-06 vault bridge tests."""

from __future__ import annotations

from datetime import UTC, datetime
from pathlib import Path

import pytest

from personal_enigma.api.storage.retention_vault import (
    RetentionVaultError,
    VaultDurableAssertionStore,
    assertion_lineage_ref,
    build_retained_assertion_payload,
    forget_retained_assertion,
    is_retained_assertion_record,
    map_retention_to_derived_record,
    retention_decision_lineage_ref,
)
from personal_enigma.api.storage.vault import PrivateVault
from personal_enigma.domain.grounding import (
    AssertionKind,
    AssertionValidityKind,
    EpistemicStatus,
    GroundedAssertion,
)
from personal_enigma.domain.retention import (
    DerivedRecordType,
    RetentionClass,
    RetentionPurpose,
)
from personal_enigma.domain.retention_gate import (
    RetentionDecision,
    RetentionOutcome,
    RetentionRejectionReason,
    evaluate_retention,
)


def _assertion(**overrides: object) -> GroundedAssertion:
    base: dict[str, object] = {
        "id": "A1",
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


class TestVaultBridgeMapping:
    def test_maps_durable_decision_to_derived_record(self) -> None:
        assertion = _assertion()
        decision = evaluate_retention(assertion)
        record = map_retention_to_derived_record(assertion, decision)

        assert record.id == assertion.id
        assert is_retained_assertion_record(record)
        assert record.payload["epistemic_status"] == EpistemicStatus.USER_CONFIRMED.value
        assert record.payload["retention_decision"]["outcome"] == RetentionOutcome.DURABLE.value
        assert record.lineage.purpose == RetentionPurpose.USER_EXPLICIT_RECALL
        assert record.lineage.retention_class == RetentionClass.DURABLE_SHADOW
        assert assertion_lineage_ref(assertion.id) in record.lineage.derived_from
        assert retention_decision_lineage_ref(assertion.id) in record.lineage.derived_from
        assert "EV_CHAT_1" in record.lineage.derived_from

    def test_rejects_ephemeral_decision(self) -> None:
        assertion = _assertion(
            epistemic_status=EpistemicStatus.MODEL_INFERRED,
            id="inferred-1",
        )
        decision = evaluate_retention(assertion)
        with pytest.raises(RetentionVaultError, match="Vault write rejected"):
            map_retention_to_derived_record(assertion, decision)

    def test_rejects_reject_decision(self) -> None:
        assertion = _assertion(
            predicate="is_emotionally_dependent_on",
            value="Oscar",
            id="profiling-1",
        )
        decision = evaluate_retention(assertion)
        with pytest.raises(RetentionVaultError, match="Vault write rejected"):
            map_retention_to_derived_record(assertion, decision)

    def test_rejects_forced_durable_on_model_inferred(self) -> None:
        assertion = _assertion(
            id="forced-inferred",
            epistemic_status=EpistemicStatus.MODEL_INFERRED,
            value="may like ceramics",
        )
        forced = RetentionDecision(
            assertion_id=assertion.id,
            outcome=RetentionOutcome.DURABLE,
            retention_class=RetentionClass.DURABLE_SHADOW,
            purpose=RetentionPurpose.LIFE_FACT,
            rationale="invalid forced durable",
        )
        with pytest.raises(RetentionVaultError, match="cannot become durable"):
            map_retention_to_derived_record(assertion, forced)

    def test_epistemic_status_not_upgraded_in_payload(self) -> None:
        assertion = _assertion(
            epistemic_status=EpistemicStatus.USER_REPORTED,
            id="reported-1",
        )
        decision = evaluate_retention(assertion)
        payload = build_retained_assertion_payload(assertion, decision)
        assert payload["epistemic_status"] == EpistemicStatus.USER_REPORTED.value
        assert payload["epistemic_status"] != EpistemicStatus.USER_CONFIRMED.value


class TestVaultBridgePersistence:
    def test_store_writes_retained_assertion_to_vault(
        self, vault_root: Path, memory_keychain
    ) -> None:
        assertion = _assertion()
        decision = evaluate_retention(assertion)
        with PrivateVault.open(root=vault_root, keychain=memory_keychain) as vault:
            store = VaultDurableAssertionStore(vault)
            stored_id = store.store(assertion, decision)
            record = store.get_record(stored_id)

            assert stored_id == assertion.id
            assert record is not None
            assert record.payload["predicate"] == "likes"
            assert record.payload["value"] == "ceramics"

    def test_evaluate_and_store_skips_ephemeral(
        self, vault_root: Path, memory_keychain
    ) -> None:
        assertion = _assertion(
            id="ephemeral-only",
            epistemic_status=EpistemicStatus.MODEL_INFERRED,
        )
        with PrivateVault.open(root=vault_root, keychain=memory_keychain) as vault:
            store = VaultDurableAssertionStore(vault)
            result = store.evaluate_and_store(assertion)
            assert result is None
            assert store.list_retained_ids() == []

    def test_no_vault_entry_without_retention_gate(
        self, vault_root: Path, memory_keychain
    ) -> None:
        """Regression: direct vault write without gate is not a retained assertion."""
        with PrivateVault.open(root=vault_root, keychain=memory_keychain) as vault:
            vault.store_derived_new(
                record_id="direct-write",
                record_type=DerivedRecordType.FACT,
                payload={"predicate": "likes", "value": "ceramics"},
                derived_from=["EV_CHAT_1"],
                purpose=RetentionPurpose.LIFE_FACT,
            )
            store = VaultDurableAssertionStore(vault)
            assert store.list_retained_ids() == []
            assert store.get_record("direct-write") is None

    def test_ttl_decision_persists_with_lifetime(
        self, vault_root: Path, memory_keychain
    ) -> None:
        assertion = _assertion(
            id="ttl-gift",
            predicate="gift_history",
            purpose_tags=["temporary_case"],
            validity_kind=AssertionValidityKind.TTL,
            temporal_scope="gift_planning_2026",
            valid_until=datetime(2026, 6, 1, tzinfo=UTC),
        )
        decision = evaluate_retention(assertion)
        with PrivateVault.open(root=vault_root, keychain=memory_keychain) as vault:
            store = VaultDurableAssertionStore(vault)
            store.store(assertion, decision)
            record = store.get_record("ttl-gift")
            assert record is not None
            assert record.lineage.retention_class == RetentionClass.ACTIVE_UNTIL_RESOLVED
            assert record.lineage.expires_after_resolution is not None


class TestVaultBridgeFreeze:
    def test_truth_not_retention_confirmed_reject_no_vault(
        self, vault_root: Path, memory_keychain
    ) -> None:
        """USER_CONFIRMED truth with REJECT retention → usable in gate, no vault row."""
        assertion = _assertion(
            id="confirmed-reject",
            predicate="is_emotionally_dependent_on",
            value="Oscar",
        )
        decision = evaluate_retention(assertion)
        assert decision.outcome == RetentionOutcome.REJECT
        with PrivateVault.open(root=vault_root, keychain=memory_keychain) as vault:
            store = VaultDurableAssertionStore(vault)
            with pytest.raises(RetentionVaultError):
                store.store(assertion, decision)
            assert store.list_retained_ids() == []

    def test_truth_not_retention_confirmed_ephemeral_no_vault(
        self, vault_root: Path, memory_keychain
    ) -> None:
        """USER_CONFIRMED preference without purpose → EPHEMERAL, no vault row."""
        assertion = _assertion(
            id="confirmed-ephemeral",
            subject="PERSON_Maya",
            purpose_tags=[],
            kind=AssertionKind.FACT,
            predicate="birthday",
            value="March 12",
            epistemic_status=EpistemicStatus.SOURCE_OBSERVED,
        )
        decision = evaluate_retention(assertion)
        assert decision.outcome == RetentionOutcome.DURABLE
        ephemeral = RetentionDecision(
            assertion_id=assertion.id,
            outcome=RetentionOutcome.EPHEMERAL,
            retention_class=RetentionClass.EPHEMERAL_ANSWER_ONLY,
            rejection_reason=RetentionRejectionReason.NO_LEGITIMATE_PURPOSE,
            rationale="simulated ephemeral override",
        )
        with PrivateVault.open(root=vault_root, keychain=memory_keychain) as vault:
            store = VaultDurableAssertionStore(vault)
            with pytest.raises(RetentionVaultError):
                store.store(assertion, ephemeral)
            assert store.list_retained_ids() == []

    def test_invalid_durable_for_inferred_rejected(
        self, vault_root: Path, memory_keychain
    ) -> None:
        """MODEL_INFERRED + forced ALLOW_DURABLE → rejected at vault boundary."""
        assertion = _assertion(
            id="inferred-hypothesis",
            epistemic_status=EpistemicStatus.MODEL_INFERRED,
            value="may like ceramics",
        )
        gate_decision = evaluate_retention(assertion)
        assert gate_decision.outcome == RetentionOutcome.EPHEMERAL
        forced = RetentionDecision(
            assertion_id=assertion.id,
            outcome=RetentionOutcome.DURABLE,
            retention_class=RetentionClass.DURABLE_SHADOW,
            purpose=RetentionPurpose.LIFE_FACT,
        )
        with PrivateVault.open(root=vault_root, keychain=memory_keychain) as vault:
            store = VaultDurableAssertionStore(vault)
            with pytest.raises(RetentionVaultError):
                store.store(assertion, forced)
            assert store.list_retained_ids() == []

    def test_hypothesis_allowed_stays_hypothesis_epistemic_status(
        self, vault_root: Path, memory_keychain
    ) -> None:
        """Even if hypothesis class were allowed, epistemic status must not upgrade."""
        assertion = _assertion(
            id="hypothesis-1",
            kind=AssertionKind.HYPOTHESIS,
            epistemic_status=EpistemicStatus.MODEL_INFERRED,
            predicate="likes",
            value="may like ceramics",
        )
        decision = evaluate_retention(assertion)
        assert decision.outcome == RetentionOutcome.EPHEMERAL
        with PrivateVault.open(root=vault_root, keychain=memory_keychain) as vault:
            store = VaultDurableAssertionStore(vault)
            with pytest.raises(RetentionVaultError):
                store.store(assertion, decision)


class TestVaultBridgeForget:
    def test_forget_cascades_child_retained_assertions(
        self, vault_root: Path, memory_keychain
    ) -> None:
        parent = _assertion(
            id="parent-fact",
            predicate="gift_history",
            value="mug 2024",
            subject="self",
        )
        parent_decision = evaluate_retention(parent)
        child = _assertion(
            id="child-summary",
            kind=AssertionKind.PATTERN,
            predicate="convention",
            value="usually gifts ceramics",
            subject="self",
            epistemic_status=EpistemicStatus.DETERMINISTICALLY_DERIVED,
            derived_from=["parent-fact"],
            purpose_tags=["temporary_case"],
            validity_kind=AssertionValidityKind.DERIVED_LIFETIME,
            temporal_scope="gift_planning_2026",
        )
        child_decision = evaluate_retention(child)
        with PrivateVault.open(root=vault_root, keychain=memory_keychain) as vault:
            store = VaultDurableAssertionStore(vault)
            store.store(parent, parent_decision)
            if child_decision.outcome in (RetentionOutcome.DURABLE, RetentionOutcome.TTL):
                store.store(child, child_decision)
            result = store.forget("parent-fact")
            assert "parent-fact" in result.deleted_assertion_ids
            assert store.list_retained_ids() == []

    def test_forget_lineage_records_deleted_ids(
        self, vault_root: Path, memory_keychain
    ) -> None:
        assertion = _assertion(id="lineage-forget")
        decision = evaluate_retention(assertion)
        with PrivateVault.open(root=vault_root, keychain=memory_keychain) as vault:
            store = VaultDurableAssertionStore(vault)
            store.store(assertion, decision)
            result = forget_retained_assertion(vault._conn, "lineage-forget")
            assert result.root_assertion_id == "lineage-forget"
            assert "lineage-forget" in result.deleted_assertion_ids
            assert vault.count_orphaned_derivatives() == 0
