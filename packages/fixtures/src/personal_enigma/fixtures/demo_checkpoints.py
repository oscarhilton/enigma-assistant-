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
    payload = json.loads(path.read_text(encoding="utf-8"))
    semantics = payload.get("semantics") or {}
    return {
        candidate_id: SemanticInput.model_validate(values)
        for candidate_id, values in semantics.items()
    }


def list_demo_checkpoints() -> list[dict[str, str]]:
    rows: list[dict[str, str]] = []
    for checkpoint_id in ALEX_V1_MILESTONE_CHECKPOINTS:
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
    "list_demo_checkpoints",
    "load_checkpoint_snapshot",
    "load_semantic_inputs",
    "semantic_fixture_path",
]
