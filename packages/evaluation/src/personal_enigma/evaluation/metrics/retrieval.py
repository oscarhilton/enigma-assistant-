"""Retrieval metrics (stub recall@k with optional real observation wiring)."""

from __future__ import annotations

from dataclasses import dataclass

from personal_enigma.evaluation.observations import RetrievalObservation


@dataclass(frozen=True, slots=True)
class RetrievalMetrics:
    recall_at_k: float
    mean_recall_at_k: float
    queries: int

    def as_dict(self) -> dict[str, float | int]:
        return {
            "recall_at_k": self.recall_at_k,
            "mean_recall_at_k": self.mean_recall_at_k,
            "queries": self.queries,
        }


def recall_at_k(*, hits: int, k: int) -> float:
    """Stub retrieval recall@k (hits among top-k / k)."""
    if k <= 0:
        return 0.0
    return hits / k


def compute_retrieval_metrics(
    observations: list[RetrievalObservation],
) -> RetrievalMetrics:
    if not observations:
        return RetrievalMetrics(recall_at_k=1.0, mean_recall_at_k=1.0, queries=0)

    scores: list[float] = []
    for obs in observations:
        relevant = set(obs.relevant_ids)
        if not relevant:
            scores.append(1.0)
            continue
        top = obs.hits[: obs.k]
        hit_count = sum(1 for h in top if h in relevant)
        scores.append(recall_at_k(hits=hit_count, k=obs.k) if obs.k else 0.0)

    mean = sum(scores) / len(scores)
    return RetrievalMetrics(
        recall_at_k=mean,
        mean_recall_at_k=mean,
        queries=len(observations),
    )


__all__ = [
    "RetrievalMetrics",
    "compute_retrieval_metrics",
    "recall_at_k",
]
