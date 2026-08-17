"""Offline transform re-gate (R-L09 Phase 3c).

Sequence:
1. Transform diff + semantic-preservation tests (no LLM)
2. Recommend live hardest-10 only if offline gate checklist passes
"""

from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

from personal_enigma.evaluation.checkpoint_runner import load_checkpoint_snapshot
from personal_enigma.evaluation.llm_benchmark import snapshot_to_production_transformed
from personal_enigma.evaluation.transform_diff import run_transform_diff
from personal_enigma.evaluation.transform_semantic_audit import OfflineTransformGate
from personal_enigma.reasoning.errors import PrivacyGateError
from personal_enigma.reasoning.privacy_gate import assert_remote_safe
from personal_enigma.transformation.semantic_preservation import (
    SemanticPreservationExpectation,
    assert_semantic_preservation,
)


@dataclass
class TransformRegateReport:
    checkpoint_ids: list[str]
    offline_gates: list[OfflineTransformGate] = field(default_factory=list)
    privacy_gate_passed: bool = True
    semantic_preservation_passed: bool = True
    semantic_violations: list[str] = field(default_factory=list)
    unacceptable_loss_count: int = 0
    recommend_live_hardest_10: bool = False
    rationale: str = ""

    def as_dict(self) -> dict[str, Any]:
        return {
            "checkpoint_ids": self.checkpoint_ids,
            "offline_gates": [g.as_dict() for g in self.offline_gates],
            "privacy_gate_passed": self.privacy_gate_passed,
            "semantic_preservation_passed": self.semantic_preservation_passed,
            "semantic_violations": self.semantic_violations,
            "unacceptable_loss_count": self.unacceptable_loss_count,
            "recommend_live_hardest_10": self.recommend_live_hardest_10,
            "rationale": self.rationale,
        }


def run_offline_transform_regate(
    *,
    baseline_dir: str | Path,
    checkpoint_ids: list[str],
) -> TransformRegateReport:
    """Run transform diff + deterministic semantic checks without LLM calls."""
    root = Path(baseline_dir)
    diffs = run_transform_diff(baseline_dir=baseline_dir, checkpoint_ids=checkpoint_ids)
    violations: list[str] = []
    unacceptable = 0
    gates: list[OfflineTransformGate] = []
    privacy_ok = True

    for diff in diffs:
        for loss in diff.losses:
            if not loss.acceptable:
                unacceptable += 1
        if diff.offline_gate is not None:
            gates.append(diff.offline_gate)

        snap_path = root / f"{diff.checkpoint_id}.json"
        if not snap_path.exists():
            continue
        snap = load_checkpoint_snapshot(snap_path)
        ctx = snapshot_to_production_transformed(snap)
        try:
            assert_remote_safe(ctx)
        except PrivacyGateError as exc:
            privacy_ok = False
            violations.append(f"{diff.checkpoint_id}: privacy gate: {exc}")
            continue
        token_blocked = any(
            r.subject == "TASK_TOKEN_AUDIT" and r.type == "BLOCKED_BY" for r in ctx.relations
        )
        result = assert_semantic_preservation(
            ctx,
            SemanticPreservationExpectation(
                must_not_contain=("alex", "elena", "maya", "jordan", "sam", "@", ".com"),
                require_resolved_blockers=("TASK_TOKEN_AUDIT",) if token_blocked else (),
            ),
        )
        if not result.passed:
            violations.extend(f"{diff.checkpoint_id}: {v}" for v in result.violations)

    gates_passed = bool(gates) and all(g.passed for g in gates)
    semantic_ok = not violations
    recommend = gates_passed and semantic_ok and privacy_ok and unacceptable == 0

    if recommend:
        rationale = (
            "Offline gate checklist passed (dependency, resolution, causality) — "
            "eligible for live hardest-10 reasoning check."
        )
    elif not gates_passed:
        failed = [g.checkpoint_id for g in gates if not g.passed]
        rationale = (
            f"Offline gate failed for {failed} — shallow relations; "
            "do not spend live until BLOCKED_BY resolved semantics land."
        )
    elif not semantic_ok:
        rationale = "Semantic preservation failed — fix transform before any live re-gate."
    else:
        rationale = (
            f"{unacceptable} unacceptable information losses remain — "
            "extend relations[] before live re-gate."
        )

    return TransformRegateReport(
        checkpoint_ids=list(checkpoint_ids),
        offline_gates=gates,
        semantic_preservation_passed=semantic_ok,
        privacy_gate_passed=privacy_ok,
        semantic_violations=violations,
        unacceptable_loss_count=unacceptable,
        recommend_live_hardest_10=recommend,
        rationale=rationale,
    )


__all__ = [
    "TransformRegateReport",
    "run_offline_transform_regate",
]
