"""P01 world isolation — Alex Lab vs My Enigma never share storage or HMAC keys."""

from __future__ import annotations

from datetime import UTC, datetime
from pathlib import Path

import pytest

from personal_enigma.ingestion.sources.gmail import GmailSource
from personal_enigma.simulation import (
    RealSourceAccessError,
    SimulationClock,
    SystemClock,
    WorldId,
    WorldIsolationError,
    WorldRegistry,
    parse_world_id,
)
from personal_enigma.simulation.worlds import (
    assert_private_storage_root,
    hmac_key_path,
    person_token_for,
)


def test_parse_world_id_aliases() -> None:
    assert parse_world_id("alex_lab") is WorldId.ALEX_LAB
    assert parse_world_id("My Enigma") is WorldId.MY_ENIGMA
    assert parse_world_id("demo") is WorldId.ALEX_LAB
    assert parse_world_id("private") is WorldId.MY_ENIGMA
    with pytest.raises(ValueError, match="Unknown world"):
        parse_world_id("shadow")


def test_worlds_are_isolated(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.delenv("ENIGMA_PRIVATE_STORAGE_ROOT", raising=False)
    monkeypatch.delenv("ENIGMA_DEMO_STORAGE_ROOT", raising=False)
    monkeypatch.delenv("ENIGMA_HOME", raising=False)
    registry = WorldRegistry(home=tmp_path)
    alex = registry.handle(WorldId.ALEX_LAB)
    mine = registry.handle(WorldId.MY_ENIGMA)

    assert alex.storage_root == tmp_path / ".enigma" / "demo" / "alex-v1"
    assert mine.storage_root == tmp_path / ".enigma" / "private"
    assert alex.storage_root != mine.storage_root
    assert alex.database_path != mine.database_path
    assert alex.hmac_fingerprint != mine.hmac_fingerprint
    assert "PRIVATE_HMAC_KEY" not in alex.environment.secrets
    assert "PRIVATE_HMAC_KEY" in mine.environment.secrets
    assert "DEMO_HMAC_KEY" in alex.environment.secrets

    sample = "maya@example.com"
    assert person_token_for(alex.hmac_key, sample) != person_token_for(
        mine.hmac_key, sample
    )
    assert person_token_for(alex.hmac_key, sample).startswith("PERSON_")
    registry.assert_isolated(require_keys=True)


def test_clock_source_differs(tmp_path: Path) -> None:
    registry = WorldRegistry(home=tmp_path)
    assert isinstance(registry.handle(WorldId.ALEX_LAB).clock, SimulationClock)
    assert isinstance(registry.handle(WorldId.MY_ENIGMA).clock, SystemClock)
    assert registry.handle(WorldId.ALEX_LAB).clock_kind == "simulation"
    assert registry.handle(WorldId.MY_ENIGMA).clock_kind == "system"


def test_switch_does_not_copy_keys_or_storage(tmp_path: Path) -> None:
    registry = WorldRegistry(home=tmp_path)
    alex = registry.switch(WorldId.ALEX_LAB)
    alex_fp = alex.hmac_fingerprint
    alex_root = alex.storage_root
    marker = alex_root / "state" / "alex-only.txt"
    marker.parent.mkdir(parents=True, exist_ok=True)
    marker.write_text("alex", encoding="utf-8")

    mine = registry.switch(WorldId.MY_ENIGMA)
    assert mine.world is WorldId.MY_ENIGMA
    assert mine.hmac_fingerprint != alex_fp
    assert mine.storage_root != alex_root
    assert not (mine.storage_root / "state" / "alex-only.txt").exists()
    assert marker.read_text(encoding="utf-8") == "alex"

    back = registry.switch(WorldId.ALEX_LAB)
    assert back.hmac_fingerprint == alex_fp
    assert marker.exists()


def test_alex_reset_does_not_touch_my_enigma(tmp_path: Path) -> None:
    registry = WorldRegistry(home=tmp_path)
    mine = registry.handle(WorldId.MY_ENIGMA)
    keep = mine.storage_root / "keep-private.txt"
    keep.parent.mkdir(parents=True, exist_ok=True)
    keep.write_text("private-safe", encoding="utf-8")
    private_fp = mine.hmac_fingerprint

    alex = registry.handle(WorldId.ALEX_LAB)
    junk = alex.storage_root / "stale.json"
    junk.parent.mkdir(parents=True, exist_ok=True)
    junk.write_text('{"dirty": true}', encoding="utf-8")
    old_alex_fp = alex.hmac_fingerprint

    registry.reset(WorldId.ALEX_LAB)
    assert not junk.exists()
    assert keep.read_text(encoding="utf-8") == "private-safe"
    assert registry.handle(WorldId.MY_ENIGMA).hmac_fingerprint == private_fp
    assert registry.handle(WorldId.ALEX_LAB).hmac_fingerprint != old_alex_fp
    assert hmac_key_path(mine.storage_root).is_file()


def test_my_enigma_reset_is_refused(tmp_path: Path) -> None:
    registry = WorldRegistry(home=tmp_path)
    keep = registry.handle(WorldId.MY_ENIGMA).storage_root / "keep.txt"
    keep.parent.mkdir(parents=True, exist_ok=True)
    keep.write_text("stay", encoding="utf-8")
    with pytest.raises(WorldIsolationError, match="persistent"):
        registry.reset(WorldId.MY_ENIGMA)
    assert keep.read_text(encoding="utf-8") == "stay"


def test_alex_lab_refuses_real_sources(tmp_path: Path) -> None:
    registry = WorldRegistry(home=tmp_path)
    alex = registry.handle(WorldId.ALEX_LAB)
    with pytest.raises(RealSourceAccessError, match="IMPOSSIBLE"):
        alex.environment.register_source(GmailSource(access_token="x"))
    mine = registry.handle(WorldId.MY_ENIGMA)
    mine.environment.register_source(GmailSource(access_token="x"))
    assert len(mine.environment.sources) == 1


def test_shared_hmac_file_is_refused(tmp_path: Path) -> None:
    registry = WorldRegistry(home=tmp_path)
    alex = registry.handle(WorldId.ALEX_LAB)
    mine = registry.handle(WorldId.MY_ENIGMA)
    _ = alex.hmac_key
    private_key = hmac_key_path(mine.storage_root)
    private_key.parent.mkdir(parents=True, exist_ok=True)
    private_key.write_bytes(hmac_key_path(alex.storage_root).read_bytes())
    mine._hmac_key = None  # noqa: SLF001 — simulate reload of tampered key
    with pytest.raises(WorldIsolationError, match="HMAC"):
        registry.assert_isolated(require_keys=True)


def test_private_root_must_not_be_demo(tmp_path: Path) -> None:
    demo = tmp_path / ".enigma" / "demo" / "alex-v1"
    demo.mkdir(parents=True)
    with pytest.raises(WorldIsolationError, match="Demo"):
        assert_private_storage_root(demo)


def test_public_view_omits_raw_hmac(tmp_path: Path) -> None:
    registry = WorldRegistry(home=tmp_path)
    view = registry.public_view()
    blob = str(view)
    assert "hmac_key" not in blob
    worlds = view["worlds"]
    assert isinstance(worlds, list)
    alex = worlds[0]
    assert isinstance(alex, dict)
    fingerprint = alex["hmac_fingerprint"]
    assert isinstance(fingerprint, str)
    assert fingerprint.startswith("sha256:")
    assert len(fingerprint) < 40
    assert registry.active_id.value == view["active"]


def test_identity_01_same_email_different_tokens(tmp_path: Path) -> None:
    """IDENTITY_01 — same email → different tokens across worlds."""
    registry = WorldRegistry(home=tmp_path)
    sample = "maya@example.com"
    alex = person_token_for(registry.handle(WorldId.ALEX_LAB).hmac_key, sample)
    mine = person_token_for(registry.handle(WorldId.MY_ENIGMA).hmac_key, sample)
    assert alex != mine
    assert alex.startswith("PERSON_")
    assert mine.startswith("PERSON_")


def test_key_01_demo_private_fingerprints_differ(tmp_path: Path) -> None:
    """KEY_01 — demo/private key fingerprints differ."""
    registry = WorldRegistry(home=tmp_path)
    alex = registry.handle(WorldId.ALEX_LAB).hmac_fingerprint
    mine = registry.handle(WorldId.MY_ENIGMA).hmac_fingerprint
    assert alex != mine
    assert alex.startswith("sha256:")
    assert mine.startswith("sha256:")
    registry.assert_isolated(require_keys=True)


def test_reset_01_alex_reset_destroys_only_alex_state(tmp_path: Path) -> None:
    """RESET_01 — Alex reset destroys only Alex state."""
    registry = WorldRegistry(home=tmp_path)
    mine = registry.handle(WorldId.MY_ENIGMA)
    keep = mine.storage_root / "keep-private.txt"
    keep.parent.mkdir(parents=True, exist_ok=True)
    keep.write_text("private-safe", encoding="utf-8")
    private_fp = mine.hmac_fingerprint
    junk = registry.handle(WorldId.ALEX_LAB).storage_root / "stale.json"
    junk.parent.mkdir(parents=True, exist_ok=True)
    junk.write_text("dirty", encoding="utf-8")
    old_alex_fp = registry.handle(WorldId.ALEX_LAB).hmac_fingerprint

    registry.reset(WorldId.ALEX_LAB)
    assert not junk.exists()
    assert keep.read_text(encoding="utf-8") == "private-safe"
    assert registry.handle(WorldId.MY_ENIGMA).hmac_fingerprint == private_fp
    assert registry.handle(WorldId.ALEX_LAB).hmac_fingerprint != old_alex_fp


def test_clock_01_alex_clock_cannot_alter_private_temporal_state(tmp_path: Path) -> None:
    """CLOCK_01 — Alex clock manipulation cannot alter private temporal state."""
    registry = WorldRegistry(home=tmp_path)
    alex = registry.handle(WorldId.ALEX_LAB)
    mine = registry.handle(WorldId.MY_ENIGMA)
    far = datetime(2099, 6, 1, tzinfo=UTC)
    assert isinstance(alex.clock, SimulationClock)
    alex.clock.set_time(far)
    assert alex.clock.now() == far
    private_now = mine.clock.now()
    assert private_now.year != 2099
    assert isinstance(mine.clock, SystemClock)
