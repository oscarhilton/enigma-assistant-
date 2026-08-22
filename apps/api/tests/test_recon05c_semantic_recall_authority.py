"""RECON-05C — vault MemoryInventory is recall authority, not the index.

Embeddings stay out of this tranche. A scripted candidate index proposes IDs;
only inventory/vault authority may admit them as current memory.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import UTC, datetime
from pathlib import Path

import pytest

from personal_enigma.api.storage.memory_inventory import correct_retained_assertion
from personal_enigma.api.storage.retention_vault import VaultDurableAssertionStore
from personal_enigma.api.storage.semantic_recall import (
    VaultInventoryAuthority,
    assertion_from_retained_record,
)
from personal_enigma.api.storage.vault import PrivateVault
from personal_enigma.domain.grounding import (
    AssertionKind,
    AssertionValidityKind,
    DerivationKind,
    EpistemicStatus,
    GroundedAssertion,
)
from personal_enigma.domain.retention import (
    DerivedRecord,
    DerivedRecordType,
    LineageMetadata,
    MemoryLayer,
    RetentionClass,
    RetentionPurpose,
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
    import ast

    import personal_enigma.api.storage.semantic_recall as adapter

    def _imported_modules(path: Path) -> set[str]:
        tree = ast.parse(path.read_text(encoding="utf-8"))
        names: set[str] = set()
        for node in ast.walk(tree):
            if isinstance(node, ast.Import):
                names.update(alias.name for alias in node.names)
            elif isinstance(node, ast.ImportFrom) and node.module:
                names.add(node.module)
        return names

    imported = _imported_modules(Path(adapter.__file__)) | _imported_modules(
        Path(__file__)
    )
    assert not any(
        name == "personal_enigma.embeddings"
        or name.startswith("personal_enigma.embeddings.")
        for name in imported
    )


def _retained_record(assertion_id: str, **payload_overrides: object) -> DerivedRecord:
    payload: dict[str, object] = {
        "record_kind": "retained_assertion",
        "assertion_id": assertion_id,
        "kind": "preference",
        "subject": "PERSON_Maya",
        "predicate": "likes",
        "value": "ceramics",
        "epistemic_status": "user_confirmed",
        "evidence_refs": ["EV_CHAT_1"],
        "purpose_tags": ["user_explicit_recall"],
        "validity_kind": "stable",
    }
    payload.update(payload_overrides)
    return DerivedRecord(
        id=assertion_id,
        record_type=DerivedRecordType.FACT,
        memory_layer=MemoryLayer.ACTIVE,
        payload=payload,
        lineage=LineageMetadata(
            derived_from=[f"assertion:{assertion_id}"],
            purpose=RetentionPurpose.USER_EXPLICIT_RECALL,
            retention_class=RetentionClass.DURABLE_SHADOW,
        ),
        created_at=datetime(2026, 1, 1, tzinfo=UTC),
    )


def test_until_event_without_persisted_invalidated_by_does_not_abort_batch(
    vault_root: Path, memory_keychain
) -> None:
    current = _assertion(id="maya-ceramics")
    until_event = _assertion(
        id="maya-until-event",
        purpose_tags=["temporary_case"],
        validity_kind=AssertionValidityKind.UNTIL_EVENT,
        invalidated_by=["EVENT_MOVED"],
    )
    index = ScriptedCandidateIndex(
        hits_by_query={
            "ceramics": [
                CandidateHit(assertion_id=until_event.id, score=0.99),
                CandidateHit(assertion_id=current.id, score=0.90),
            ]
        }
    )

    with PrivateVault.open(root=vault_root, keychain=memory_keychain) as vault:
        store = VaultDurableAssertionStore(vault)
        store.store(until_event, evaluate_retention(until_event))
        store.store(current, evaluate_retention(current))
        stored = store.get_record(until_event.id)
        assert stored is not None
        assert "invalidated_by" not in stored.payload

        authority = VaultInventoryAuthority(vault._conn, store)
        result = recall_governed_memory(
            "ceramics", candidate_index=index, authority=authority
        )
        assert until_event.id in result.candidate_ids
        assert result.rejected[until_event.id] == RecallRejection.NOT_IN_GOVERNED_MEMORY
        assert result.exposed_ids == (current.id,)


def test_naive_validity_timestamps_are_normalized_to_utc() -> None:
    now = datetime(2026, 1, 2, tzinfo=UTC)
    current = assertion_from_retained_record(
        _retained_record(
            "maya-naive-current",
            validity_kind="ttl",
            valid_until="2026-01-03T00:00:00",
        )
    )
    assert current.valid_until is not None
    assert current.valid_until.tzinfo is not None
    assert current.is_usable_now(now=now)

    expired = assertion_from_retained_record(
        _retained_record(
            "maya-naive-expired",
            validity_kind="ttl",
            valid_until="2026-01-01T00:00:00",
        )
    )
    assert expired.valid_until is not None
    assert expired.valid_until.tzinfo is not None
    assert not expired.is_usable_now(now=now)


def test_payload_invalidated_by_is_preserved_when_present() -> None:
    rebuilt = assertion_from_retained_record(
        _retained_record(
            "maya-until-event",
            validity_kind="until_event",
            invalidated_by=["EVENT_MOVED"],
        )
    )
    assert rebuilt.validity_kind == AssertionValidityKind.UNTIL_EVENT
    assert rebuilt.invalidated_by == ["EVENT_MOVED"]
