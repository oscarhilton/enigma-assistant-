"""Demo Mode evaluation package (Phase 2) — runner + metric placeholders."""

from personal_enigma.evaluation.adversarial import (
    ADVERSARIAL_PACK_IDS,
    AdversarialPackReport,
    run_adversarial_pack,
)
from personal_enigma.evaluation.runner import EvaluationReport, EvaluationRunner

__all__ = [
    "ADVERSARIAL_PACK_IDS",
    "AdversarialPackReport",
    "EvaluationReport",
    "EvaluationRunner",
    "run_adversarial_pack",
]
