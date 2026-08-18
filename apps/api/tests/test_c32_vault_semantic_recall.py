"""C32 ceramics freeze against vault MemoryInventory authority."""

from __future__ import annotations

from datetime import UTC, datetime
from pathlib import Path

import pytest

from personal_enigma.api.storage.retention_vault import VaultDurableAssertionStore
from personal_enigma.api.storage.semantic_recall import VaultInventoryAuthority
from personal_enigma.api.storage.vault import PrivateVault
from personal_enigma.domain.grounding import (
    AssertionKind,
    AssertionValidityKind,
    EpistemicStatus,
    GroundedAssertion,
)
from personal_enigma.domain.retention_gate import evaluate_retention
from personal_enigma.domain.semantic_recall import (
    RECALL_PIPELINE_ORDER,
    RecallRejection,
    recall_governed_memory,
)
from personal_enigma.embeddings import FakeEmbeddingModel, InMemoryVectorIndex
from personal_enigma.embeddings.governed_index import LocalCandidateIndex


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


def test_ceramics_forget_stale_index_rejected_by_inventory(
    vault_root: Path, memory_keychain
) -> None:
    assertion = _assertion()
    index = LocalCandidateIndex(model=FakeEmbeddingModel(), index=InMemoryVectorIndex())
    index.index_assertion(assertion)

    with PrivateVault.open(root=vault_root, keychain=memory_keychain) as vault:
        store = VaultDurableAssertionStore(vault)
        store.store(assertion, evaluate_retention(assertion))
        authority = VaultInventoryAuthority(vault._conn, store)

        found = recall_governed_memory(
            "ceramics", candidate_index=index, authority=authority
        )
        assert found.stages == RECALL_PIPELINE_ORDER
        assert found.exposed_ids == (assertion.id,)

        store.forget(assertion.id)
        assert assertion.id in index

        result = recall_governed_memory(
            "ceramics", candidate_index=index, authority=authority
        )
        assert assertion.id in result.candidate_ids
        assert result.assertions == ()
        assert result.rejected[assertion.id] == RecallRejection.NOT_IN_GOVERNED_MEMORY


def test_inverse_reestablishment_through_inventory(
    vault_root: Path, memory_keychain
) -> None:
    forgotten = _assertion(id="maya-ceramics-v1")
    index = LocalCandidateIndex(model=FakeEmbeddingModel(), index=InMemoryVectorIndex())
    index.index_assertion(forgotten)

    with PrivateVault.open(root=vault_root, keychain=memory_keychain) as vault:
        store = VaultDurableAssertionStore(vault)
        store.store(forgotten, evaluate_retention(forgotten))
        store.forget(forgotten.id)

        reestablished = _assertion(
            id="maya-ceramics-v2",
            evidence_refs=["EV_CHAT_INDEPENDENT"],
            derived_from=["EV_CHAT_INDEPENDENT"],
        )
        store.store(reestablished, evaluate_retention(reestablished))
        index.index_assertion(reestablished)
        authority = VaultInventoryAuthority(vault._conn, store)

        result = recall_governed_memory(
            "ceramics", candidate_index=index, authority=authority
        )
        assert result.exposed_ids == (reestablished.id,)
        assert forgotten.id not in result.exposed_ids
        exposed = result.assertions[0].assertion
        assert exposed.epistemic_status == EpistemicStatus.USER_CONFIRMED
        assert "EV_CHAT_INDEPENDENT" in exposed.derived_from


def test_elapsed_ttl_hidden_by_inventory_despite_stale_index(
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
    index = LocalCandidateIndex(model=FakeEmbeddingModel(), index=InMemoryVectorIndex())
    index.index_assertion(assertion)

    with PrivateVault.open(root=vault_root, keychain=memory_keychain) as vault:
        store = VaultDurableAssertionStore(vault)
        store.store(assertion, evaluate_retention(assertion))
        authority = VaultInventoryAuthority(vault._conn, store, now=now)

        result = recall_governed_memory(
            "ceramics", candidate_index=index, authority=authority, now=now
        )
        assert assertion.id in index
        assert result.assertions == ()
        assert assertion.id not in result.exposed_ids
        assert result.rejected.get(assertion.id) == RecallRejection.NOT_IN_GOVERNED_MEMORY
