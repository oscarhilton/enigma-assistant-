"""Smoke tests for Reasoning Value Gate report (R07)."""

from __future__ import annotations

import json
from pathlib import Path

from personal_enigma.evaluation.reasoning_value_gate import (
    collect_reasoning_value_gate_evidence,
    decide_architecture,
    render_gate_report_markdown,
)

REPO = Path(__file__).resolve().parents[3]
GT = REPO / "scenarios" / "alex-v1" / "ground_truth"
BASELINES = Path(__file__).resolve().parents[1] / "fixtures" / "baselines" / "arm-a"


def test_decide_architecture_branches() -> None:
    adopt, _ = decide_architecture(
        {"critical_recall": 0.5, "top3_critical_recall": 0.5, "next_action_fit": 0.5},
        {"critical_recall": 0.9, "top3_critical_recall": 0.9, "next_action_fit": 0.9},
        ablation_delta={"next_action_fit": 0.01},
    )
    assert adopt == "adopt"
    keep, _ = decide_architecture(
        {"critical_recall": 0.9, "top3_critical_recall": 0.9, "next_action_fit": 0.9},
        {"critical_recall": 0.9, "top3_critical_recall": 0.9, "next_action_fit": 0.9},
        ablation_delta={},
    )
    assert keep == "keep_deterministic"


def test_gate_report_smoke(tmp_path: Path) -> None:
    from personal_enigma.evaluation.checkpoint_runner import load_checkpoint_snapshot
    from personal_enigma.evaluation.evaluation_truth import load_evaluation_truth
    from personal_enigma.evaluation.llm_benchmark import (
        score_arm_b,
        snapshot_to_transformed_context,
    )
    from personal_enigma.reasoning import (
        MockPaygTransport,
        PaygReasoningService,
        ReasoningMode,
        RecordingPaygTransport,
    )

    truth = load_evaluation_truth(GT)
    response = json.dumps(
        {
            "attention": {
                "item_id": "item-obligation_december_expenses",
                "behaviour": "surface",
                "priority": 4,
            },
            "next_action": {
                "title": "Gather receipts",
                "estimated_minutes": 5,
                "effort": "light",
                "why_this_now": "Due soon",
            },
        }
    )
    recorder = RecordingPaygTransport(
        MockPaygTransport(response_text=response), scenario="gate-smoke"
    )
    service = PaygReasoningService(mode=ReasoningMode.ENABLED, transport=recorder)
    snap = load_checkpoint_snapshot(BASELINES / "cp-2026-01-14T10:00.json")
    score_arm_b(
        snap,
        truth,
        service=service,
        context=snapshot_to_transformed_context(snap),
    )
    replay = tmp_path / "replay.json"
    recorder.save(replay)

    evidence = collect_reasoning_value_gate_evidence(
        truth,
        baseline_dir=BASELINES,
        replay_fixture=replay,
        checkpoint_ids=["cp-2026-01-14T10:00"],
        repo=REPO,
    )
    md = render_gate_report_markdown(evidence)
    assert "Reasoning Value Gate Report" in md
    assert evidence.architecture_decision in {"adopt", "hybrid", "keep_deterministic"}
