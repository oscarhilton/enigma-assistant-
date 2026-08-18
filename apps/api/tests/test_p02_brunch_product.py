"""P02 — Brunch as a product script against Demo routes (same truth the pilot shell shows)."""

from __future__ import annotations

from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from personal_enigma.api import create_app

BRUNCH_ID = "item-obligation_brunch_book"
BRUNCH_CHECKPOINT = "cp-2026-01-20T11:00"
BRUNCH_TITLE = "Book Saturday brunch for Elena's parents"
CALENDAR_EVENT = "Brunch with Elena's parents"


def _client(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> TestClient:
    monkeypatch.setenv("ENIGMA_HOME", str(tmp_path / "home"))
    monkeypatch.setenv("ENIGMA_ENVIRONMENT_MODE", "demo")
    monkeypatch.setenv("LLM_DISABLED", "1")
    monkeypatch.delenv("ENIGMA_PRIVATE_STORAGE_ROOT", raising=False)
    monkeypatch.delenv("ENIGMA_DEMO_STORAGE_ROOT", raising=False)
    return TestClient(create_app())


def test_p02_brunch_fixture_is_unresolved_and_calendar_is_not_a_reservation(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    client = _client(tmp_path, monkeypatch)
    assert client.post("/worlds/switch", json={"world": "alex_lab"}).status_code == 200
    jumped = client.post(f"/demo/timeline/checkpoint/{BRUNCH_CHECKPOINT}")
    assert jumped.status_code == 200

    attention = client.get("/demo/attention/state").json()
    needs = {row["id"]: row for row in attention["needs_you"]}
    assert BRUNCH_ID in needs
    assert needs[BRUNCH_ID]["title"] == BRUNCH_TITLE
    evidence = set(needs[BRUNCH_ID]["evidence_ids"])
    assert "cal-brunch-parents" in evidence
    assert "rem-brunch-book" in evidence
    assert "mail-elena-weekend" in evidence

    why = client.get(f"/demo/why/{BRUNCH_ID}").json()
    assert "cal-brunch-parents" in why["evidence"]
    assert "rem-brunch-book" in why["evidence"]

    # Product already distinguishes calendar hold vs still-open booking
    # (availability-shaped Saturday ask). Reservation is not confirmed.
    turn = client.post(
        "/demo/conversation/message",
        json={"text": "Tell me about the Saturday brunch"},
    )
    assert turn.status_code == 200
    blob = str(turn.json()).lower()
    assert "brunch with elena's parents" in blob or CALENDAR_EVENT.lower() in blob
    assert "still open" in blob
    assert "riverside brunch club" not in blob
    assert "confirm the reservation" not in blob
