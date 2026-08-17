"""Transform diff diagnostic — raw vs evaluation_transformed_v1 (R-L09)."""

from __future__ import annotations

import json
from dataclasses import dataclass, field
from enum import StrEnum
from pathlib import Path
from typing import Any

from personal_enigma.evaluation.checkpoint_runner import load_checkpoint_snapshot
from personal_enigma.evaluation.evaluation_transformed_v1_frozen import (
    snapshot_to_evaluation_transformed_v1_frozen,
)
from personal_enigma.evaluation.llm_benchmark import (
    snapshot_to_context_dict,
    snapshot_to_full_synthetic_context,
    snapshot_to_production_transformed,
)
from personal_enigma.evaluation.observations import CheckpointSnapshot
from personal_enigma.evaluation.transform_semantic_audit import (
    OfflineTransformGate,
    audit_offline_transform_gate,
)
from personal_enigma.transformation.protocol import TransformedContext


class InformationLossClass(StrEnum):
    ENTITY_IDENTITY = "entity_identity"
    RELATIONSHIP = "relationship"
    TEMPORAL_RELATION = "temporal_relation"
    DEPENDENCY_BLOCKER = "dependency_blocker"
    COMMITMENT_OWNERSHIP = "commitment_ownership"
    RESOLUTION_EVIDENCE = "resolution_evidence"
    ACTIONABILITY_CONTEXT = "actionability_context"
    CAUSAL_RELATION = "causal_relation"


@dataclass
class InformationLoss:
    field_path: str
    loss_class: InformationLossClass
    raw_snippet: str
    transformed_snippet: str
    acceptable: bool
    notes: str = ""

    def as_dict(self) -> dict[str, Any]:
        return {
            "field_path": self.field_path,
            "loss_class": self.loss_class.value,
            "raw_snippet": self.raw_snippet,
            "transformed_snippet": self.transformed_snippet,
            "acceptable": self.acceptable,
            "notes": self.notes,
        }


@dataclass
class TransformDiffReport:
    checkpoint_id: str
    evaluation_transformed_v1: dict[str, Any]
    evaluation_transformed_v2: dict[str, Any]
    full_synthetic: dict[str, Any]
    judge_context: dict[str, Any]
    losses: list[InformationLoss] = field(default_factory=list)
    offline_gate: OfflineTransformGate | None = None
    production_transform_gap: str = (
        "evaluation_transformed_v2 uses DefaultEnigmaTransformer.build_remote_attention_context "
        "(shared with production)."
    )

    def as_dict(self) -> dict[str, Any]:
        return {
            "checkpoint_id": self.checkpoint_id,
            "production_transform_gap": self.production_transform_gap,
            "evaluation_transformed_v1": self.evaluation_transformed_v1,
            "evaluation_transformed_v2": self.evaluation_transformed_v2,
            "full_synthetic": self.full_synthetic,
            "judge_context": self.judge_context,
            "losses": [loss.as_dict() for loss in self.losses],
            "offline_gate": self.offline_gate.as_dict() if self.offline_gate else None,
        }


def _ctx_dict(ctx: TransformedContext) -> dict[str, Any]:
    return ctx.model_dump(mode="json")


def _classify_summary_loss(raw: str, transformed: str) -> list[InformationLoss]:
    losses: list[InformationLoss] = []
    raw_lower = raw.lower()
    trans_lower = transformed.lower()

    for name in ("alex", "elena", "maya", "jordan"):
        if name in raw_lower and name not in trans_lower:
            losses.append(
                InformationLoss(
                    field_path="summary.entities.name",
                    loss_class=InformationLossClass.ENTITY_IDENTITY,
                    raw_snippet=name,
                    transformed_snippet="(pseudonymised or absent)",
                    acceptable=True,
                    notes="Expected identity removal",
                )
            )

    causal_markers = (
        ("waiting for", InformationLossClass.CAUSAL_RELATION),
        ("blocked", InformationLossClass.DEPENDENCY_BLOCKER),
        ("figma link", InformationLossClass.RESOLUTION_EVIDENCE),
        ("unblocked", InformationLossClass.CAUSAL_RELATION),
        ("resolves", InformationLossClass.CAUSAL_RELATION),
        ("due ", InformationLossClass.TEMPORAL_RELATION),
        ("saturday", InformationLossClass.TEMPORAL_RELATION),
    )
    for marker, loss_class in causal_markers:
        if marker in raw_lower and marker not in trans_lower:
            acceptable = loss_class == InformationLossClass.ENTITY_IDENTITY
            losses.append(
                InformationLoss(
                    field_path="summary.semantics",
                    loss_class=loss_class,
                    raw_snippet=marker,
                    transformed_snippet="(absent in evaluation_transformed_v1)",
                    acceptable=acceptable,
                    notes="May harm attention timing if not in relations[]",
                )
            )

    if "people:" in raw_lower and "people:" not in trans_lower:
        losses.append(
            InformationLoss(
                field_path="summary.relationship",
                loss_class=InformationLossClass.RELATIONSHIP,
                raw_snippet="people: ...",
                transformed_snippet="OBLIGATION_* entities only",
                acceptable=True,
                notes="Identity removal expected; check relations[] for causal semantics",
            )
        )

    if not losses and raw != transformed:
        losses.append(
            InformationLoss(
                field_path="summary",
                loss_class=InformationLossClass.ACTIONABILITY_CONTEXT,
                raw_snippet=raw[:120],
                transformed_snippet=transformed[:120],
                acceptable=False,
            )
        )
    return losses


def diff_checkpoint_transform(
    snapshot: CheckpointSnapshot,
) -> TransformDiffReport:
    v1_ctx = snapshot_to_evaluation_transformed_v1_frozen(snapshot)
    v2_ctx = snapshot_to_production_transformed(snapshot)
    full_ctx = snapshot_to_full_synthetic_context(snapshot)
    judge_ctx = snapshot_to_context_dict(snapshot)

    losses = _classify_summary_loss(full_ctx.summary, v1_ctx.summary)
    offline_gate = audit_offline_transform_gate(snapshot, v2_ctx)
    for gap in offline_gate.semantic_gaps:
        if gap.status != "LOST":
            continue
        loss_class = InformationLossClass(gap.gap_class.value)
        losses.append(
            InformationLoss(
                field_path=f"relations.{gap.task_subject}",
                loss_class=loss_class,
                raw_snippet=f"evidence implies {gap.gap_class.value}",
                transformed_snippet="(absent or shallow in relations[])",
                acceptable=False,
                notes=gap.notes,
            )
        )

    return TransformDiffReport(
        checkpoint_id=snapshot.checkpoint_id,
        evaluation_transformed_v1=_ctx_dict(v1_ctx),
        evaluation_transformed_v2=_ctx_dict(v2_ctx),
        full_synthetic=_ctx_dict(full_ctx),
        judge_context=judge_ctx,
        losses=losses,
        offline_gate=offline_gate,
    )


def run_transform_diff(
    *,
    baseline_dir: str | Path,
    checkpoint_ids: list[str],
) -> list[TransformDiffReport]:
    root = Path(baseline_dir)
    reports: list[TransformDiffReport] = []
    for cp_id in checkpoint_ids:
        if cp_id == "cp-prizevault-smoke":
            smoke = (
                Path(__file__).resolve().parents[3]
                / "fixtures"
                / "smoke"
                / "cp-prizevault-smoke.json"
            )
            snap = load_checkpoint_snapshot(smoke)
        else:
            snap = load_checkpoint_snapshot(root / f"{cp_id}.json")
        reports.append(diff_checkpoint_transform(snap))
    return reports


def write_transform_diff_report(
    reports: list[TransformDiffReport],
    *,
    output_path: str | Path,
) -> Path:
    path = Path(output_path)
    path.parent.mkdir(parents=True, exist_ok=True)
    payload = {"checkpoints": [r.as_dict() for r in reports]}
    path.write_text(json.dumps(payload, indent=2) + "\n", encoding="utf-8")
    return path


__all__ = [
    "InformationLoss",
    "InformationLossClass",
    "TransformDiffReport",
    "diff_checkpoint_transform",
    "run_transform_diff",
    "write_transform_diff_report",
]
