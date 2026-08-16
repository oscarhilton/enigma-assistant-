"""Demo Mode evaluation package (Phase 2) — runner, ground truth, metrics.

Ground-truth APIs are developer-only. Never import them into Enigma reasoning,
attention, memory, or the external sanitised surface.
"""

from personal_enigma.evaluation.ab_eval import (
    StorylineRecallAB,
    compare_storyline_ab,
    storyline_recall_under_noise,
)
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
    SignalTruth,
    detect_missed_obligations,
    load_ground_truth,
)
from personal_enigma.evaluation.metrics.suppression import (
    MAX_BACKGROUND_FALSE_ALERTS_PER_1000,
    BackgroundFalseAlertRate,
    background_false_alerts_per_1000,
    quiet_day_attention_empty,
)
from personal_enigma.evaluation.observations import EvaluationObservations, SurfacedAlert
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
    "BackgroundFalseAlertRate",
    "CommitmentTruth",
    "EvaluationObservations",
    "EvaluationReport",
    "EvaluationRunner",
    "GroundTruthCorpus",
    "GroundTruthValidationError",
    "MAX_BACKGROUND_FALSE_ALERTS_PER_1000",
    "MemoryCheckpoint",
    "MissedObligation",
    "ObligationTruth",
    "ReplayMismatchPolicy",
    "ReplayPaygTransport",
    "ScenarioSignalClass",
    "SignalTruth",
    "StorylineRecallAB",
    "SurfacedAlert",
    "background_false_alerts_per_1000",
    "compare_storyline_ab",
    "default_replay_fixture_path",
    "detect_missed_obligations",
    "load_ground_truth",
    "load_recording_store",
    "quiet_day_attention_empty",
    "run_adversarial_pack",
    "storyline_recall_under_noise",
]
