"""RECON-05A — minimal C29 retention→vault adapter tests.

This suite specifies only the first adapter wire:
- retention gate decision is required before durable vault write
- retained assertions are stored as SEC-06 DerivedRecord rows with record_kind marker
- epistemic status is never silently upgraded at the persistence boundary

Deliberately out of scope here (RECON-05B+): retained-assertion forget propagation,
TTL expiry sweep, memory inventory query/correction, semantic recall adapters.
"""

from __future__ import annotations

from datetime import UTC, datetime
from pathlib import Path

import pytest

from personal_enigma.api.storage.retention_vault import (
    RetentionVaultError,
    VaultDurableAssertionStore,
    assertion_lineage_ref,
    build_retained_assertion_payload,
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
from personal_enigma.domain.retention import DerivedRecordType, RetentionClass, RetentionPurpose
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


class TestRetentionVaultMapping:
    def test_maps_durable_decision_to_derived_record(self) -> None:
        assertion = _assertion()
        decision = evaluate_retention(assertion)
        assert decision.outcome == RetentionOutcome.DURABLE
        record = map_retention_to_derived_record(assertion, decision)

        assert record.id == assertion.id
        assert record.record_type == DerivedRecordType.FACT
        assert is_retained_assertion_record(record)
        assert record.payload["assertion_id"] == assertion.id
        assert record.payload["epistemic_status"] == EpistemicStatus.USER_CONFIRMED.value
        assert record.payload["retention_decision"]["outcome"] == RetentionOutcome.DURABLE.value
        assert record.lineage.purpose == RetentionPurpose.USER_EXPLICIT_RECALL
        assert record.lineage.retention_class == RetentionClass.DURABLE_SHADOW
        assert record.created_at.tzinfo is not None

        assert assertion_lineage_ref(assertion.id) in record.lineage.derived_from
        assert retention_decision_lineage_ref(assertion.id) in record.lineage.derived_from
        assert "EV_CHAT_1" in record.lineage.derived_from
        assert assertion.id not in record.lineage.derived_from

    def test_parent_assertion_refs_are_namespaced_only(self) -> None:
        assertion = _assertion(id="child", derived_from=["PARENT1"])
        decision = evaluate_retention(assertion)
        assert decision.outcome == RetentionOutcome.DURABLE
        record = map_retention_to_derived_record(assertion, decision)

        assert assertion_lineage_ref("PARENT1") in record.lineage.derived_from
        assert "PARENT1" not in record.lineage.derived_from

    def test_rejects_ephemeral_gate_outcomes(self) -> None:
        assertion = _assertion(
            epistemic_status=EpistemicStatus.MODEL_INFERRED,
            id="inferred-1",
            value="may like ceramics",
        )
        decision = evaluate_retention(assertion)
        assert decision.outcome == RetentionOutcome.EPHEMERAL
        with pytest.raises(RetentionVaultError, match="Vault write rejected"):
            map_retention_to_derived_record(assertion, decision)

    def test_rejects_reject_gate_outcomes(self) -> None:
        assertion = _assertion(
            predicate="is_emotionally_dependent_on",
            value="Oscar",
            id="profiling-1",
        )
        decision = evaluate_retention(assertion)
        assert decision.outcome == RetentionOutcome.REJECT
        with pytest.raises(RetentionVaultError, match="Vault write rejected"):
            map_retention_to_derived_record(assertion, decision)

    def test_ttl_gate_outcome_is_not_persistable_in_recon05a(self) -> None:
        assertion = _assertion(
            id="ttl-gift",
            kind=AssertionKind.FACT,
            predicate="gift_history",
            purpose_tags=["temporary_case"],
            validity_kind=AssertionValidityKind.TTL,
            temporal_scope="gift_planning_2026",
            valid_until=datetime(2026, 6, 1, tzinfo=UTC),
        )
        decision = evaluate_retention(assertion)
        assert decision.outcome == RetentionOutcome.TTL
        with pytest.raises(RetentionVaultError, match="RECON-05A supports DURABLE"):
            map_retention_to_derived_record(assertion, decision)

    def test_epistemic_status_is_not_upgraded_in_payload(self) -> None:
        assertion = _assertion(
            epistemic_status=EpistemicStatus.USER_REPORTED,
            id="reported-1",
        )
        decision = evaluate_retention(assertion)
        payload = build_retained_assertion_payload(assertion, decision)
        assert payload["epistemic_status"] == EpistemicStatus.USER_REPORTED.value
        assert payload["epistemic_status"] != EpistemicStatus.USER_CONFIRMED.value

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

    def test_rejects_decision_with_rejection_reason_even_if_durable(self) -> None:
        assertion = _assertion(id="bad-decision")
        forced = RetentionDecision(
            assertion_id=assertion.id,
            outcome=RetentionOutcome.DURABLE,
            retention_class=RetentionClass.DURABLE_SHADOW,
            purpose=RetentionPurpose.LIFE_FACT,
            rejection_reason=RetentionRejectionReason.NO_LEGITIMATE_PURPOSE,
            rationale="contradictory decision object",
        )
        with pytest.raises(RetentionVaultError, match="rejection reason"):
            map_retention_to_derived_record(assertion, forced)


class TestVaultDurableAssertionStore:
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
            assert store.list_retained_ids() == [assertion.id]

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

    def test_direct_vault_write_without_gate_is_not_a_retained_assertion(
        self, vault_root: Path, memory_keychain
    ) -> None:
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

    def test_store_recomputes_gate_and_rejects_mismatched_decision(
        self, vault_root: Path, memory_keychain
    ) -> None:
        assertion = _assertion(id="maya-ceramics")
        expected = evaluate_retention(assertion)
        assert expected.outcome == RetentionOutcome.DURABLE
        supplied = RetentionDecision(
            assertion_id=assertion.id,
            outcome=expected.outcome,
            retention_class=expected.retention_class,
            purpose=RetentionPurpose.LIFE_FACT,
            lifetime=expected.lifetime,
            provenance_refs=list(expected.provenance_refs),
            rejection_reason=expected.rejection_reason,
            rationale="caller-supplied mismatch",
        )
        with PrivateVault.open(root=vault_root, keychain=memory_keychain) as vault:
            store = VaultDurableAssertionStore(vault)
            with pytest.raises(RetentionVaultError, match="does not match canonical"):
                store.store(assertion, supplied)

    def test_ttl_retention_is_unsupported_in_recon05a(
        self, vault_root: Path, memory_keychain
    ) -> None:
        assertion = _assertion(
            id="ttl-gift",
            kind=AssertionKind.FACT,
            predicate="gift_history",
            purpose_tags=["temporary_case"],
            validity_kind=AssertionValidityKind.TTL,
            temporal_scope="gift_planning_2026",
            valid_until=datetime(2026, 6, 1, tzinfo=UTC),
        )
        decision = evaluate_retention(assertion)
        assert decision.outcome == RetentionOutcome.TTL
        with PrivateVault.open(root=vault_root, keychain=memory_keychain) as vault:
            store = VaultDurableAssertionStore(vault)
            with pytest.raises(RetentionVaultError, match="unsupported for non-durable"):
                store.store(assertion, decision)
            assert store.list_retained_ids() == []

    def test_in_place_rewrite_is_forbidden(
        self, vault_root: Path, memory_keychain
    ) -> None:
        original = _assertion(id="maya-ceramics-v1", value="ceramics")
        edited = _assertion(id="maya-ceramics-v1", value="pottery")

        with PrivateVault.open(root=vault_root, keychain=memory_keychain) as vault:
            store = VaultDurableAssertionStore(vault)
            store.store(original, evaluate_retention(original))

            with pytest.raises(RetentionVaultError, match="In-place rewrite"):
                store.store(edited, evaluate_retention(edited))

            record = store.get_record("maya-ceramics-v1")
            assert record is not None
            assert record.payload["value"] == "ceramics"

    def test_id_collision_with_non_retained_row_is_rejected(
        self, vault_root: Path, memory_keychain
    ) -> None:
        assertion = _assertion(
            id="collision-id",
            subject="PERSON_Maya",
            predicate="likes",
            value="ceramics",
        )
        decision = evaluate_retention(assertion)
        assert decision.outcome == RetentionOutcome.DURABLE

        with PrivateVault.open(root=vault_root, keychain=memory_keychain) as vault:
            vault.store_derived_new(
                record_id="collision-id",
                record_type=DerivedRecordType.FACT,
                payload={"label": "preexisting", "predicate": "likes", "value": "cats"},
                derived_from=["SRC_X"],
                purpose=RetentionPurpose.LIFE_FACT,
            )
            existing = vault.get_derived_record("collision-id")
            assert existing is not None
            assert is_retained_assertion_record(existing) is False
            assert existing.payload.get("label") == "preexisting"

            store = VaultDurableAssertionStore(vault)
            with pytest.raises(RetentionVaultError, match="id collision"):
                store.store(assertion, decision)
            after = vault.get_derived_record("collision-id")
            assert after is not None
            assert is_retained_assertion_record(after) is False
            assert after.payload.get("label") == "preexisting"

