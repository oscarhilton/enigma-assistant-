"""D12 product-demo scenario smoke tests."""

from __future__ import annotations

from pathlib import Path

from personal_enigma.evaluation.ground_truth import load_ground_truth
from personal_enigma.simulation import SimulationEngine, load_scenario

REPO = Path(__file__).resolve().parents[3]
PRODUCT = REPO / "scenarios" / "product-demo"


def test_product_demo_loads_and_replays(tmp_path: Path) -> None:
    pkg = load_scenario(PRODUCT)
    assert pkg.manifest.id == "product-demo"
    assert pkg.manifest.status == "product-demo"
    assert len(pkg.events) >= 10
    engine = SimulationEngine.from_scenario(PRODUCT, home=tmp_path)
    engine.run_batch()
    assert len(engine.fingerprint()) == len(pkg.events)
    truth = load_ground_truth(PRODUCT / "ground_truth")
    assert truth.obligation_by_id("obligation_empty_states") is not None
    assert truth.window_for("obligation_empty_states") is not None
