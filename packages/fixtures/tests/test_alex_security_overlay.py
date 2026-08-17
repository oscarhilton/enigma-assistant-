"""Alex security overlay — separation from behavioural truth."""

from __future__ import annotations

import pytest

from personal_enigma.fixtures.alex_security_canaries import grep_directory_for_sentinels
from personal_enigma.fixtures.alex_security_overlay import (
    ALEX_SCENARIO_ROOT,
    SECURITY_OVERLAY,
    load_alex_fixture_context,
    load_security_overlay,
    security_profile_enabled,
)
from personal_enigma.fixtures.alex_sensitive_canaries import ALEX_SENSITIVE_CANARIES


def test_default_alex_fixture_load_excludes_canaries() -> None:
    ctx = load_alex_fixture_context(load_security_overlay=False)
    assert ctx.security_overlay == ()
    assert ctx.security_overlay_enabled is False
    assert ctx.scenario_id == "alex-v1"
    assert load_security_overlay(load_security_overlay=False) == ()


def test_security_profile_includes_canaries(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("ENIGMA_SECURITY_PROFILE", "1")
    assert security_profile_enabled() is True
    ctx = load_alex_fixture_context()
    assert ctx.security_overlay_enabled is True
    assert len(ctx.security_overlay) == len(ALEX_SENSITIVE_CANARIES)
    assert load_security_overlay() == ALEX_SENSITIVE_CANARIES


def test_security_overlay_marker_constant() -> None:
    assert SECURITY_OVERLAY == "alex-security-overlay-v1"


def test_alex_behavioural_corpus_excludes_canary_sentinels() -> None:
    """Behavioural timeline must not contain security overlay sentinels."""
    if not ALEX_SCENARIO_ROOT.is_dir():
        pytest.skip("scenarios/alex-v1 not present in checkout")
    hits = grep_directory_for_sentinels(ALEX_SCENARIO_ROOT)
    assert hits == [], f"Canaries leaked into behavioural corpus: {hits[:5]}"


def test_env_profile_off_by_default(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.delenv("ENIGMA_SECURITY_PROFILE", raising=False)
    assert security_profile_enabled() is False
    assert load_security_overlay() == ()
