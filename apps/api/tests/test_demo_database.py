from __future__ import annotations

from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from personal_enigma.api import create_app
from personal_enigma.api.db.demo import (
    assert_demo_database_url,
    demo_database_path,
    drop_demo_database,
    resolve_demo_database_url,
)
from personal_enigma.api.db.migrate import upgrade_head
from personal_enigma.api.db.store import open_store
from personal_enigma.ingestion import SyncCursor
from personal_enigma.simulation.checkpoints import ensure_demo_layout


def test_resolve_demo_database_url_defaults_to_demo_root(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv("ENIGMA_HOME", str(tmp_path / "home"))
    monkeypatch.delenv("ENIGMA_DATABASE_URL", raising=False)

    url = resolve_demo_database_url(scenario="alex-v1")
    assert url.endswith("/demo/alex-v1/enigma.db")
    assert demo_database_path(scenario="alex-v1") == Path(url.removeprefix("sqlite:///"))


def test_assert_demo_database_url_rejects_private_default(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    private_db = tmp_path / "personal-enigma" / "private.db"
    private_db.parent.mkdir(parents=True)
    monkeypatch.setenv("ENIGMA_HOME", str(tmp_path / "home"))
    monkeypatch.setenv("ENIGMA_DATABASE_URL", f"sqlite:///{private_db}")

    with pytest.raises(ValueError, match="Demo database URL must live under"):
        assert_demo_database_url(f"sqlite:///{private_db}", scenario="alex-v1")


def test_drop_demo_database_removes_migrated_schema(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv("ENIGMA_HOME", str(tmp_path / "home"))
    monkeypatch.delenv("ENIGMA_DATABASE_URL", raising=False)

    url = resolve_demo_database_url(scenario="alex-v1")
    ensure_demo_layout(demo_database_path(scenario="alex-v1").parent)
    upgrade_head(url)
    store = open_store(url=url)
    store.upsert_sync_cursor(SyncCursor(value="cursor-1", source="demo_mail"))

    db_path = drop_demo_database(scenario="alex-v1")
    assert not db_path.exists()
    assert not Path(f"{db_path}-wal").exists()
    assert not Path(f"{db_path}-shm").exists()

    upgrade_head(url)
    restored = open_store(url=url)
    assert restored.get_sync_cursor("demo_mail") is None


def test_demo_reset_drops_migrated_demo_database(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv("ENIGMA_ENVIRONMENT_MODE", "demo")
    monkeypatch.setenv("ENIGMA_HOME", str(tmp_path / "home"))
    monkeypatch.delenv("ENIGMA_DATABASE_URL", raising=False)

    url = resolve_demo_database_url(scenario="alex-v1")
    ensure_demo_layout(demo_database_path(scenario="alex-v1").parent)
    upgrade_head(url)
    store = open_store(url=url)
    store.upsert_sync_cursor(SyncCursor(value="stale", source="demo_mail"))

    client = TestClient(create_app())
    body = client.post("/demo/reset").json()
    assert body["ok"] is True
    assert body["reset"] is True

    db_path = demo_database_path(scenario="alex-v1")
    assert db_path.is_file()
    assert db_path.stat().st_size == 0

    upgrade_head(url)
    restored = open_store(url=url)
    assert restored.get_sync_cursor("demo_mail") is None
