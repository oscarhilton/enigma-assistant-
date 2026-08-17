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
    CONTEXT_ONLY = "CONTEXT_ONLY"
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
    valid_from: datetime | None = None
    valid_until: datetime | None = None
    resolution_event: str | None = None
    expected_surface_window: str | None = None

    @field_validator("valid_from", "valid_until", mode="before")
    @classmethod
    def _parse_validity(cls, value: object) -> object:
        if value is None:
            return None
        return _parse_instant(value)

    @model_validator(mode="before")
    @classmethod
    def _sync_window_aliases(cls, data: Any) -> Any:
        if not isinstance(data, dict):
            return data
        attention_raw = data.get("attention")
        attention: dict[str, Any] = (
            dict(attention_raw) if isinstance(attention_raw, dict) else {}
        )
        window_raw = attention.get("window")
        window: dict[str, Any] = (
            dict(window_raw) if isinstance(window_raw, dict) else {}
        )

        valid_from = data.get("valid_from")
        valid_until = data.get("valid_until")
        window_start = window.get("start")
        window_end = window.get("end")

        if valid_from is not None or valid_until is not None:
            if window_start is not None and valid_from is not None and window_start != valid_from:
                raise ValueError("valid_from must match attention.window.start when both are set")
            if window_end is not None and valid_until is not None and window_end != valid_until:
                raise ValueError("valid_until must match attention.window.end when both are set")
            start = valid_from if valid_from is not None else window_start
            end = valid_until if valid_until is not None else window_end
            if start is not None and end is not None:
                attention["window"] = {"start": start, "end": end}
        elif window_start is not None and window_end is not None:
            data["valid_from"] = window_start
            data["valid_until"] = window_end

        if attention:
            data["attention"] = attention
        return data

    @model_validator(mode="after")
    def _populate_validity_from_window(self) -> Self:
        if self.attention.window is None:
            return self
        updates: dict[str, datetime] = {}
        if self.valid_from is None:
            updates["valid_from"] = self.attention.window.start
        if self.valid_until is None:
            updates["valid_until"] = self.attention.window.end
        if updates:
            return self.model_copy(update=updates)
        return self

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


def render_truth_checklist(corpus: SupportContractCorpus) -> str:
    """Human-inspectable markdown table — one row per support-contract arc."""
    lines = [
        "# Alex v1 — support contract truth checklist",
        "",
        "Evaluator-only ground truth for Reasoning Value Gate (R-L01). "
        "One row per arc in `scenarios/alex-v1/ground_truth/support_contracts.yaml`.",
        "",
        "| Scenario | Behaviour | Valid from | Valid until | Resolution event | "
        "Expected surface window | Obligation | Good next actions |",
        "| --- | --- | --- | --- | --- | --- | --- | --- |",
    ]
    for contract in sorted(corpus.contracts, key=lambda c: c.scenario):
        vf = _format_instant(contract.valid_from)
        vu = _format_instant(contract.valid_until)
        resolution = contract.resolution_event or "—"
        surface = (contract.expected_surface_window or "—").replace("|", "\\|")
        obligation = contract.obligation_id or "—"
        actions = ", ".join(contract.support.good_next_actions)
        lines.append(
            f"| {contract.scenario} | {contract.attention.behaviour.value} | "
            f"{vf} | {vu} | {resolution} | {surface} | {obligation} | {actions} |"
        )
    lines.append("")
    return "\n".join(lines)


def _format_instant(value: datetime | None) -> str:
    if value is None:
        return "—"
    return value.astimezone(UTC).strftime("%Y-%m-%dT%H:%MZ")


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
    "render_truth_checklist",
]
