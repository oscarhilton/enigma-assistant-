"""P01 world switcher API — isolation, clocks, reset, one product."""

from __future__ import annotations

from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from personal_enigma.api import create_app
from personal_enigma.simulation.worlds import hmac_key_path, person_token_for


def _client(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> TestClient:
    monkeypatch.setenv("ENIGMA_HOME", str(tmp_path / "home"))
    monkeypatch.delenv("ENIGMA_ENVIRONMENT_MODE", raising=False)
    monkeypatch.delenv("ENIGMA_ACTIVE_WORLD", raising=False)
    monkeypatch.delenv("ENIGMA_PRIVATE_STORAGE_ROOT", raising=False)
    monkeypatch.delenv("ENIGMA_DEMO_STORAGE_ROOT", raising=False)
    return TestClient(create_app())


def test_worlds_are_isolated_on_the_wire(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    client = _client(tmp_path, monkeypatch)
    body = client.get("/worlds").json()
    assert body["active"] == "my_enigma"
    worlds = {row["id"]: row for row in body["worlds"]}
    alex = worlds["alex_lab"]
    mine = worlds["my_enigma"]
    assert alex["storage_root"] != mine["storage_root"]
    assert alex["database_path"] != mine["database_path"]
    assert alex["hmac_fingerprint"] != mine["hmac_fingerprint"]
    assert alex["clock_kind"] == "simulation"
    assert mine["clock_kind"] == "system"
    assert alex["resettable"] is True
    assert mine["resettable"] is False
    assert mine["persistent"] is True
    blob = str(body)
    assert "hmac_key" not in blob
    alex_key = hmac_key_path(Path(alex["storage_root"])).read_text(encoding="utf-8").strip()
    mine_key = hmac_key_path(Path(mine["storage_root"])).read_text(encoding="utf-8").strip()
    assert person_token_for(bytes.fromhex(alex_key), "maya@example.com") != person_token_for(
        bytes.fromhex(mine_key), "maya@example.com"
    )


def test_switch_enables_alex_lab_without_process_demo_env(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    client = _client(tmp_path, monkeypatch)
    blocked = client.get("/demo/conversation")
    assert blocked.status_code == 409

    switched = client.post("/worlds/switch", json={"world": "alex_lab"})
    assert switched.status_code == 200
    assert switched.json()["active"]["id"] == "alex_lab"
    assert switched.json()["active"]["clock_kind"] == "simulation"

    convo = client.get("/demo/conversation")
    assert convo.status_code == 200
    assert "items" in convo.json()

    # My Enigma conversation must not be reachable while Alex Lab is active.
    private = client.get("/worlds/my_enigma/conversation")
    assert private.status_code == 409


def test_switch_back_does_not_leak_alex_conversation(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    client = _client(tmp_path, monkeypatch)
    client.post("/worlds/switch", json={"world": "my_enigma"})
    mine = client.get("/worlds/my_enigma/conversation").json()
    assert mine["items"] == []

    attention = client.get("/worlds/my_enigma/attention/state").json()
    assert attention["presentation"]["proactive_silence"] is True
    assert attention["needs_you"] == []
    assert attention["simulated_time"]  # wall clock, not Alex Jan 19 epoch


def test_reset_alex_leaves_my_enigma_intact(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    client = _client(tmp_path, monkeypatch)
    worlds = {row["id"]: row for row in client.get("/worlds").json()["worlds"]}
    private_root = Path(worlds["my_enigma"]["storage_root"])
    keep = private_root / "keep-private.txt"
    keep.parent.mkdir(parents=True, exist_ok=True)
    keep.write_text("private-safe", encoding="utf-8")
    private_fp = worlds["my_enigma"]["hmac_fingerprint"]

    alex_root = Path(worlds["alex_lab"]["storage_root"])
    junk = alex_root / "stale.json"
    junk.parent.mkdir(parents=True, exist_ok=True)
    junk.write_text("dirty", encoding="utf-8")

    refused = client.post("/worlds/my_enigma/reset")
    assert refused.status_code == 409
    assert keep.read_text(encoding="utf-8") == "private-safe"

    reset = client.post("/worlds/alex_lab/reset")
    assert reset.status_code == 200
    assert not junk.exists()
    assert keep.read_text(encoding="utf-8") == "private-safe"
    after = {row["id"]: row for row in client.get("/worlds").json()["worlds"]}
    assert after["my_enigma"]["hmac_fingerprint"] == private_fp
    assert after["alex_lab"]["hmac_fingerprint"] != worlds["alex_lab"]["hmac_fingerprint"]


def test_unknown_world_is_rejected(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    client = _client(tmp_path, monkeypatch)
    response = client.post("/worlds/switch", json={"world": "shadow"})
    assert response.status_code == 400
