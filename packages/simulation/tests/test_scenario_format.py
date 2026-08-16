"""D3 scenario format validation tests."""

from __future__ import annotations

from pathlib import Path

import pytest

from personal_enigma.simulation.scenario import (
    ScenarioValidationError,
    load_scenario,
    try_load_scenario,
)

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


def test_alex_scaffold_loads() -> None:
    pkg = load_scenario(ALEX)
    assert pkg.manifest.id == "alex-v1"
    assert pkg.manifest.status == "scaffold"
    assert pkg.persona


def test_relative_offsets_resolve() -> None:
    pkg = load_scenario(FEATURE / "commitment-basic")
    nudge = next(e for e in pkg.events if e.id == "cb-mail-nudge")
    assert nudge.at.isoformat().startswith("2026-03-04")


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
