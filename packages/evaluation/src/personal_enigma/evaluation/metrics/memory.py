"""Memory metrics for Demo Mode evaluation (checkpoint hit rate)."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime

from personal_enigma.evaluation.ground_truth import GroundTruthCorpus, MemoryCheckpoint
from personal_enigma.evaluation.observations import MemoryObservation


@dataclass(frozen=True, slots=True)
class MemoryMetrics:
    checkpoint_hit_rate: float
    checkpoints_evaluated: int
    hits: int
    unsupported: int
    stale: int

    def as_dict(self) -> dict[str, float | int]:
        return {
            "checkpoint_hit_rate": self.checkpoint_hit_rate,
            "checkpoints_evaluated": self.checkpoints_evaluated,
            "hits": self.hits,
            "unsupported": self.unsupported,
            "stale": self.stale,
        }


def checkpoint_hit_rate(*, hits: int, total: int) -> float:
    """Stub memory-checkpoint hit rate."""
    if total <= 0:
        return 1.0
    return hits / total


def _observation_near(
    observations: list[MemoryObservation],
    checkpoint: MemoryCheckpoint,
) -> MemoryObservation | None:
    if not observations:
        return None
    # Prefer exact-at match; otherwise latest observation at or before checkpoint.
    best: MemoryObservation | None = None
    for obs in observations:
        if obs.at is None:
            if best is None:
                best = obs
            continue
        if obs.at == checkpoint.at:
            return obs
        if obs.at <= checkpoint.at and (best is None or best.at is None or obs.at > best.at):
            best = obs
    return best


def compute_memory_metrics(
    truth: GroundTruthCorpus,
    observations: list[MemoryObservation],
    *,
    at: datetime | None = None,
) -> MemoryMetrics:
    """Compare observed memories to ground-truth checkpoints (substring match)."""
    checkpoints = truth.memory_checkpoints
    if at is not None:
        checkpoints = [c for c in checkpoints if c.at <= at]

    hits = 0
    expected = 0
    unsupported = 0
    for checkpoint in checkpoints:
        obs = _observation_near(observations, checkpoint)
        corpus_text = " ".join(obs.texts if obs else []).lower()
        corpus_ids = set(obs.memory_ids if obs else [])
        for expected_mem in checkpoint.expected_memories:
            expected += 1
            needle = expected_mem.lower()
            if needle in corpus_text or expected_mem in corpus_ids:
                hits += 1
            else:
                unsupported += 1

    # Stale stub: memories present with no supporting checkpoint expectation
    expected_set = {
        m.lower() for c in checkpoints for m in c.expected_memories
    }
    stale = 0
    for obs in observations:
        for text in obs.texts:
            if text.lower() not in expected_set and text not in {
                m for c in checkpoints for m in c.expected_memories
            }:
                stale += 1

    return MemoryMetrics(
        checkpoint_hit_rate=checkpoint_hit_rate(hits=hits, total=expected),
        checkpoints_evaluated=len(checkpoints),
        hits=hits,
        unsupported=unsupported,
        stale=stale,
    )


__all__ = [
    "MemoryMetrics",
    "checkpoint_hit_rate",
    "compute_memory_metrics",
]
