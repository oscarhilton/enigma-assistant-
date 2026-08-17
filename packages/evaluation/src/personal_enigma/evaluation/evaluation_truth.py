"""Merged evaluator truth: D06 ground truth + support contracts (R01)."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Any

import yaml

from personal_enigma.evaluation.ground_truth import (
    GroundTruthCorpus,
    GroundTruthValidationError,
    SignalTruth,
    load_ground_truth,
)
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


def _merge_canonical_noise_signals(corpus: GroundTruthCorpus, root: Path) -> None:
    """Append spine mail noise labels (evaluator-only, not D08d background noise)."""
    path = root / "canonical_noise_signals.yaml"
    if not path.is_file():
        return
    try:
        raw = yaml.safe_load(path.read_text(encoding="utf-8"))
    except yaml.YAMLError as exc:
        raise GroundTruthValidationError([f"{path}: YAML error: {exc}"]) from exc
    if not isinstance(raw, dict):
        raise GroundTruthValidationError([f"{path}: expected mapping"])
    signals: Any = raw.get("signals")
    if not signals:
        return
    if not isinstance(signals, list):
        raise GroundTruthValidationError([f"{path}: signals must be a list"])
    errors: list[str] = []
    for index, item in enumerate(signals):
        try:
            corpus.signals.append(SignalTruth.model_validate(item))
        except Exception as exc:
            errors.append(f"{path}[{index}]: {exc}")
    if errors:
        raise GroundTruthValidationError(errors)
    corpus.source_paths.append(str(path))


def load_evaluation_truth(path: str | Path) -> EvaluationTruth:
    """Load ground truth directory plus optional ``support_contracts.yaml``."""
    root = Path(path)
    gt = load_ground_truth(root)
    _merge_canonical_noise_signals(gt, root)
    contract_file = root / "support_contracts.yaml"
    contracts = (
        load_support_contracts(contract_file)
        if contract_file.is_file()
        else SupportContractCorpus()
    )
    return EvaluationTruth(ground_truth=gt, support_contracts=contracts)


__all__ = ["EvaluationTruth", "load_evaluation_truth"]
