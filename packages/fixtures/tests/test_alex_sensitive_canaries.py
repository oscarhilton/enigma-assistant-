"""Alex synthetic sensitive canary pack — manifest and grep regression."""

from __future__ import annotations

from pathlib import Path

import pytest

from personal_enigma.fixtures.alex_security_canaries import (
    GREP_TARGETS,
    PACK_ID,
    GrepTargetId,
    forbidden_on_wire_sentinels,
    grep_directory_for_sentinels,
    reconstructability_probe_sentinels,
    security_canary_manifest,
)
from personal_enigma.fixtures.alex_sensitive_canaries import (
    ALEX_SENSITIVE_CANARIES,
    ALL_CANARY_SENTINELS,
    assert_canary_pack_complete,
)

_FIXTURES_ROOT = Path(__file__).resolve().parents[1] / "src" / "personal_enigma" / "fixtures"
_CANARY_SOURCE_ROOT = _FIXTURES_ROOT / "data" / "security_canaries"
_SYNTHETIC_MARKER = "FICTIONAL_SYNTHETIC_CANARY_ENIGMA_FIXTURE_ONLY"


def test_canary_pack_complete() -> None:
    assert_canary_pack_complete()
    assert len(ALEX_SENSITIVE_CANARIES) == 7
    assert len(ALL_CANARY_SENTINELS) >= 14


def test_every_canary_carries_synthetic_marker() -> None:
    for canary in ALEX_SENSITIVE_CANARIES:
        assert _SYNTHETIC_MARKER in canary.body_text
        assert canary.synthetic_marker == _SYNTHETIC_MARKER


def test_enhanced_canary_metadata_present() -> None:
    for canary in ALEX_SENSITIVE_CANARIES:
        assert canary.raw_marker
        assert canary.raw_marker in canary.sentinel_strings
        assert canary.forbidden_remote_semantics
    medical = next(c for c in ALEX_SENSITIVE_CANARIES if c.category == "medical")
    assert medical.allowed_shadow_features == ()
    assert "diagnosis" in medical.forbidden_remote_semantics
    work = next(c for c in ALEX_SENSITIVE_CANARIES if c.category == "confidential_work")
    assert "OPEN_WORK_COMMITMENT" in work.allowed_shadow_features
    assert "project_nightingale" in work.forbidden_remote_semantics


def test_security_manifest_matches_canaries() -> None:
    manifest = security_canary_manifest()
    assert len(manifest) == len(ALEX_SENSITIVE_CANARIES)
    assert manifest[0].canary_id.startswith("canary-")
    assert manifest[0].raw_marker
    assert manifest[0].forbidden_remote_semantics


def test_forbidden_and_reconstructability_sentinels_aligned() -> None:
    assert forbidden_on_wire_sentinels() == ALL_CANARY_SENTINELS
    assert reconstructability_probe_sentinels() == ALL_CANARY_SENTINELS


def test_grep_targets_documented() -> None:
    ids = {target.target_id for target in GREP_TARGETS}
    assert ids == {
        GrepTargetId.SOURCE,
        GrepTargetId.REMOTE_EGRESS,
        GrepTargetId.PERSISTENT_SHADOW,
        GrepTargetId.STOLEN_DIRECTORY,
    }
    source = next(t for t in GREP_TARGETS if t.target_id == GrepTargetId.SOURCE)
    shadow = next(t for t in GREP_TARGETS if t.target_id == GrepTargetId.PERSISTENT_SHADOW)
    assert source.must_contain_sentinels is True
    assert shadow.must_contain_sentinels is False


def test_source_grep_finds_sentinels() -> None:
    hits = grep_directory_for_sentinels(_CANARY_SOURCE_ROOT)
    assert hits, "Canary source pack must contain discoverable sentinels"


@pytest.mark.parametrize("sentinel", ALL_CANARY_SENTINELS)
def test_sentinel_grepable_in_fixture_tree(sentinel: str) -> None:
    """Each sentinel must be discoverable in fixture sources for SEC CI assertions."""
    hits = grep_directory_for_sentinels(_FIXTURES_ROOT, sentinels=(sentinel,))
    assert hits, f"Sentinel {sentinel!r} not found under fixtures"


def test_canary_pack_id_stable() -> None:
    assert PACK_ID == "alex-sensitive-canaries-v1"
