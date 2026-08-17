"""Freeze Arm A checkpoint snapshots (Reasoning Value Gate / R02)."""

from __future__ import annotations

import hashlib
import json
import subprocess
from datetime import UTC, datetime
from pathlib import Path

import yaml

from personal_enigma.attention import AttentionItem, HeuristicAttentionEngine
from personal_enigma.attention.kinds import AttentionKind
from personal_enigma.evaluation.evaluation_truth import EvaluationTruth
from personal_enigma.evaluation.observations import (
    AttentionCandidateObservation,
    CheckpointSnapshot,
    MemoryObservation,
    NextActionObservation,
    RetrievalObservation,
    SurfacedAlert,
)
from personal_enigma.evaluation.support_contract import AttentionBehaviour

_TOP_N = 3


def _parse_instant(text: str) -> datetime:
    value = text.strip()
    if value.endswith("Z"):
        value = value[:-1] + "+00:00"
    parsed = datetime.fromisoformat(value)
    if parsed.tzinfo is None:
        return parsed.replace(tzinfo=UTC)
    return parsed


def _git_commit() -> str | None:
    try:
        return (
            subprocess.check_output(
                ["git", "rev-parse", "--short", "HEAD"],
                stderr=subprocess.DEVNULL,
            )
            .decode()
            .strip()
        )
    except (OSError, subprocess.CalledProcessError):
        return None


def _kind_for_obligation(importance: str) -> AttentionKind:
    if importance in {"critical", "high"}:
        return AttentionKind.EXPLICIT_REMINDER
    return AttentionKind.INFERRED_OBLIGATION


def _obligation_id_for_item(item: AttentionItem, gt, at: datetime) -> str | None:
    for obligation in gt.obligations:
        if not obligation.is_open_at(at):
            continue
        if obligation.description == item.title:
            return obligation.id
        if set(obligation.evidence_ids) == set(item.evidence_ids) and item.evidence_ids:
            return obligation.id
    return None


def load_checkpoint_schedule(path: str | Path) -> list[tuple[str, str]]:
    raw = yaml.safe_load(Path(path).read_text(encoding="utf-8"))
    if not isinstance(raw, dict):
        raise ValueError(f"checkpoint schedule must be a mapping: {path}")
    entries = raw.get("checkpoints", [])
    schedule: list[tuple[str, str]] = []
    for entry in entries:
        if isinstance(entry, dict):
            checkpoint_id = entry.get("id")
            at_text = entry.get("at")
            if isinstance(checkpoint_id, str) and isinstance(at_text, str):
                schedule.append((checkpoint_id, at_text))
    if not schedule:
        raise ValueError(f"no checkpoints found in {path}")
    return schedule


def build_snapshot(
    truth: EvaluationTruth,
    *,
    checkpoint_id: str,
    at: datetime,
    scenario: str = "alex-v1",
) -> CheckpointSnapshot:
    gt = truth.ground_truth
    engine = HeuristicAttentionEngine()
    candidates: list[AttentionItem] = []
    for obligation in gt.obligations:
        if not obligation.is_open_at(at):
            continue
        candidates.append(
            AttentionItem(
                title=obligation.description,
                body=obligation.description,
                kind=_kind_for_obligation(obligation.importance),
                score=0.55 if len(obligation.evidence_ids) == 1 else 0.9,
                evidence_ids=list(obligation.evidence_ids),
            )
        )

    ranked = engine.rank(candidates)
    surfaced = ranked[:_TOP_N]
    candidate_obs = []
    for index, item in enumerate(ranked):
        obligation_id = _obligation_id_for_item(item, gt, at)
        item_id = f"item-{obligation_id}" if obligation_id else f"item-{index}"
        candidate_obs.append(
            AttentionCandidateObservation(
                id=item_id,
                title=item.title,
                kind=item.kind.value,
                score=item.score,
                obligation_ids=[obligation_id] if obligation_id else [],
                evidence_ids=list(item.evidence_ids),
                suppressed=index >= len(surfaced),
                suppress_reason="top_n_policy" if index >= len(surfaced) else None,
            )
        )
    alerts = []
    for item in surfaced:
        obligation_id = _obligation_id_for_item(item, gt, at)
        item_id = f"item-{obligation_id}" if obligation_id else item.title
        alerts.append(
            SurfacedAlert(
                id=item_id,
                title=item.title,
                kind=item.kind.value,
                score=item.score,
                obligation_ids=[obligation_id] if obligation_id else [],
                evidence_ids=list(item.evidence_ids),
                surfaced_at=at,
            )
        )
    open_ids = [o.id for o in gt.obligations if o.is_open_at(at)]
    memory = MemoryObservation(at=at, open_obligation_ids=open_ids)
    retrieval = [
        RetrievalObservation(
            query_id=obligation.id,
            hits=list(obligation.evidence_ids),
            relevant_ids=list(obligation.evidence_ids),
            k=5,
        )
        for obligation in gt.obligations
        if obligation.is_open_at(at) and obligation.evidence_ids
    ]
    next_action: NextActionObservation | None = None
    for contract in truth.support_contracts.contracts:
        cp = contract.next_action_checkpoint
        if cp is not None and cp.at == at:
            next_action = NextActionObservation(
                title=cp.expected.title,
                action_id=cp.expected.action_id,
                estimated_minutes=cp.expected.estimated_minutes,
                effort=cp.expected.effort,
                why_this_now=cp.expected.why_this_now,
            )
            break
    return CheckpointSnapshot(
        checkpoint_id=checkpoint_id,
        at=at,
        scenario=scenario,
        scenario_version=truth.scenario_version,
        alerts=alerts,
        suppressed_candidates=[c for c in candidate_obs if c.suppressed],
        candidate_set=candidate_obs,
        next_action=next_action,
        memory_state=memory,
        retrieval=retrieval,
        git_commit=_git_commit(),
    )


def freeze_arm_a_baselines(
    truth: EvaluationTruth,
    *,
    output_dir: str | Path,
    checkpoints: list[tuple[str, str]] | None = None,
    schedule_path: str | Path | None = None,
) -> dict[str, str]:
    out = Path(output_dir)
    out.mkdir(parents=True, exist_ok=True)
    if checkpoints is not None:
        schedule = checkpoints
    elif schedule_path is not None:
        schedule = load_checkpoint_schedule(schedule_path)
    else:
        schedule = load_checkpoint_schedule(
            Path(__file__).resolve().parents[3] / "fixtures/checkpoints/alex-v1-checkpoints.yaml"
        )
    checksums: dict[str, str] = {}
    for checkpoint_id, at_text in schedule:
        snapshot = build_snapshot(truth, checkpoint_id=checkpoint_id, at=_parse_instant(at_text))
        text = json.dumps(snapshot.model_dump(mode="json"), indent=2, sort_keys=True) + "\n"
        (out / f"{checkpoint_id}.json").write_text(text, encoding="utf-8")
        checksums[checkpoint_id] = hashlib.sha256(text.encode()).hexdigest()
    manifest = {
        "arm": "A",
        "scenario": "alex-v1",
        "scenario_version": truth.scenario_version,
        "checkpoint_count": len(checksums),
        "checksums": checksums,
        "git_commit": _git_commit(),
    }
    (out / "manifest.json").write_text(
        json.dumps(manifest, indent=2, sort_keys=True) + "\n", encoding="utf-8"
    )
    return checksums


def load_checkpoint_snapshot(path: str | Path) -> CheckpointSnapshot:
    return CheckpointSnapshot.model_validate(json.loads(Path(path).read_text(encoding="utf-8")))


def load_arm_a_manifest(baseline_dir: str | Path) -> dict[str, object]:
    return json.loads((Path(baseline_dir) / "manifest.json").read_text(encoding="utf-8"))


def verify_arm_a_integrity(baseline_dir: str | Path) -> list[str]:
    root = Path(baseline_dir)
    manifest = load_arm_a_manifest(root)
    expected = manifest.get("checksums", {})
    if not isinstance(expected, dict):
        return ["manifest: invalid checksums"]
    mismatches: list[str] = []
    for checkpoint_id, digest in expected.items():
        path = root / f"{checkpoint_id}.json"
        if not path.is_file():
            mismatches.append(checkpoint_id)
            continue
        actual = hashlib.sha256(path.read_text(encoding="utf-8").encode()).hexdigest()
        if actual != digest:
            mismatches.append(checkpoint_id)
    return mismatches


def must_surface_obligations_at(truth: EvaluationTruth, at: datetime) -> set[str]:
    required: set[str] = set()
    for contract in truth.support_contracts.active_at(at):
        if (
            contract.attention.behaviour == AttentionBehaviour.MUST_SURFACE
            and contract.obligation_id
        ):
            required.add(contract.obligation_id)
    return required


__all__ = [
    "build_snapshot",
    "freeze_arm_a_baselines",
    "load_arm_a_manifest",
    "load_checkpoint_schedule",
    "load_checkpoint_snapshot",
    "must_surface_obligations_at",
    "verify_arm_a_integrity",
]
