"""Demo checkpoint paths — shared by simulation, Demo API, and evaluation parity."""

from __future__ import annotations

import json
from functools import lru_cache
from pathlib import Path

from personal_enigma.attention.projection import SemanticInput
from personal_enigma.attention.snapshot import CheckpointSnapshot

_FIXTURES_PKG = Path(__file__).resolve().parent
_DATA_ROOT = _FIXTURES_PKG / "data" / "demo"
_REPO_ROOT = Path(__file__).resolve().parents[5]

ALEX_V1_MILESTONE_CHECKPOINTS: tuple[str, ...] = (
    "cp-2026-01-19T10:00",
    "cp-2026-01-20T11:00",
)

DEFAULT_DEMO_CHECKPOINT = ALEX_V1_MILESTONE_CHECKPOINTS[0]


def arm_a_baseline_path(checkpoint_id: str) -> Path:
    return (
        _REPO_ROOT
        / "packages"
        / "evaluation"
        / "fixtures"
        / "baselines"
        / "arm-a"
        / f"{checkpoint_id}.json"
    )


def semantic_fixture_path(checkpoint_id: str) -> Path:
    return _DATA_ROOT / "semantic" / f"{checkpoint_id}.json"


@lru_cache(maxsize=16)
def load_checkpoint_snapshot(checkpoint_id: str) -> CheckpointSnapshot:
    path = arm_a_baseline_path(checkpoint_id)
    payload = json.loads(path.read_text(encoding="utf-8"))
    return CheckpointSnapshot.model_validate(payload)


def load_semantic_inputs(checkpoint_id: str) -> dict[str, SemanticInput]:
    path = semantic_fixture_path(checkpoint_id)
    if not path.is_file():
        return {}
    payload = json.loads(path.read_text(encoding="utf-8"))
    semantics = payload.get("semantics") or {}
    return {
        candidate_id: SemanticInput.model_validate(values)
        for candidate_id, values in semantics.items()
    }


def bootstrap_semantic_inputs(snapshot: CheckpointSnapshot) -> dict[str, SemanticInput]:
    """Demo fallback when curated judge semantics are absent (non-milestone checkpoints).

    Derives coarse SemanticInput values from arm-a candidate scores so timeline
    jumps show plausible attention before full B2 semantics land for every day.
    """
    active = sorted(
        (candidate for candidate in snapshot.candidate_set if not candidate.suppressed),
        key=lambda candidate: (-candidate.score, candidate.id),
    )
    is_weekend = snapshot.at.weekday() >= 5
    semantics: dict[str, SemanticInput] = {}
    for index, candidate in enumerate(active):
        high_score = candidate.score >= 100.0
        if is_weekend:
            # Restful-weekend policy suppresses unless both urgency bars clear.
            time_sensitivity = 0.93
            actionability_now = 0.93 if index == 0 else 0.92
        elif high_score and index == 0:
            time_sensitivity = 0.55
            actionability_now = 0.5
        else:
            time_sensitivity = 0.35
            actionability_now = (
                0.85
                if "token" in candidate.id
                else 0.7
                if not high_score
                else 0.5
            )
        semantics[candidate.id] = SemanticInput(
            obligation_strength=0.85 if high_score else 0.7,
            user_responsibility=0.85 if high_score else 0.8,
            importance=0.7 if high_score else 0.5,
            time_sensitivity=time_sensitivity,
            actionability_now=actionability_now,
            confidence=0.95,
            reason_codes=["DEMO_BOOTSTRAP"],
        )
    return semantics


def resolve_semantic_inputs(
    checkpoint_id: str,
    snapshot: CheckpointSnapshot,
) -> dict[str, SemanticInput]:
    curated = load_semantic_inputs(checkpoint_id)
    if curated:
        return curated
    return bootstrap_semantic_inputs(snapshot)


def _alex_v1_checkpoint_ids() -> list[str]:
    baseline_dir = _REPO_ROOT / "packages" / "evaluation" / "fixtures" / "baselines" / "arm-a"
    return sorted(path.stem for path in baseline_dir.glob("cp-*.json"))


def list_demo_checkpoints() -> list[dict[str, str]]:
    rows: list[dict[str, str]] = []
    for checkpoint_id in _alex_v1_checkpoint_ids():
        snapshot = load_checkpoint_snapshot(checkpoint_id)
        rows.append(
            {
                "id": checkpoint_id,
                "at": snapshot.at.isoformat(),
                "label": snapshot.at.strftime("%b %d · %H:%M"),
            }
        )
    return rows


__all__ = [
    "ALEX_V1_MILESTONE_CHECKPOINTS",
    "DEFAULT_DEMO_CHECKPOINT",
    "arm_a_baseline_path",
    "bootstrap_semantic_inputs",
    "list_demo_checkpoints",
    "load_checkpoint_snapshot",
    "load_semantic_inputs",
    "resolve_semantic_inputs",
    "semantic_fixture_path",
]
