"""Local candidate index over reduced assertion meaning — not a memory store."""

from __future__ import annotations

from dataclasses import dataclass, field

from personal_enigma.domain.grounding import GroundedAssertion
from personal_enigma.domain.semantic_recall import CandidateHit, reduce_retained_assertion
from personal_enigma.embeddings.protocol import EmbeddingModel, VectorIndex


@dataclass
class LocalCandidateIndex:
    """Vector index from reduced meaning → assertion IDs.

    Payloads are ids and the reduced text used for similarity. They are not
    governed assertions and must not be treated as current memory.
    """

    model: EmbeddingModel
    index: VectorIndex
    _indexed_ids: set[str] = field(default_factory=set)

    def index_assertion(self, assertion: GroundedAssertion) -> str:
        """Embed reduced meaning and key it by assertion id. Does not retain memory."""
        meaning = reduce_retained_assertion(assertion)
        vector = self.model.embed([meaning])[0]
        self.index.upsert(
            [assertion.id],
            [vector],
            [{"assertion_id": assertion.id, "reduced_meaning": meaning}],
        )
        self._indexed_ids.add(assertion.id)
        return assertion.id

    def candidate_ids(self, query: str, *, limit: int = 10) -> list[CandidateHit]:
        """Approximate retrieval only. Hits are candidate IDs, not usable memory."""
        if not query.strip() or limit < 1:
            return []
        query_vector = self.model.embed([query])[0]
        hits = self.index.search(query_vector, limit=limit)
        candidates: list[CandidateHit] = []
        for hit in hits:
            assertion_id = str(hit.get("assertion_id") or hit.get("id") or "")
            if not assertion_id:
                continue
            candidates.append(
                CandidateHit(assertion_id=assertion_id, score=float(hit.get("score", 0.0)))
            )
        return candidates

    def __contains__(self, assertion_id: str) -> bool:
        return assertion_id in self._indexed_ids
