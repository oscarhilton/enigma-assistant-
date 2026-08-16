"""Demo Mode evaluation package (Phase 2) — runner, ground truth, metrics.

Ground-truth APIs are developer-only. Never import them into Enigma reasoning,
attention, memory, or the external sanitised surface.
"""

from personal_enigma.evaluation.ground_truth import (
    AttentionWindow,
    CommitmentTruth,
    GroundTruthCorpus,
    GroundTruthValidationError,
    MemoryCheckpoint,
    MissedObligation,
    ObligationTruth,
    detect_missed_obligations,
    load_ground_truth,
)
from personal_enigma.evaluation.observations import EvaluationObservations
from personal_enigma.evaluation.runner import EvaluationReport, EvaluationRunner

__all__ = [
    "AttentionWindow",
    "CommitmentTruth",
    "EvaluationObservations",
    "EvaluationReport",
    "EvaluationRunner",
    "GroundTruthCorpus",
    "GroundTruthValidationError",
    "MemoryCheckpoint",
    "MissedObligation",
    "ObligationTruth",
    "detect_missed_obligations",
    "load_ground_truth",
]
