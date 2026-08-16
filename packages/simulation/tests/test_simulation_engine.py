"""D5 simulation engine tests."""

from __future__ import annotations

from pathlib import Path

import pytest

from personal_enigma.simulation import SimulationClock, load_scenario
from personal_enigma.simulation.engine import SimulationEngine

REPO = Path(__file__).resolve().parents[3]
FEATURE = REPO / "scenarios" / "feature" / "commitment-basic"


def test_advance_one_and_day(tmp_path: Path) -> None:
    engine = SimulationEngine.from_scenario(FEATURE, home=tmp_path)
    assert engine.storage_root.parts[-2] == "demo"
    first = engine.advance_one_event()
    assert first is not None
    assert first.id == engine.emitted[0].id
    before = len(engine.emitted)
    engine.advance_day()
    assert len(engine.emitted) >= before


def test_batch_run_deterministic(tmp_path: Path) -> None:
    a = SimulationEngine.from_scenario(FEATURE, home=tmp_path / "a")
    b = SimulationEngine.from_scenario(
        FEATURE,
        home=tmp_path / "b",
        clock=SimulationClock(initial=a.clock.now()),
    )
    a.run_batch()
    b.run_batch()
    assert a.fingerprint() == b.fingerprint()
    assert a.fingerprint()
    assert len(a.fingerprint()) == len(a.package.events)


def test_reset_clears_demo_storage_only(tmp_path: Path) -> None:
    private = tmp_path / ".enigma" / "private"
    private.mkdir(parents=True)
    (private / "keep.txt").write_text("safe", encoding="utf-8")
    engine = SimulationEngine.from_scenario(FEATURE, home=tmp_path)
    engine.run_batch()
    marker = engine.storage_root / "state" / "engine.json"
    assert marker.is_file()
    engine.reset()
    assert (engine.storage_root / "state" / "engine.json").is_file()
    assert engine.emitted == []
    assert len(engine.pending) == len(engine.package.events)
    assert (private / "keep.txt").read_text(encoding="utf-8") == "safe"


def test_rejects_private_storage_root(tmp_path: Path) -> None:
    package = load_scenario(FEATURE)
    private = tmp_path / ".enigma" / "private" / package.manifest.id
    private.mkdir(parents=True)
    with pytest.raises(ValueError, match="not Private"):
        SimulationEngine(
            package=package,
            clock=SimulationClock(),
            storage_root=private,
        )


def test_rejects_non_scenario_named_root(tmp_path: Path) -> None:
    package = load_scenario(FEATURE)
    bad = tmp_path / ".enigma" / "demo" / "wrong-id"
    bad.mkdir(parents=True)
    with pytest.raises(ValueError, match="per-scenario"):
        SimulationEngine(
            package=package,
            clock=SimulationClock(),
            storage_root=bad,
        )
