"""RECON-05C — vault MemoryInventory is recall authority, not the index.

Embeddings stay out of this tranche. A scripted candidate index proposes IDs;
only inventory/vault authority may admit them as current memory.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import UTC, datetime, timedelta
from pathlib import Path

import pytest

from personal_enigma.api.storage.memory_inventory import correct_retained_assertion
from personal_enigma.api.storage.retention_vault import VaultDurableAssertionStore
from personal_enigma.api.storage.semantic_recall import VaultInventoryAuthority
from personal_enigma.api.storage.vault import PrivateVault
from personal_enigma.domain.grounding import (
    AssertionKind,
    AssertionValidityKind,
    DerivationKind,
    EpistemicStatus,
    GroundedAssertion,
)
from personal_enigma.domain.retention_gate import evaluate_retention
from personal_enigma.domain.semantic_recall import (
    RECALL_PIPELINE_ORDER,
    CandidateHit,
    RecallRejection,
    recall_governed_memory,
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


@dataclass
class ScriptedCandidateIndex:
    """Approximate retrieval stub — IDs and scores, never assertions."""

    hits_by_query: dict[str, list[CandidateHit]] = field(default_factory=dict)

    def candidate_ids(self, query: str, *, limit: int = 10) -> list[CandidateHit]:
        return list(self.hits_by_query.get(query, []))[:limit]


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


def _boom(*_args: object, **_kwargs: object) -> None:
    raise AssertionError("recall must not write vault or retention state")


def test_current_retained_assertion_is_exposed_with_pipeline_order(
    vault_root: Path, memory_keychain
) -> None:
    assertion = _assertion()
    index = ScriptedCandidateIndex(
        hits_by_query={"ceramics": [CandidateHit(assertion_id=assertion.id, score=0.91)]}
    )

    with PrivateVault.open(root=vault_root, keychain=memory_keychain) as vault:
        store = VaultDurableAssertionStore(vault)
        store.store(assertion, evaluate_retention(assertion))
        authority = VaultInventoryAuthority(vault._conn, store)

        result = recall_governed_memory(
            "ceramics", candidate_index=index, authority=authority
        )
        assert result.stages == RECALL_PIPELINE_ORDER
        assert result.exposed_ids == (assertion.id,)
        exposed = result.assertions[0].assertion
        assert exposed.epistemic_status == EpistemicStatus.USER_CONFIRMED
        assert exposed.evidence_refs == ["EV_CHAT_1"]
        assert exposed.purpose_tags == ["user_explicit_recall"]
        assert result.assertions[0].similarity == 0.91


def test_forgotten_stale_index_hit_is_rejected(
    vault_root: Path, memory_keychain
) -> None:
    assertion = _assertion()
    index = ScriptedCandidateIndex(
        hits_by_query={"ceramics": [CandidateHit(assertion_id=assertion.id, score=0.99)]}
    )

    with PrivateVault.open(root=vault_root, keychain=memory_keychain) as vault:
        store = VaultDurableAssertionStore(vault)
        store.store(assertion, evaluate_retention(assertion))
        authority = VaultInventoryAuthority(vault._conn, store)

        found = recall_governed_memory(
            "ceramics", candidate_index=index, authority=authority
        )
        assert found.exposed_ids == (assertion.id,)

        store.forget(assertion.id)
        assert store.get_record(assertion.id) is None

        result = recall_governed_memory(
            "ceramics", candidate_index=index, authority=authority
        )
        assert assertion.id in result.candidate_ids
        assert result.assertions == ()
        assert result.rejected[assertion.id] == RecallRejection.NOT_IN_GOVERNED_MEMORY


def test_elapsed_ttl_hidden_by_inventory_despite_stale_index_and_vault_row(
    vault_root: Path, memory_keychain
) -> None:
    expired_at = datetime(2026, 1, 1, tzinfo=UTC)
    now = datetime(2026, 1, 3, tzinfo=UTC)
    assertion = _assertion(
        id="maya-ceramics-ttl",
        purpose_tags=["temporary_case"],
        validity_kind=AssertionValidityKind.TTL,
        valid_until=expired_at,
    )
    index = ScriptedCandidateIndex(
        hits_by_query={"ceramics": [CandidateHit(assertion_id=assertion.id, score=0.88)]}
    )

    with PrivateVault.open(root=vault_root, keychain=memory_keychain) as vault:
        store = VaultDurableAssertionStore(vault)
        store.store(assertion, evaluate_retention(assertion))
        leftover = store.get_record(assertion.id)
        assert leftover is not None

        authority = VaultInventoryAuthority(vault._conn, store, now=now)
        result = recall_governed_memory(
            "ceramics", candidate_index=index, authority=authority, now=now
        )
        assert leftover.id == assertion.id
        assert store.get_record(assertion.id) is not None
        assert result.assertions == ()
        assert assertion.id not in result.exposed_ids
        assert result.rejected[assertion.id] == RecallRejection.NOT_IN_GOVERNED_MEMORY


def test_superseded_prior_is_not_current_even_if_index_hits_both(
    vault_root: Path, memory_keychain
) -> None:
    original = _assertion(id="maya-ceramics-v1", value="ceramics")
    correction = _assertion(
        id="maya-ceramics-v2",
        value="studio pottery",
        evidence_refs=["EV_CHAT_2"],
    )
    index = ScriptedCandidateIndex(
        hits_by_query={
            "ceramics": [
                CandidateHit(assertion_id="maya-ceramics-v1", score=0.95),
                CandidateHit(assertion_id="maya-ceramics-v2", score=0.94),
            ]
        }
    )

    with PrivateVault.open(root=vault_root, keychain=memory_keychain) as vault:
        store = VaultDurableAssertionStore(vault)
        store.store(original, evaluate_retention(original))
        correct_retained_assertion(store, "maya-ceramics-v1", correction)
        assert store.get_record("maya-ceramics-v1") is not None

        authority = VaultInventoryAuthority(vault._conn, store)
        result = recall_governed_memory(
            "ceramics", candidate_index=index, authority=authority
        )
        assert result.exposed_ids == ("maya-ceramics-v2",)
        assert result.rejected["maya-ceramics-v1"] == RecallRejection.NOT_IN_GOVERNED_MEMORY
        exposed = result.assertions[0].assertion
        assert exposed.value == "studio pottery"
        assert "maya-ceramics-v1" in exposed.supersedes
        assert "EV_CHAT_2" in exposed.evidence_refs


def test_inverse_reestablishment_exposes_new_lineage_only(
    vault_root: Path, memory_keychain
) -> None:
    forgotten = _assertion(id="maya-ceramics-v1")
    reestablished = _assertion(
        id="maya-ceramics-v2",
        evidence_refs=["EV_CHAT_INDEPENDENT"],
        derived_from=["EV_CHAT_INDEPENDENT"],
    )
    index = ScriptedCandidateIndex(
        hits_by_query={
            "ceramics": [
                CandidateHit(assertion_id=forgotten.id, score=0.97),
                CandidateHit(assertion_id=reestablished.id, score=0.96),
            ]
        }
    )

    with PrivateVault.open(root=vault_root, keychain=memory_keychain) as vault:
        store = VaultDurableAssertionStore(vault)
        store.store(forgotten, evaluate_retention(forgotten))
        store.forget(forgotten.id)
        store.store(reestablished, evaluate_retention(reestablished))
        authority = VaultInventoryAuthority(vault._conn, store)

        result = recall_governed_memory(
            "ceramics", candidate_index=index, authority=authority
        )
        assert result.exposed_ids == (reestablished.id,)
        assert forgotten.id not in result.exposed_ids
        assert result.rejected[forgotten.id] == RecallRejection.NOT_IN_GOVERNED_MEMORY
        exposed = result.assertions[0].assertion
        assert exposed.epistemic_status == EpistemicStatus.USER_CONFIRMED
        assert "EV_CHAT_INDEPENDENT" in exposed.evidence_refs
        assert "EV_CHAT_INDEPENDENT" in exposed.derived_from


def test_similarity_does_not_upgrade_or_rewrite_epistemic_status(
    vault_root: Path, memory_keychain
) -> None:
    reported = _assertion(
        id="maya-ceramics-reported",
        epistemic_status=EpistemicStatus.USER_REPORTED,
        evidence_refs=["EV_CHAT_USER"],
        derived_from=["EV_CHAT_USER"],
    )
    index = ScriptedCandidateIndex(
        hits_by_query={
            "ceramics": [CandidateHit(assertion_id=reported.id, score=0.999)]
        }
    )

    with PrivateVault.open(root=vault_root, keychain=memory_keychain) as vault:
        store = VaultDurableAssertionStore(vault)
        store.store(reported, evaluate_retention(reported))
        authority = VaultInventoryAuthority(vault._conn, store)

        result = recall_governed_memory(
            "ceramics", candidate_index=index, authority=authority
        )
        assert len(result.assertions) == 1
        exposed = result.assertions[0].assertion
        assert exposed.epistemic_status == EpistemicStatus.USER_REPORTED
        assert exposed.epistemic_status is not EpistemicStatus.USER_CONFIRMED
        assert exposed.derivation_kind is None
        assert exposed.derivation_kind is not DerivationKind.SEMANTIC_SIMILARITY
        assert exposed.evidence_refs == ["EV_CHAT_USER"]
        assert result.assertions[0].similarity == 0.999


def test_recall_has_no_write_path(
    vault_root: Path, memory_keychain, monkeypatch: pytest.MonkeyPatch
) -> None:
    assertion = _assertion()
    index = ScriptedCandidateIndex(
        hits_by_query={"ceramics": [CandidateHit(assertion_id=assertion.id, score=0.8)]}
    )

    with PrivateVault.open(root=vault_root, keychain=memory_keychain) as vault:
        store = VaultDurableAssertionStore(vault)
        store.store(assertion, evaluate_retention(assertion))
        retained_before = store.list_retained_ids()
        current_before = [record.id for record in store.list_current_retained()]

        monkeypatch.setattr(store, "store", _boom)
        monkeypatch.setattr(store, "evaluate_and_store", _boom)
        monkeypatch.setattr(store, "forget", _boom)
        monkeypatch.setattr(store, "expire_ttl", _boom)
        monkeypatch.setattr(vault, "store_derived", _boom)

        authority = VaultInventoryAuthority(vault._conn, store)
        assert not hasattr(authority, "store")
        assert not hasattr(authority, "forget")
        assert not hasattr(authority, "evaluate_retention")
        assert not hasattr(recall_governed_memory, "store")

        result = recall_governed_memory(
            "ceramics", candidate_index=index, authority=authority
        )
        assert result.exposed_ids == (assertion.id,)
        assert store.list_retained_ids() == retained_before
        assert [record.id for record in store.list_current_retained()] == current_before


def test_adapter_and_tests_do_not_import_embeddings() -> None:
    import personal_enigma.api.storage.semantic_recall as adapter

    module_source = Path(adapter.__file__).read_text(encoding="utf-8")
    assert "personal_enigma.embeddings" not in module_source
    test_source = Path(__file__).read_text(encoding="utf-8")
    assert "personal_enigma.embeddings" not in test_source
