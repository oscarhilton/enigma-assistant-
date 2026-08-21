"""Semantic recall is an index over governed memory — never a truth store.

Constitutional rule:

> Recall may find governed memory. It may not create, promote, resurrect, or retain it.

> Retrieval may be approximate. Authority may not be.

Required order (must not flip):

```text
approximate retrieval
  → candidate assertion IDs
  → governed-memory lookup
  → current / retained / valid check
  → only then expose assertion
```

An embedding hit is never usable memory.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import UTC, datetime
from enum import StrEnum
from typing import Protocol, runtime_checkable

from personal_enigma.domain.grounding import EpistemicStatus, GroundedAssertion
from personal_enigma.domain.memory_inventory import MemoryInventory, format_memory_claim


class RecallStage(StrEnum):
    """Pipeline stages in the only legal order."""

    APPROXIMATE_RETRIEVAL = "approximate_retrieval"
    CANDIDATE_ASSERTION_IDS = "candidate_assertion_ids"
    GOVERNED_MEMORY_LOOKUP = "governed_memory_lookup"
    CURRENT_RETAINED_VALID_CHECK = "current_retained_valid_check"
    EXPOSE_ASSERTION = "expose_assertion"


RECALL_PIPELINE_ORDER: tuple[RecallStage, ...] = (
    RecallStage.APPROXIMATE_RETRIEVAL,
    RecallStage.CANDIDATE_ASSERTION_IDS,
    RecallStage.GOVERNED_MEMORY_LOOKUP,
    RecallStage.CURRENT_RETAINED_VALID_CHECK,
    RecallStage.EXPOSE_ASSERTION,
)


class RecallRejection(StrEnum):
    """Why a candidate ID was not exposed as current memory."""

    NOT_IN_GOVERNED_MEMORY = "not_in_governed_memory"
    NOT_CURRENT = "not_current"


@dataclass(frozen=True)
class CandidateHit:
    """Approximate retrieval result — an ID and a score, not a memory."""

    assertion_id: str
    score: float


@dataclass(frozen=True)
class RecalledAssertion:
    """Governed assertion admitted after the filter. Similarity is metadata only."""

    assertion: GroundedAssertion
    candidate_id: str
    similarity: float

    @property
    def epistemic_status(self) -> EpistemicStatus:
        return self.assertion.epistemic_status


@dataclass(frozen=True)
class RecallResult:
    """Inspectable recall outcome. Candidates may be wrong; exposed memory may not."""

    query: str
    stages: tuple[RecallStage, ...]
    candidate_ids: tuple[str, ...]
    rejected: dict[str, RecallRejection]
    assertions: tuple[RecalledAssertion, ...]

    @property
    def exposed_ids(self) -> tuple[str, ...]:
        return tuple(item.candidate_id for item in self.assertions)


@runtime_checkable
class CandidateAssertionIndex(Protocol):
    """Approximate index from reduced meaning → assertion IDs.

    Implementations must not treat hits as current memory.
    """

    def candidate_ids(self, query: str, *, limit: int = 10) -> list[CandidateHit]: ...


@runtime_checkable
class GovernedMemoryAuthority(Protocol):
    """Current retained / valid assertions. The index is not this."""

    def current_retained(self, assertion_id: str) -> GroundedAssertion | None:
        """Return the current retained assertion, or None if forgotten/expired/superseded."""
        ...


@dataclass
class InMemoryGovernedMemory:
    """Test/runtime snapshot of current retained assertions.

    Mutating this object simulates vault/inventory changes. Recall never writes it.
    """

    _current: dict[str, GroundedAssertion] = field(default_factory=dict)

    def current_retained(self, assertion_id: str) -> GroundedAssertion | None:
        return self._current.get(assertion_id)

    def put(self, assertion: GroundedAssertion) -> None:
        """Record a currently retained assertion. Not a recall API."""
        self._current[assertion.id] = assertion

    def discard(self, assertion_id: str) -> None:
        """Drop a forgotten / no-longer-current id. Not a recall API."""
        self._current.pop(assertion_id, None)


@dataclass
class InventoryGovernedMemory:
    """Authority = current MemoryInventory ids, payloads from retained assertions."""

    inventory: MemoryInventory
    retained: dict[str, GroundedAssertion]

    def current_retained(self, assertion_id: str) -> GroundedAssertion | None:
        if self.inventory.get(assertion_id) is None:
            return None
        return self.retained.get(assertion_id)


def reduce_retained_assertion(assertion: GroundedAssertion) -> str:
    """Structured meaning for the index — never raw email/chat bodies."""
    return format_memory_claim(assertion.subject, assertion.predicate, assertion.value)


def recall_governed_memory(
    query: str,
    *,
    candidate_index: CandidateAssertionIndex,
    authority: GovernedMemoryAuthority,
    now: datetime | None = None,
    limit: int = 10,
) -> RecallResult:
    """Run the legal pipeline. Embedding hits cannot skip the governed-memory filter.

    This function does not create, promote, resurrect, or retain memory.
    """
    moment = now or datetime.now(tz=UTC)
    stages: list[RecallStage] = []

    stages.append(RecallStage.APPROXIMATE_RETRIEVAL)
    hits = candidate_index.candidate_ids(query, limit=limit)

    stages.append(RecallStage.CANDIDATE_ASSERTION_IDS)
    candidate_ids = tuple(hit.assertion_id for hit in hits)
    scores = {hit.assertion_id: hit.score for hit in hits}

    stages.append(RecallStage.GOVERNED_MEMORY_LOOKUP)
    looked_up = {
        assertion_id: authority.current_retained(assertion_id) for assertion_id in candidate_ids
    }

    stages.append(RecallStage.CURRENT_RETAINED_VALID_CHECK)
    rejected: dict[str, RecallRejection] = {}
    admitted: list[str] = []
    for assertion_id in candidate_ids:
        assertion = looked_up.get(assertion_id)
        if assertion is None:
            rejected[assertion_id] = RecallRejection.NOT_IN_GOVERNED_MEMORY
            continue
        if not assertion.is_usable_now(now=moment):
            rejected[assertion_id] = RecallRejection.NOT_CURRENT
            continue
        admitted.append(assertion_id)

    stages.append(RecallStage.EXPOSE_ASSERTION)
    exposed: list[RecalledAssertion] = []
    for assertion_id in admitted:
        assertion = looked_up[assertion_id]
        if assertion is None:
            continue
        exposed.append(
            RecalledAssertion(
                assertion=assertion,
                candidate_id=assertion_id,
                similarity=scores.get(assertion_id, 0.0),
            )
        )
    return RecallResult(
        query=query,
        stages=tuple(stages),
        candidate_ids=candidate_ids,
        rejected=rejected,
        assertions=tuple(exposed),
    )


__all__ = [
    "CandidateAssertionIndex",
    "CandidateHit",
    "GovernedMemoryAuthority",
    "InMemoryGovernedMemory",
    "InventoryGovernedMemory",
    "RECALL_PIPELINE_ORDER",
    "RecallRejection",
    "RecallResult",
    "RecallStage",
    "RecalledAssertion",
    "recall_governed_memory",
    "reduce_retained_assertion",
]
