"""Evaluator-only support contracts (Reasoning Value Gate / R01).

Never ingested by Enigma runtime or LLM prompts. See ADR-011 and
docs/architecture/eval-stubs/support_contract.v0.json.
"""

from __future__ import annotations

from datetime import UTC, datetime
from enum import StrEnum
from pathlib import Path
from typing import Any, Literal, Self

import yaml
from pydantic import BaseModel, Field, field_validator, model_validator

from personal_enigma.evaluation.ground_truth import GroundTruthValidationError, _parse_instant


class AttentionBehaviour(StrEnum):
    MUST_SURFACE = "MUST_SURFACE"
    MAY_SURFACE = "MAY_SURFACE"
    MUST_SUPPRESS = "MUST_SUPPRESS"
    MUST_STAY_QUIET = "MUST_STAY_QUIET"


class SupportChallenge(StrEnum):
    PROSPECTIVE_MEMORY = "prospective_memory"
    TASK_INITIATION = "task_initiation"
    AMBIGUITY = "ambiguity"
    TRANSITION_COST = "transition_cost"
    WORKING_MEMORY = "working_memory"
    TIME_ESTIMATION = "time_estimation"
    DISTRACTION = "distraction"
    ADMIN_FRICTION = "admin_friction"
    TASK_DECOMPOSITION = "task_decomposition"
    TIME_BLINDNESS = "time_blindness"
    TRANSITION = "transition"
    INTERRUPTION_RECOVERY = "interruption_recovery"
    BLOCKED_TASK = "blocked_task"
    RECURRENCE = "recurrence"
    ENERGY_MISMATCH = "energy_mismatch"
    SOCIAL_COORDINATION = "social_coordination"
    OVERWHELM = "overwhelm"


class AttentionContractWindow(BaseModel):
    start: datetime
    end: datetime

    @field_validator("start", "end", mode="before")
    @classmethod
    def _parse_times(cls, value: object) -> object:
        return _parse_instant(value)

    @model_validator(mode="after")
    def _check_order(self) -> Self:
        if self.start > self.end:
            raise ValueError("attention window start must be before end")
        return self


class AttentionContract(BaseModel):
    behaviour: AttentionBehaviour
    window: AttentionContractWindow | None = None
    minimum_priority: int | None = Field(default=None, ge=1, le=5)


class PreferredEffort(BaseModel):
    max_minutes: int | None = Field(default=None, ge=1)
    effort: Literal["trivial", "light", "moderate", "heavy"] | None = None


class SupportActions(BaseModel):
    good_next_actions: list[str] = Field(min_length=1)
    acceptable_next_actions: list[str] = Field(default_factory=list)
    poor_actions: list[str] = Field(default_factory=list)
    preferred_effort: PreferredEffort | None = None
    timing_notes: str | None = None


class NextActionExpected(BaseModel):
    title: str
    action_id: str | None = None
    estimated_minutes: int | None = Field(default=None, ge=1)
    effort: Literal["trivial", "light", "moderate", "heavy"] | None = None
    why_this_now: str | None = None


class NextActionCheckpoint(BaseModel):
    at: datetime
    expected: NextActionExpected
    attention_item_id: str | None = None

    @field_validator("at", mode="before")
    @classmethod
    def _parse_at(cls, value: object) -> object:
        return _parse_instant(value)


class SupportContract(BaseModel):
    """One evaluator-only arc or checkpoint contract."""

    scenario: str
    obligation_id: str | None = None
    challenge: list[SupportChallenge] = Field(min_length=1)
    attention: AttentionContract
    support: SupportActions
    next_action_checkpoint: NextActionCheckpoint | None = None
    evidence_ids: list[str] = Field(default_factory=list)

    def is_active_at(self, when: datetime) -> bool:
        if when.tzinfo is None:
            when = when.replace(tzinfo=UTC)
        if self.attention.window is None:
            return True
        return self.attention.window.start <= when <= self.attention.window.end


class SupportContractCorpus(BaseModel):
    contracts: list[SupportContract] = Field(default_factory=list)
    source_paths: list[str] = Field(default_factory=list)

    def by_scenario(self, scenario_id: str) -> SupportContract | None:
        for contract in self.contracts:
            if contract.scenario == scenario_id:
                return contract
        return None

    def active_at(self, when: datetime) -> list[SupportContract]:
        return [c for c in self.contracts if c.is_active_at(when)]


def load_support_contracts(path: str | Path) -> SupportContractCorpus:
    """Load ``support_contracts.yaml`` (or directory of yaml files)."""
    root = Path(path)
    corpus = SupportContractCorpus()

    if root.is_file():
        files = [root]
    elif root.is_dir():
        files = sorted(p for p in root.glob("*.yaml") if p.is_file())
        if (root / "support_contracts.yaml").is_file():
            files = [root / "support_contracts.yaml"]
    else:
        raise GroundTruthValidationError([f"support contract path not found: {root}"])

    errors: list[str] = []
    for file_path in files:
        if not file_path.name.endswith(".yaml"):
            continue
        try:
            raw = yaml.safe_load(file_path.read_text(encoding="utf-8"))
        except yaml.YAMLError as exc:
            errors.append(f"{file_path}: YAML error: {exc}")
            continue
        if raw is None:
            continue
        entries: list[Any]
        if isinstance(raw, dict) and "support_contracts" in raw:
            entries = raw["support_contracts"]
        elif isinstance(raw, dict) and "contracts" in raw:
            entries = raw["contracts"]
        elif isinstance(raw, list):
            entries = raw
        elif isinstance(raw, dict) and "scenario" in raw:
            entries = [raw]
        else:
            errors.append(f"{file_path}: unrecognised support contract document")
            continue
        for index, item in enumerate(entries):
            label = str(file_path) if len(entries) == 1 else f"{file_path}[{index}]"
            try:
                corpus.contracts.append(SupportContract.model_validate(item))
            except Exception as exc:
                errors.append(f"{label}: {exc}")

    if errors:
        raise GroundTruthValidationError(errors)

    dup = _duplicates(c.scenario for c in corpus.contracts)
    if dup:
        raise GroundTruthValidationError(
            [f"duplicate support contract scenario ids: {sorted(dup)}"]
        )

    corpus.source_paths = [str(f) for f in files]
    return corpus


def _duplicates(ids: Any) -> set[str]:
    seen: set[str] = set()
    dups: set[str] = set()
    for item in ids:
        if item in seen:
            dups.add(item)
        else:
            seen.add(item)
    return dups


__all__ = [
    "AttentionBehaviour",
    "AttentionContract",
    "AttentionContractWindow",
    "NextActionCheckpoint",
    "NextActionExpected",
    "PreferredEffort",
    "SupportActions",
    "SupportChallenge",
    "SupportContract",
    "SupportContractCorpus",
    "load_support_contracts",
]
