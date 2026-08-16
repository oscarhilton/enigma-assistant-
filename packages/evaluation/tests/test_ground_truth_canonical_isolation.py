"""F-background-canonical-isolation — evaluation-side GroundTruth path isolation."""

from __future__ import annotations

from pathlib import Path

from personal_enigma.evaluation import ScenarioSignalClass, load_ground_truth
from personal_enigma.simulation.scenario import load_scenario

REPO = Path(__file__).resolve().parents[3]
FEATURE = REPO / "scenarios" / "feature" / "background-canonical-isolation"


def test_isolation_ground_truth_loads_without_touching_mail_payloads() -> None:
    pkg = load_scenario(FEATURE)
    gt_root = FEATURE / "ground_truth"
    assert gt_root.is_dir()
    assert (FEATURE / "scenario.yaml").is_file()
    # Ground-truth store is a sibling directory of scenario.yaml, never an ingest input.
    assert gt_root.parent == pkg.root
    assert "ground_truth" not in {e.source for e in pkg.events}

    truth = load_ground_truth(gt_root)
    assert truth.signals_for_class(ScenarioSignalClass.CANONICAL)
    assert truth.signals_for_class(ScenarioSignalClass.BACKGROUND)
    assert (gt_root / "background_signals.yaml").is_file()

    for event in pkg.events:
        assert "signal_class" not in event.payload
        assert "expected_attention" not in event.payload
