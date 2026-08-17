"""Merged evaluator truth: D06 ground truth + support contracts (R01)."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

from personal_enigma.evaluation.ground_truth import GroundTruthCorpus, load_ground_truth
from personal_enigma.evaluation.support_contract import (
    SupportContractCorpus,
    load_support_contracts,
)


@dataclass(frozen=True, slots=True)
class EvaluationTruth:
    """Authoritative evaluator inputs for Reasoning Value Gate."""

    ground_truth: GroundTruthCorpus
    support_contracts: SupportContractCorpus

    @property
    def scenario_version(self) -> str:
        return "0.2.1"


def load_evaluation_truth(path: str | Path) -> EvaluationTruth:
    """Load ground truth directory plus optional ``support_contracts.yaml``."""
    root = Path(path)
    gt = load_ground_truth(root)
    contract_file = root / "support_contracts.yaml"
    contracts = (
        load_support_contracts(contract_file)
        if contract_file.is_file()
        else SupportContractCorpus()
    )
    return EvaluationTruth(ground_truth=gt, support_contracts=contracts)


__all__ = ["EvaluationTruth", "load_evaluation_truth"]
