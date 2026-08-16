"""D3 scenario format validation tests."""

from __future__ import annotations

from pathlib import Path

import pytest

from personal_enigma.simulation.scenario import (
    ScenarioValidationError,
    load_scenario,
    try_load_scenario,
)
from personal_enigma.simulation.scenario_rng import scenario_rng

REPO = Path(__file__).resolve().parents[3]
FEATURE = REPO / "scenarios" / "feature"
ALEX = REPO / "scenarios" / "alex-v1"

FEATURE_SCENARIOS = (
    "commitment-basic",
    "commitment-resolved",
    "calendar-conflict",
    "cross-source-merge",
    "quiet-day",
)


@pytest.mark.parametrize("name", FEATURE_SCENARIOS)
def test_feature_scenarios_load(name: str) -> None:
    pkg = load_scenario(FEATURE / name)
    assert pkg.manifest.id == name
    assert pkg.manifest.status == "feature"
    assert 5 <= len(pkg.events) <= 10
    for event in pkg.events:
        assert "obligation" not in event.payload
        assert "commitment" not in event.payload


def test_alex_scaffold_loads_deterministically() -> None:
    first = load_scenario(ALEX)
    second = load_scenario(ALEX)
    assert first.manifest.id == "alex-v1"
    assert first.manifest.status == "scaffold"
    assert first.persona
    assert first.effective_seed == "alex-v1"
    assert [e.model_dump(mode="json") for e in first.events] == [
        e.model_dump(mode="json") for e in second.events
    ]
    assert first.persona == second.persona
    assert first.rng().random() == second.rng().random()


def test_scenario_rng_is_seeded() -> None:
    a = scenario_rng("alex-v1")
    b = scenario_rng("alex-v1")
    seq_a = [a.random() for _ in range(8)]
    seq_b = [b.random() for _ in range(8)]
    assert seq_a == seq_b
    other = scenario_rng("other")
    seq_other = [other.random() for _ in range(8)]
    assert seq_a != seq_other
    assert scenario_rng("alex-v1").getstate() != scenario_rng("other").getstate()


def test_relative_offsets_resolve() -> None:
    pkg = load_scenario(FEATURE / "commitment-basic")
    nudge = next(e for e in pkg.events if e.id == "cb-mail-nudge")
    assert nudge.at.isoformat().startswith("2026-03-04")


def test_rejects_relative_without_start_at(tmp_path: Path) -> None:
    root = tmp_path / "no-start"
    root.mkdir()
    (root / "scenario.yaml").write_text(
        "id: no-start\nversion: '0'\nevents:\n"
        "  - id: e1\n    at: '+1d'\n"
        "    type: email.receive\n    source: mail\n    payload: {}\n",
        encoding="utf-8",
    )
    result = try_load_scenario(root)
    assert not result.ok
    assert any("requires manifest start_at" in err for err in result.errors)


def test_rejects_directory_id_mismatch(tmp_path: Path) -> None:
    root = tmp_path / "folder-name"
    root.mkdir()
    (root / "scenario.yaml").write_text(
        "id: other-id\nversion: '0'\n",
        encoding="utf-8",
    )
    result = try_load_scenario(root)
    assert not result.ok
    assert any("must match manifest id" in err for err in result.errors)


def test_rejects_invalid_timeline_yaml(tmp_path: Path) -> None:
    root = tmp_path / "bad-yaml"
    root.mkdir()
    (root / "scenario.yaml").write_text("id: bad-yaml\nversion: '0'\n", encoding="utf-8")
    timeline = root / "timeline"
    timeline.mkdir()
    (timeline / "broken.yaml").write_text(":\n  - bad\n", encoding="utf-8")
    result = try_load_scenario(root)
    assert not result.ok
    assert any("timeline/broken.yaml" in err for err in result.errors)


def test_rejects_world_model_payload() -> None:
    result = try_load_scenario(FEATURE / "_invalid_world_model")
    assert not result.ok
    assert any("obligation" in err for err in result.errors)


def test_rejects_missing_manifest() -> None:
    path = REPO / "scenarios" / "_fixtures_invalid" / "missing-manifest"
    with pytest.raises(ScenarioValidationError, match="scenario.yaml"):
        load_scenario(path)


def test_rejects_unknown_event_type(tmp_path: Path) -> None:
    root = tmp_path / "bad-type"
    root.mkdir()
    (root / "scenario.yaml").write_text(
        "id: bad-type\nversion: '0'\nevents:\n"
        "  - id: e1\n    at: '2026-01-01T00:00:00Z'\n"
        "    type: obligation.create\n    source: mail\n    payload: {}\n",
        encoding="utf-8",
    )
    result = try_load_scenario(root)
    assert not result.ok
    assert any("unknown type" in err for err in result.errors)
