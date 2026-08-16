"""Demo Mode evaluation package (Phase 2) — runner, ground truth, metrics.

Ground-truth APIs are developer-only. Never import them into Enigma reasoning,
attention, memory, or the external sanitised surface.
"""

from personal_enigma.evaluation.adversarial import (
    ADVERSARIAL_PACK_IDS,
    AdversarialPackReport,
    run_adversarial_pack,
)
from personal_enigma.evaluation.ground_truth import (
    AttentionWindow,
    CommitmentTruth,
    GroundTruthCorpus,
    GroundTruthValidationError,
    MemoryCheckpoint,
    MissedObligation,
    ObligationTruth,
    ScenarioSignalClass,
    detect_missed_obligations,
    load_ground_truth,
)
from personal_enigma.evaluation.observations import EvaluationObservations
from personal_enigma.evaluation.replay import (
    ReplayMismatchPolicy,
    ReplayPaygTransport,
    default_replay_fixture_path,
    load_recording_store,
)
from personal_enigma.evaluation.runner import EvaluationReport, EvaluationRunner

__all__ = [
    "ADVERSARIAL_PACK_IDS",
    "AdversarialPackReport",
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
    "ReplayMismatchPolicy",
    "ReplayPaygTransport",
    "ScenarioSignalClass",
    "default_replay_fixture_path",
    "detect_missed_obligations",
    "load_ground_truth",
    "load_recording_store",
    "run_adversarial_pack",
]
