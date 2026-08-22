"""C29 slice 4 — MemoryInventory freeze tests against vault + forget/TTL."""

from __future__ import annotations

from datetime import UTC, datetime, timedelta
from pathlib import Path

import pytest

from personal_enigma.api.storage.memory_inventory import (
    correct_retained_assertion,
    inspect_memory_why,
    list_memory_inventory,
)
from personal_enigma.api.storage.retention_vault import (
    RetentionVaultError,
    VaultDurableAssertionStore,
)
from personal_enigma.api.storage.vault import PrivateVault
from personal_enigma.domain.grounding import (
    AssertionKind,
    AssertionValidityKind,
    EpistemicStatus,
    GroundedAssertion,
)
from personal_enigma.domain.memory_inventory import (
    FORGET_RETAINED_ASSERTION_ACTION,
    MemoryInventoryStatus,
    inventory_contains_profiling_claim,
)
from personal_enigma.domain.retention_gate import RetentionOutcome, evaluate_retention

_RAW_EMAIL = (
    b"From: maya@example.com\n"
    b"Hey - I spent the whole weekend throwing bowls at Clayworks on Maple. "
    b"Bring the kiln notes tomorrow?\n"
)


def _assertion(**overrides: object) -> GroundedAssertion:
    base: dict[str, object] = {
        "id": "maya-ceramics",
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


class TestWhyRemember:
    def test_why_maya_likes_ceramics_is_inspectable(
        self, vault_root: Path, memory_keychain
    ) -> None:
        assertion = _assertion()
        with PrivateVault.open(root=vault_root, keychain=memory_keychain) as vault:
            store = VaultDurableAssertionStore(vault)
            store.store(assertion, evaluate_retention(assertion))

            inventory = list_memory_inventory(vault._conn, subject="PERSON_Maya")
            entry = inventory.get("maya-ceramics")
            assert entry is not None
            assert entry.claim == "Maya likes ceramics"
            assert entry.inventory_status == MemoryInventoryStatus.KNOWN
            assert entry.epistemic_status == EpistemicStatus.USER_CONFIRMED

            why = inspect_memory_why(vault._conn, "maya-ceramics")
            assert why is not None
            assert why.purpose is not None
            assert why.purpose.value == "user_explicit_recall"
            assert "EV_CHAT_1" in why.provenance_refs
            assert why.retained_at is not None
            assert why.rationale
            assert "shrug" not in why.rationale.lower()
            assert entry.forget.action == FORGET_RETAINED_ASSERTION_ACTION
            assert entry.forget.available is True
            assert entry.can_correct is True


class TestCorrectionSupersession:
    def test_correction_mints_new_lineage_without_rewriting_history(
        self, vault_root: Path, memory_keychain
    ) -> None:
        original = _assertion(id="maya-ceramics-v1", value="ceramics")
        with PrivateVault.open(root=vault_root, keychain=memory_keychain) as vault:
            store = VaultDurableAssertionStore(vault)
            store.store(original, evaluate_retention(original))
            stored = store.get_record("maya-ceramics-v1")
            assert stored is not None
            prior_payload = dict(stored.payload)

            correction = _assertion(
                id="maya-ceramics-v2",
                value="studio pottery",
                evidence_refs=["EV_CHAT_2"],
                epistemic_status=EpistemicStatus.USER_CONFIRMED,
            )
            new_id = correct_retained_assertion(store, "maya-ceramics-v1", correction)

            assert new_id == "maya-ceramics-v2"
            unchanged = store.get_record("maya-ceramics-v1")
            assert unchanged is not None
            assert unchanged.payload["value"] == "ceramics"
            assert unchanged.payload["value"] == prior_payload["value"]
            assert unchanged.payload["epistemic_status"] == prior_payload["epistemic_status"]

            current = list_memory_inventory(vault._conn, subject="Maya")
            assert current.get("maya-ceramics-v1") is None
            entry = current.get("maya-ceramics-v2")
            assert entry is not None
            assert entry.value == "studio pottery"
            assert "maya-ceramics-v1" in entry.supersedes
            assert "maya-ceramics-v1" in entry.derived_from
            assert entry.claim == "Maya likes studio pottery"

            stored_v2 = store.get_record("maya-ceramics-v2")
            assert stored_v2 is not None
            lineage = stored_v2.lineage.derived_from
            assert "assertion:maya-ceramics-v1" in lineage
            assert "assertion:assertion:maya-ceramics-v1" not in lineage
            payload_parents = stored_v2.payload["derived_from_assertion_ids"]
            assert "assertion:maya-ceramics-v1" not in payload_parents

    def test_forgetting_correction_does_not_resurrect_prior(
        self, vault_root: Path, memory_keychain
    ) -> None:
        original = _assertion(id="maya-ceramics-v1", value="ceramics")
        with PrivateVault.open(root=vault_root, keychain=memory_keychain) as vault:
            store = VaultDurableAssertionStore(vault)
            store.store(original, evaluate_retention(original))
            correction = _assertion(
                id="maya-ceramics-v2",
                value="studio pottery",
                evidence_refs=["EV_CHAT_2"],
            )
            correct_retained_assertion(store, "maya-ceramics-v1", correction)

            result = store.forget("maya-ceramics-v2")
            assert "maya-ceramics-v2" in result.deleted_assertion_ids
            assert "maya-ceramics-v1" in result.deleted_assertion_ids
            assert store.get_record("maya-ceramics-v1") is None
            after = list_memory_inventory(vault._conn, subject="Maya")
            assert after.get("maya-ceramics-v1") is None
            assert after.get("maya-ceramics-v2") is None
            dumped = after.model_dump_json()
            assert "ceramics" not in dumped
            assert "studio pottery" not in dumped

    def test_forgetting_prior_keeps_independently_retained_correction(
        self, vault_root: Path, memory_keychain
    ) -> None:
        original = _assertion(id="maya-ceramics-v1", value="ceramics")
        with PrivateVault.open(root=vault_root, keychain=memory_keychain) as vault:
            store = VaultDurableAssertionStore(vault)
            store.store(original, evaluate_retention(original))
            correction = _assertion(
                id="maya-ceramics-v2",
                value="studio pottery",
                evidence_refs=["EV_CHAT_2"],
            )
            correct_retained_assertion(store, "maya-ceramics-v1", correction)

            result = store.forget("maya-ceramics-v1")
            assert "maya-ceramics-v1" in result.deleted_assertion_ids
            assert "maya-ceramics-v2" not in result.deleted_assertion_ids
            assert store.get_record("maya-ceramics-v2") is not None
            after = list_memory_inventory(vault._conn, subject="Maya")
            assert after.get("maya-ceramics-v1") is None
            entry = after.get("maya-ceramics-v2")
            assert entry is not None
            assert entry.value == "studio pottery"

    def test_same_id_store_is_rejected_as_history_rewrite(
        self, vault_root: Path, memory_keychain
    ) -> None:
        original = _assertion(id="maya-ceramics-v1")
        with PrivateVault.open(root=vault_root, keychain=memory_keychain) as vault:
            store = VaultDurableAssertionStore(vault)
            store.store(original, evaluate_retention(original))
            edited = _assertion(id="maya-ceramics-v1", value="pottery")
            with pytest.raises(RetentionVaultError, match="In-place rewrite"):
                store.store(edited, evaluate_retention(edited))
            record = store.get_record("maya-ceramics-v1")
            assert record is not None
            assert record.payload["value"] == "ceramics"


class TestForgetAndExpiryInventory:
    def test_forgotten_item_absent_from_current_inventory(
        self, vault_root: Path, memory_keychain
    ) -> None:
        ceramics = _assertion(id="maya-ceramics")
        birthday = _assertion(
            id="maya-birthday",
            kind=AssertionKind.FACT,
            predicate="birthday",
            value="14 March",
            evidence_refs=["EV_CALENDAR_1"],
        )
        with PrivateVault.open(root=vault_root, keychain=memory_keychain) as vault:
            store = VaultDurableAssertionStore(vault)
            store.store(ceramics, evaluate_retention(ceramics))
            store.store(birthday, evaluate_retention(birthday))

            before = list_memory_inventory(vault._conn, subject="PERSON_Maya")
            assert {entry.assertion_id for entry in before.entries} == {
                "maya-ceramics",
                "maya-birthday",
            }

            result = store.forget("maya-ceramics")
            assert "maya-ceramics" in result.deleted_assertion_ids

            after = list_memory_inventory(vault._conn, subject="PERSON_Maya")
            assert after.get("maya-ceramics") is None
            assert after.get("maya-birthday") is not None
            dumped = after.model_dump_json()
            assert "ceramics" not in dumped

    def test_expired_ttl_absent_from_current_inventory(
        self, vault_root: Path, memory_keychain
    ) -> None:
        expired_at = datetime(2026, 1, 1, tzinfo=UTC)
        now = datetime(2026, 1, 3, tzinfo=UTC)
        plan = _assertion(
            id="gift-plan",
            predicate="gift_history",
            value="mug 2024",
            purpose_tags=["temporary_case"],
            validity_kind=AssertionValidityKind.TTL,
            temporal_scope="gift_planning_2026",
            valid_until=expired_at,
        )
        decision = evaluate_retention(plan)
        assert decision.outcome == RetentionOutcome.TTL
        with PrivateVault.open(root=vault_root, keychain=memory_keychain) as vault:
            store = VaultDurableAssertionStore(vault)
            store.store(plan, decision)
            still_listed = list_memory_inventory(vault._conn, now=expired_at - timedelta(days=1))
            gift = still_listed.get("gift-plan")
            assert gift is not None
            assert gift.inventory_status == MemoryInventoryStatus.EXPIRING

            store.expire_ttl(now=now)
            after = list_memory_inventory(vault._conn, now=now)
            assert after.get("gift-plan") is None


class TestDetectiveNotDossier:
    def test_inventory_keeps_practical_facts_not_inferred_psychology(
        self, vault_root: Path, memory_keychain
    ) -> None:
        ceramics = _assertion(id="maya-ceramics")
        birthday = _assertion(
            id="maya-birthday",
            kind=AssertionKind.FACT,
            predicate="birthday",
            value="14 March",
        )
        profiling = _assertion(
            id="maya-profile",
            predicate="is_emotionally_dependent_on",
            value="Oscar",
        )
        inferred_trait = _assertion(
            id="maya-anxious",
            kind=AssertionKind.HYPOTHESIS,
            predicate="personality_type",
            value="anxious achiever",
            epistemic_status=EpistemicStatus.MODEL_INFERRED,
            purpose_tags=[],
        )
        with PrivateVault.open(root=vault_root, keychain=memory_keychain) as vault:
            store = VaultDurableAssertionStore(vault)
            store.evaluate_and_store(ceramics)
            store.evaluate_and_store(birthday)
            assert store.evaluate_and_store(profiling) is None
            assert store.evaluate_and_store(inferred_trait) is None

            inventory = list_memory_inventory(vault._conn, subject="Maya")
            claims = {entry.claim for entry in inventory.entries}
            predicates = {entry.predicate for entry in inventory.entries}
            assert "Maya likes ceramics" in claims
            assert any("birthday" in claim for claim in claims)
            assert "personality_type" not in predicates
            assert "is_emotionally_dependent_on" not in predicates
            assert inventory_contains_profiling_claim(inventory) is False
            assert all(
                entry.inventory_status != MemoryInventoryStatus.KNOWN
                or entry.epistemic_status != EpistemicStatus.MODEL_INFERRED
                for entry in inventory.entries
            )


class TestNoRawSource:
    def test_inspecting_memory_does_not_dump_email_body(
        self, vault_root: Path, memory_keychain
    ) -> None:
        with PrivateVault.open(root=vault_root, keychain=memory_keychain) as vault:
            vault.store_raw_source(
                source="gmail",
                external_id="msg-maya-studio",
                raw_content=_RAW_EMAIL,
                record_id="EMAIL_MAYA_STUDIO",
            )
            assertion = _assertion(
                id="maya-ceramics",
                evidence_refs=["EMAIL_MAYA_STUDIO"],
            )
            store = VaultDurableAssertionStore(vault)
            store.store(assertion, evaluate_retention(assertion))

            inventory = list_memory_inventory(vault._conn, subject="Maya")
            dumped = inventory.model_dump_json()
            assert "throwing bowls" not in dumped
            assert "Clayworks" not in dumped
            assert "Maple" not in dumped
            assert "maya@example.com" not in dumped
            entry = inventory.get("maya-ceramics")
            assert entry is not None
            assert "EMAIL_MAYA_STUDIO" in entry.provenance_refs
            assert "EMAIL_MAYA_STUDIO" in entry.why.provenance_refs


class TestEpistemicDisplay:
    def test_model_inferred_does_not_appear_as_known(
        self, vault_root: Path, memory_keychain
    ) -> None:
        inferred = _assertion(
            id="inferred-ceramics",
            epistemic_status=EpistemicStatus.MODEL_INFERRED,
            value="may like ceramics",
        )
        confirmed = _assertion(id="maya-ceramics")
        with PrivateVault.open(root=vault_root, keychain=memory_keychain) as vault:
            store = VaultDurableAssertionStore(vault)
            assert store.evaluate_and_store(inferred) is None
            store.evaluate_and_store(confirmed)
            inventory = list_memory_inventory(vault._conn, subject="Maya")
            assert inventory.get("inferred-ceramics") is None
            known = inventory.get("maya-ceramics")
            assert known is not None
            assert known.inventory_status == MemoryInventoryStatus.KNOWN
            assert known.epistemic_status == EpistemicStatus.USER_CONFIRMED
            assert all(
                entry.epistemic_status != EpistemicStatus.MODEL_INFERRED
                for entry in inventory.entries
            )

    def test_conflicted_current_claims_display_as_conflicted(
        self, vault_root: Path, memory_keychain
    ) -> None:
        ceramics = _assertion(id="likes-ceramics", value="ceramics")
        painting = _assertion(id="likes-painting", value="painting")
        with PrivateVault.open(root=vault_root, keychain=memory_keychain) as vault:
            store = VaultDurableAssertionStore(vault)
            store.store(ceramics, evaluate_retention(ceramics))
            store.store(painting, evaluate_retention(painting))
            inventory = list_memory_inventory(vault._conn, subject="Maya")
            ceramics_entry = inventory.get("likes-ceramics")
            painting_entry = inventory.get("likes-painting")
            assert ceramics_entry is not None
            assert painting_entry is not None
            assert ceramics_entry.inventory_status == MemoryInventoryStatus.CONFLICTED
            assert painting_entry.inventory_status == MemoryInventoryStatus.CONFLICTED
