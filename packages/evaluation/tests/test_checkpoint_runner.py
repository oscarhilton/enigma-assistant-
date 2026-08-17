"""Tests for Arm A checkpoint snapshot freeze (Reasoning Value Gate / R02)."""

from __future__ import annotations

import hashlib
import json
from datetime import UTC, datetime
from pathlib import Path

import pytest

from personal_enigma.evaluation.checkpoint_runner import (
    build_snapshot,
    freeze_arm_a_baselines,
    load_checkpoint_schedule,
    load_checkpoint_snapshot,
    verify_arm_a_integrity,
)
from personal_enigma.evaluation.evaluation_truth import load_evaluation_truth

REPO_ROOT = Path(__file__).resolve().parents[3]
ALEX_GROUND_TRUTH = REPO_ROOT / "scenarios" / "alex-v1" / "ground_truth"
CHECKPOINTS_YAML = REPO_ROOT / "packages/evaluation/fixtures/checkpoints/alex-v1-checkpoints.yaml"
ARM_A_BASELINE = REPO_ROOT / "packages/evaluation/fixtures/baselines/arm-a"


@pytest.fixture
def evaluation_truth():
    return load_evaluation_truth(ALEX_GROUND_TRUTH)


def test_checkpoint_schedule_has_twenty_instants() -> None:
    schedule = load_checkpoint_schedule(CHECKPOINTS_YAML)
    assert 15 <= len(schedule) <= 25
    assert "cp-2026-01-21T13:30" in {item[0] for item in schedule}


def test_build_snapshot_is_deterministic(evaluation_truth, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr("personal_enigma.evaluation.checkpoint_runner._git_commit", lambda: "test")
    at = datetime(2026, 1, 21, 13, 30, tzinfo=UTC)
    first = build_snapshot(evaluation_truth, checkpoint_id="cp-2026-01-21T13:30", at=at)
    second = build_snapshot(evaluation_truth, checkpoint_id="cp-2026-01-21T13:30", at=at)
    assert json.dumps(first.model_dump(mode="json"), sort_keys=True) == json.dumps(
        second.model_dump(mode="json"), sort_keys=True
    )
    assert first.next_action is not None
    assert first.next_action.action_id == "prepare_token_review"


def test_dual_conflict_checkpoint_surfaces_brunch(
    evaluation_truth, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setattr("personal_enigma.evaluation.checkpoint_runner._git_commit", lambda: "test")
    snapshot = build_snapshot(
        evaluation_truth,
        checkpoint_id="cp-2026-01-21T13:30",
        at=datetime(2026, 1, 21, 13, 30, tzinfo=UTC),
    )
    surfaced = {oid for alert in snapshot.alerts for oid in alert.obligation_ids}
    assert "obligation_brunch_book" in surfaced


def test_arm_a_manifest_integrity() -> None:
    assert verify_arm_a_integrity(ARM_A_BASELINE) == []


def test_frozen_baseline_matches_manifest_checksums() -> None:
    manifest = json.loads((ARM_A_BASELINE / "manifest.json").read_text(encoding="utf-8"))
    for checkpoint_id, expected in manifest["checksums"].items():
        payload = (ARM_A_BASELINE / f"{checkpoint_id}.json").read_text(encoding="utf-8")
        assert hashlib.sha256(payload.encode()).hexdigest() == expected


def test_regenerate_baselines_matches_committed_files(
    evaluation_truth, monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    git_commit = json.loads((ARM_A_BASELINE / "manifest.json").read_text(encoding="utf-8"))[
        "git_commit"
    ]
    monkeypatch.setattr(
        "personal_enigma.evaluation.checkpoint_runner._git_commit", lambda: git_commit
    )
    freeze_arm_a_baselines(evaluation_truth, output_dir=tmp_path, schedule_path=CHECKPOINTS_YAML)
    assert (tmp_path / "manifest.json").read_text(encoding="utf-8") == (
        ARM_A_BASELINE / "manifest.json"
    ).read_text(encoding="utf-8")
    for checkpoint_id, _ in load_checkpoint_schedule(CHECKPOINTS_YAML):
        assert (tmp_path / f"{checkpoint_id}.json").read_text(encoding="utf-8") == (
            ARM_A_BASELINE / f"{checkpoint_id}.json"
        ).read_text(encoding="utf-8")


def test_load_checkpoint_snapshot_round_trip(
    evaluation_truth, monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    monkeypatch.setattr("personal_enigma.evaluation.checkpoint_runner._git_commit", lambda: "test")
    freeze_arm_a_baselines(
        evaluation_truth,
        output_dir=tmp_path,
        checkpoints=[("cp-test", "2026-01-15T09:00:00Z")],
    )
    loaded = load_checkpoint_snapshot(tmp_path / "cp-test.json")
    assert loaded.checkpoint_id == "cp-test"
    assert loaded.scenario_version == "0.2.1"
