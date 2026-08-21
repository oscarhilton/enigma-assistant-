"""C32 ceramics freeze: stale index cannot resurrect forgotten memory."""

from __future__ import annotations

from personal_enigma.domain.grounding import (
    AssertionKind,
    EpistemicStatus,
    GroundedAssertion,
)
from personal_enigma.domain.semantic_recall import (
    RECALL_PIPELINE_ORDER,
    InMemoryGovernedMemory,
    RecallRejection,
    recall_governed_memory,
    reduce_retained_assertion,
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


def _index() -> LocalCandidateIndex:
    return LocalCandidateIndex(model=FakeEmbeddingModel(), index=InMemoryVectorIndex())


def test_ceramics_retain_index_recall_finds_it() -> None:
    assertion = _assertion()
    index = _index()
    index.index_assertion(assertion)
    authority = InMemoryGovernedMemory()
    authority.put(assertion)

    result = recall_governed_memory(
        "ceramics", candidate_index=index, authority=authority
    )

    assert result.stages == RECALL_PIPELINE_ORDER
    assert assertion.id in result.candidate_ids
    assert result.exposed_ids == (assertion.id,)
    assert result.assertions[0].assertion.epistemic_status == EpistemicStatus.USER_CONFIRMED


def test_ceramics_forget_stale_embedding_is_not_current_memory() -> None:
    assertion = _assertion()
    index = _index()
    index.index_assertion(assertion)
    authority = InMemoryGovernedMemory()
    authority.put(assertion)

    found = recall_governed_memory("ceramics", candidate_index=index, authority=authority)
    assert found.exposed_ids == (assertion.id,)

    authority.discard(assertion.id)
    assert assertion.id in index

    result = recall_governed_memory("ceramics", candidate_index=index, authority=authority)

    assert assertion.id in result.candidate_ids
    assert result.assertions == ()
    assert result.rejected[assertion.id] == RecallRejection.NOT_IN_GOVERNED_MEMORY
    assert "ceramics" not in " ".join(
        str(item.assertion.value) for item in result.assertions
    )


def test_inverse_reestablishment_finds_new_assertion_not_forgotten_id() -> None:
    forgotten = _assertion(id="maya-ceramics-v1", evidence_refs=["EV_CHAT_1"])
    index = _index()
    index.index_assertion(forgotten)
    authority = InMemoryGovernedMemory()
    authority.put(forgotten)
    authority.discard(forgotten.id)

    reestablished = _assertion(
        id="maya-ceramics-v2",
        evidence_refs=["EV_CHAT_INDEPENDENT"],
        derived_from=["EV_CHAT_INDEPENDENT"],
    )
    assert reestablished.id != forgotten.id
    assert forgotten.id not in reestablished.derived_from
    index.index_assertion(reestablished)
    authority.put(reestablished)

    result = recall_governed_memory("ceramics", candidate_index=index, authority=authority)

    assert forgotten.id in index
    assert result.exposed_ids == (reestablished.id,)
    assert forgotten.id not in result.exposed_ids
    if forgotten.id in result.candidate_ids:
        assert result.rejected[forgotten.id] == RecallRejection.NOT_IN_GOVERNED_MEMORY
    exposed = result.assertions[0].assertion
    assert exposed.id == "maya-ceramics-v2"
    assert exposed.derived_from == ["EV_CHAT_INDEPENDENT"]
    assert exposed.epistemic_status == EpistemicStatus.USER_CONFIRMED


def test_index_payload_is_not_the_assertion() -> None:
    assertion = _assertion()
    index = _index()
    index.index_assertion(assertion)
    hits = index.candidate_ids("ceramics", limit=5)
    assert hits
    assert all(isinstance(hit.assertion_id, str) for hit in hits)
    assert reduce_retained_assertion(assertion) == "Maya likes ceramics"
    assert not hasattr(hits[0], "epistemic_status")
    assert not hasattr(hits[0], "assertion")
