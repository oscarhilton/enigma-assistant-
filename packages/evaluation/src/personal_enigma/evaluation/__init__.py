"""Demo Mode evaluation package (Phase 2) — runner + ground truth + metrics."""

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
from personal_enigma.evaluation.runner import EvaluationReport, EvaluationRunner

__all__ = [
    "AttentionWindow",
    "CommitmentTruth",
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
