"""D1 environment separation and real-source invariant tests."""

from __future__ import annotations

from pathlib import Path

import pytest

from personal_enigma.ingestion.bridge_client import AppleBridgeClient
from personal_enigma.ingestion.sources.apple_calendar import AppleCalendarSource
from personal_enigma.ingestion.sources.gmail import GmailSource
from personal_enigma.simulation import (
    DEMO_BANNER_TEXT,
    DemoEnvironment,
    EnvironmentMode,
    RealSourceAccessError,
    SimulationClock,
    SimulationEvent,
    SystemClock,
    assert_source_allowed_for_mode,
    storage_root_for,
)
from personal_enigma.simulation.environment import parse_environment_mode


class _SyntheticStub:
    """Stand-in for a future synthetic adapter (not under ingestion.sources)."""


def test_environment_mode_values() -> None:
    assert EnvironmentMode.DEMO == "demo"
    assert EnvironmentMode.PRIVATE == "private"
    assert parse_environment_mode(None) is EnvironmentMode.PRIVATE
    assert parse_environment_mode("DEMO") is EnvironmentMode.DEMO


def test_storage_roots_are_separated(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.delenv("ENIGMA_PRIVATE_STORAGE_ROOT", raising=False)
    monkeypatch.delenv("ENIGMA_DEMO_STORAGE_ROOT", raising=False)
    monkeypatch.delenv("ENIGMA_HOME", raising=False)

    private = storage_root_for(EnvironmentMode.PRIVATE, home=tmp_path)
    demo = storage_root_for(EnvironmentMode.DEMO, scenario="alex-v1", home=tmp_path)

    assert private == tmp_path / ".enigma" / "private"
    assert demo == tmp_path / ".enigma" / "demo" / "alex-v1"
    assert private != demo
    assert "demo" in demo.parts
    assert "private" in private.parts


def test_storage_roots_honour_env_overrides(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    private_root = tmp_path / "p"
    demo_parent = tmp_path / "d"
    monkeypatch.setenv("ENIGMA_PRIVATE_STORAGE_ROOT", str(private_root))
    monkeypatch.setenv("ENIGMA_DEMO_STORAGE_ROOT", str(demo_parent))

    assert storage_root_for(EnvironmentMode.PRIVATE) == private_root
    assert storage_root_for(EnvironmentMode.DEMO, scenario="alex-v1") == demo_parent / "alex-v1"


def test_demo_storage_requires_scenario(tmp_path: Path) -> None:
    with pytest.raises(ValueError, match="scenario"):
        storage_root_for(EnvironmentMode.DEMO, home=tmp_path)


def test_demo_environment_has_no_real_credentials(tmp_path: Path) -> None:
    env = DemoEnvironment(scenario="alex-v1")
    assert env.mode is EnvironmentMode.DEMO
    assert env.gmail_credentials is None
    assert env.apple_bridge is None
    assert env.banner_text == DEMO_BANNER_TEXT
    assert env.storage_root.name == "alex-v1"


def test_demo_rejects_real_connectors() -> None:
    bridge = AppleBridgeClient(base_url="http://127.0.0.1:8765", token="t")
    sources: list[object] = [
        GmailSource(access_token="x"),
        AppleCalendarSource(client=bridge),
        bridge,
    ]
    env = DemoEnvironment(scenario="alex-v1")
    for source in sources:
        with pytest.raises(RealSourceAccessError, match="IMPOSSIBLE"):
            env.register_source(source)
        with pytest.raises(RealSourceAccessError):
            assert_source_allowed_for_mode(EnvironmentMode.DEMO, source)


def test_demo_allows_non_ingestion_sources() -> None:
    env = DemoEnvironment(scenario="alex-v1")
    env.register_source(_SyntheticStub())
    assert len(env.sources) == 1


def test_private_mode_allows_real_connectors() -> None:
    source = GmailSource(access_token="x")
    assert_source_allowed_for_mode(EnvironmentMode.PRIVATE, source)


def test_clock_and_event_stubs() -> None:
    wall = SystemClock()
    assert wall.now().tzinfo is not None
    sim = SimulationClock()
    before = sim.now()
    from datetime import timedelta

    sim.advance(timedelta(days=1))
    assert sim.now() > before
    event = SimulationEvent(id="e1", at=sim.now(), type="email.receive")
    assert event.id == "e1"
