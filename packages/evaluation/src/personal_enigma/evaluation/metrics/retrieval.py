"""Retrieval metrics (stub recall@k with optional real observation wiring)."""

from __future__ import annotations

from collections.abc import Sequence
from dataclasses import dataclass

from personal_enigma.evaluation.observations import RetrievalObservation


@dataclass(frozen=True, slots=True)
class RetrievalMetrics:
    recall_at_k: float
    mean_recall_at_k: float
    canonical_evidence_recall_at_k: float
    precision_at_k: float
    queries: int

    def as_dict(self) -> dict[str, float | int]:
        return {
            "recall_at_k": self.recall_at_k,
            "mean_recall_at_k": self.mean_recall_at_k,
            "canonical_evidence_recall_at_k": self.canonical_evidence_recall_at_k,
            "precision_at_k": self.precision_at_k,
            "queries": self.queries,
        }


def recall_at_k(*, hits: int, k: int) -> float:
    """Legacy stub: hits among top-k divided by k (precision-shaped)."""
    if k <= 0:
        return 0.0
    return hits / k


def canonical_evidence_recall_at_k(
    *,
    retrieved_ids: Sequence[str],
    relevant_ids: Sequence[str],
    k: int,
) -> float:
    """Fraction of canonical/relevant evidence present in the top-k hits."""
    relevant = set(relevant_ids)
    if not relevant:
        return 1.0
    if k <= 0:
        return 0.0
    top = set(retrieved_ids[:k])
    return len(top & relevant) / len(relevant)


def precision_at_k(
    *,
    retrieved_ids: Sequence[str],
    relevant_ids: Sequence[str],
    k: int,
) -> float:
    """Fraction of top-k hits that are relevant (pollution resistance)."""
    if k <= 0:
        return 0.0
    top = list(retrieved_ids[:k])
    if not top:
        return 1.0
    relevant = set(relevant_ids)
    return sum(1 for h in top if h in relevant) / len(top)


def compute_retrieval_metrics(
    observations: list[RetrievalObservation],
) -> RetrievalMetrics:
    if not observations:
        return RetrievalMetrics(
            recall_at_k=1.0,
            mean_recall_at_k=1.0,
            canonical_evidence_recall_at_k=1.0,
            precision_at_k=1.0,
            queries=0,
        )

    legacy: list[float] = []
    canonical: list[float] = []
    precision: list[float] = []
    for obs in observations:
        relevant = set(obs.relevant_ids)
        top = obs.hits[: obs.k]
        if not relevant:
            legacy.append(1.0)
            canonical.append(1.0)
            precision.append(1.0)
            continue
        hit_count = sum(1 for h in top if h in relevant)
        legacy.append(recall_at_k(hits=hit_count, k=obs.k) if obs.k else 0.0)
        canonical.append(
            canonical_evidence_recall_at_k(
                retrieved_ids=obs.hits,
                relevant_ids=obs.relevant_ids,
                k=obs.k,
            )
        )
        precision.append(
            precision_at_k(
                retrieved_ids=obs.hits,
                relevant_ids=obs.relevant_ids,
                k=obs.k,
            )
        )

    mean_legacy = sum(legacy) / len(legacy)
    return RetrievalMetrics(
        recall_at_k=mean_legacy,
        mean_recall_at_k=mean_legacy,
        canonical_evidence_recall_at_k=sum(canonical) / len(canonical),
        precision_at_k=sum(precision) / len(precision),
        queries=len(observations),
    )


__all__ = [
    "RetrievalMetrics",
    "canonical_evidence_recall_at_k",
    "compute_retrieval_metrics",
    "precision_at_k",
    "recall_at_k",
]
