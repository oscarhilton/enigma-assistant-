"""P01 world switcher API — isolation, clocks, reset, one product."""

from __future__ import annotations

from datetime import datetime
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


PRIVATE_CANARY = "PRIVATE_CONVERSATION_MUST_NOT_LEAK"
ALEX_CANARY = "ALEX_CONVERSATION_MUST_NOT_LEAK"


def _conversation_blob(payload: object) -> str:
    return str(payload)


def test_world_switch_01_private_conversation_absent_from_alex(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """WORLD_SWITCH_01 — private conversation does not appear in Alex after switch."""
    client = _client(tmp_path, monkeypatch)
    assert client.post("/worlds/switch", json={"world": "my_enigma"}).status_code == 200
    sent = client.post(
        "/worlds/my_enigma/conversation/message", json={"text": PRIVATE_CANARY}
    )
    assert sent.status_code == 200
    assert PRIVATE_CANARY in _conversation_blob(
        client.get("/worlds/my_enigma/conversation").json()
    )

    assert client.post("/worlds/switch", json={"world": "alex_lab"}).status_code == 200
    alex = client.get("/demo/conversation")
    assert alex.status_code == 200
    assert PRIVATE_CANARY not in _conversation_blob(alex.json())
    blocked = client.get("/worlds/my_enigma/conversation")
    assert blocked.status_code == 409


def test_world_switch_02_alex_conversation_absent_from_private(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """WORLD_SWITCH_02 — Alex conversation does not appear in private."""
    client = _client(tmp_path, monkeypatch)
    assert client.post("/worlds/switch", json={"world": "alex_lab"}).status_code == 200
    sent = client.post("/demo/conversation/message", json={"text": ALEX_CANARY})
    assert sent.status_code == 200
    assert ALEX_CANARY in _conversation_blob(client.get("/demo/conversation").json())

    assert client.post("/worlds/switch", json={"world": "my_enigma"}).status_code == 200
    mine = client.get("/worlds/my_enigma/conversation")
    assert mine.status_code == 200
    assert ALEX_CANARY not in _conversation_blob(mine.json())
    blocked = client.get("/demo/conversation")
    assert blocked.status_code == 409


def test_route_01_demo_rejected_while_my_enigma_active(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """ROUTE_01 — /demo/* rejected while My Enigma active."""
    client = _client(tmp_path, monkeypatch)
    assert client.get("/worlds").json()["active"] == "my_enigma"
    for path, method in (
        ("/demo/conversation", "get"),
        ("/demo/status", "get"),
        ("/demo/environment", "get"),
        ("/demo/attention/state", "get"),
        ("/demo/reset", "post"),
        ("/demo/timeline/day", "post"),
    ):
        response = client.get(path) if method == "get" else client.post(path)
        assert response.status_code == 409, path


def test_reset_02_private_impossible_through_demo_reset_path(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """RESET_02 — private reset is impossible through demo reset path."""
    client = _client(tmp_path, monkeypatch)
    worlds = {row["id"]: row for row in client.get("/worlds").json()["worlds"]}
    keep = Path(worlds["my_enigma"]["storage_root"]) / "keep-private.txt"
    keep.parent.mkdir(parents=True, exist_ok=True)
    keep.write_text("private-safe", encoding="utf-8")

    refused_world = client.post("/worlds/my_enigma/reset")
    assert refused_world.status_code == 409
    refused_demo = client.post("/demo/reset")
    assert refused_demo.status_code == 409
    assert keep.read_text(encoding="utf-8") == "private-safe"


def test_clock_01_alex_clock_cannot_alter_private_temporal_state(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """CLOCK_01 — Alex clock manipulation cannot alter private temporal state."""
    client = _client(tmp_path, monkeypatch)
    assert client.post("/worlds/switch", json={"world": "my_enigma"}).status_code == 200
    sent = client.post(
        "/worlds/my_enigma/conversation/message", json={"text": PRIVATE_CANARY}
    )
    assert sent.status_code == 200
    assert client.get("/worlds/my_enigma/conversation").json()["items"]
    private_time_before = client.get("/worlds/my_enigma/attention/state").json()[
        "simulated_time"
    ]

    assert client.post("/worlds/switch", json={"world": "alex_lab"}).status_code == 200
    demo_before = client.get("/demo/status").json()["simulated_time"]
    assert demo_before is not None
    for _ in range(3):
        stepped = client.post("/demo/timeline/day")
        assert stepped.status_code == 200
    demo_after = client.get("/demo/status").json()["simulated_time"]
    assert demo_after is not None
    assert demo_after > demo_before

    assert client.post("/worlds/switch", json={"world": "my_enigma"}).status_code == 200
    private_time_after = client.get("/worlds/my_enigma/attention/state").json()[
        "simulated_time"
    ]
    assert private_time_after != demo_after
    # ADR-040 / P03 — private conversation clears on world switch; clock stays wall time.
    assert client.get("/worlds/my_enigma/conversation").json()["items"] == []
    before = datetime.fromisoformat(private_time_before)
    after = datetime.fromisoformat(private_time_after)
    assert abs((after - before).total_seconds()) < 60
    assert not after.isoformat().startswith("2026-01-")

