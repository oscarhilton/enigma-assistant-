"""D8 Alex corpus load + determinism smoke tests."""

from __future__ import annotations

from pathlib import Path

from personal_enigma.simulation import SimulationEngine, load_scenario

REPO = Path(__file__).resolve().parents[3]
ALEX = REPO / "scenarios" / "alex-v1"


def test_alex_v1_loads_three_weeks() -> None:
    pkg = load_scenario(ALEX)
    assert pkg.manifest.id == "alex-v1"
    assert pkg.manifest.status == "benchmark"
    assert pkg.manifest.version == "0.2.0"
    assert len(pkg.events) >= 40
    sources = {e.source for e in pkg.events}
    assert sources >= {"mail", "calendar", "reminders", "notes", "contacts"}
    assert (ALEX / "ground_truth" / "obligations.yaml").is_file()
    assert (ALEX / "entities" / "contacts.yaml").is_file()


def test_alex_v1_replay_deterministic(tmp_path: Path) -> None:
    a = SimulationEngine.from_scenario(ALEX, home=tmp_path / "a")
    b = SimulationEngine.from_scenario(ALEX, home=tmp_path / "b")
    a.run_batch()
    b.run_batch()
    assert a.fingerprint() == b.fingerprint()
    assert len(a.fingerprint()) == len(a.package.events)
