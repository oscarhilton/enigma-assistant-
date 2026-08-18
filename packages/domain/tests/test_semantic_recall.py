"""C32 semantic recall — index + governed-memory filter, not a second store."""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import UTC, datetime, timedelta

from personal_enigma.domain.grounding import (
    AssertionKind,
    AssertionValidityKind,
    EpistemicStatus,
    GroundedAssertion,
)
from personal_enigma.domain.semantic_recall import (
    RECALL_PIPELINE_ORDER,
    CandidateHit,
    InMemoryGovernedMemory,
    RecallRejection,
    RecallStage,
    recall_governed_memory,
    reduce_retained_assertion,
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
    """Approximate retrieval stub — returns configured IDs, never assertions."""

    hits_by_query: dict[str, list[CandidateHit]] = field(default_factory=dict)

    def candidate_ids(self, query: str, *, limit: int = 10) -> list[CandidateHit]:
        return list(self.hits_by_query.get(query, []))[:limit]


def test_reduce_uses_structured_claim_not_raw_source() -> None:
    raw_email = (
        "From: maya@example.com\n"
        "Hey - I spent the whole weekend throwing bowls at Clayworks on Maple."
    )
    assertion = _assertion(evidence_refs=[raw_email, "EV_CHAT_1"])
    meaning = reduce_retained_assertion(assertion)
    assert meaning == "Maya likes ceramics"
    assert "Clayworks" not in meaning
    assert "maya@example.com" not in meaning
    assert "From:" not in meaning


def test_pipeline_order_is_fixed_and_filter_runs_after_retrieval() -> None:
    assertion = _assertion()
    index = ScriptedCandidateIndex(
        hits_by_query={"ceramics": [CandidateHit(assertion_id=assertion.id, score=0.99)]}
    )
    authority = InMemoryGovernedMemory()
    authority.put(assertion)

    result = recall_governed_memory("ceramics", candidate_index=index, authority=authority)

    assert result.stages == RECALL_PIPELINE_ORDER
    assert result.stages[0] == RecallStage.APPROXIMATE_RETRIEVAL
    assert result.stages[1] == RecallStage.CANDIDATE_ASSERTION_IDS
    assert result.stages[2] == RecallStage.GOVERNED_MEMORY_LOOKUP
    assert result.stages[3] == RecallStage.CURRENT_RETAINED_VALID_CHECK
    assert result.stages[4] == RecallStage.EXPOSE_ASSERTION
    assert result.candidate_ids == (assertion.id,)
    assert result.exposed_ids == (assertion.id,)


def test_embedding_hit_is_not_usable_memory_without_authority() -> None:
    index = ScriptedCandidateIndex(
        hits_by_query={"ceramics": [CandidateHit(assertion_id="maya-ceramics", score=1.0)]}
    )
    authority = InMemoryGovernedMemory()

    result = recall_governed_memory("ceramics", candidate_index=index, authority=authority)

    assert result.candidate_ids == ("maya-ceramics",)
    assert result.assertions == ()
    assert result.rejected["maya-ceramics"] == RecallRejection.NOT_IN_GOVERNED_MEMORY


def test_similarity_never_upgrades_epistemic_status() -> None:
    inferred = _assertion(
        id="maya-ceramics-inferred",
        epistemic_status=EpistemicStatus.MODEL_INFERRED,
    )
    index = ScriptedCandidateIndex(
        hits_by_query={"ceramics": [CandidateHit(assertion_id=inferred.id, score=0.999)]}
    )
    authority = InMemoryGovernedMemory()
    authority.put(inferred)

    result = recall_governed_memory("ceramics", candidate_index=index, authority=authority)

    assert len(result.assertions) == 1
    exposed = result.assertions[0].assertion
    assert exposed.epistemic_status == EpistemicStatus.MODEL_INFERRED
    assert exposed.epistemic_status is not EpistemicStatus.USER_CONFIRMED
    assert result.assertions[0].similarity == 0.999
    assert exposed.derivation_kind is None


def test_elapsed_ttl_is_not_current_even_if_candidate_hits() -> None:
    now = datetime(2026, 8, 18, tzinfo=UTC)
    expired = _assertion(
        validity_kind=AssertionValidityKind.TTL,
        valid_until=now - timedelta(hours=1),
    )
    index = ScriptedCandidateIndex(
        hits_by_query={"ceramics": [CandidateHit(assertion_id=expired.id, score=0.9)]}
    )
    authority = InMemoryGovernedMemory()
    authority.put(expired)

    result = recall_governed_memory(
        "ceramics", candidate_index=index, authority=authority, now=now
    )

    assert result.candidate_ids == (expired.id,)
    assert result.exposed_ids == ()
    assert result.rejected[expired.id] == RecallRejection.NOT_CURRENT


def test_recall_function_has_no_store_or_retain_surface() -> None:
    assert not hasattr(recall_governed_memory, "store")
    names = recall_governed_memory.__code__.co_varnames
    assert "store" not in names
    assert "retain" not in names
    assert "evaluate_retention" not in names
