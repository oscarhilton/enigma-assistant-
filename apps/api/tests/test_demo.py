"""Tests for Demo Mode API banner + D10 timeline / chrome stubs."""

from __future__ import annotations

import pytest
from fastapi.testclient import TestClient

from personal_enigma.api import create_app
from personal_enigma.api.routes import demo as demo_routes
from personal_enigma.simulation import DEMO_BANNER_TEXT


@pytest.fixture(autouse=True)
def _reset_demo_session() -> None:
    demo_routes._SESSION = demo_routes.DemoSession()


def test_demo_banner_inactive_by_default(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.delenv("ENIGMA_ENVIRONMENT_MODE", raising=False)
    client = TestClient(create_app())
    response = client.get("/demo/banner")
    assert response.status_code == 200
    body = response.json()
    assert body["active"] is False
    assert body["mode"] == "private"
    assert body["text"] == ""


def test_demo_banner_active_in_demo_mode(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("ENIGMA_ENVIRONMENT_MODE", "demo")
    client = TestClient(create_app())
    response = client.get("/demo/banner")
    assert response.status_code == 200
    body = response.json()
    assert body["active"] is True
    assert body["mode"] == "demo"
    assert body["text"] == DEMO_BANNER_TEXT


def test_demo_environment_payload(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("ENIGMA_ENVIRONMENT_MODE", "demo")
    client = TestClient(create_app())
    response = client.get("/demo/environment", params={"scenario": "alex-v1"})
    assert response.status_code == 200
    body = response.json()
    assert body["mode"] == "demo"
    assert body["scenario"] == "alex-v1"
    assert body["banner"] == DEMO_BANNER_TEXT
    assert body["storage_root"] is not None
    assert "alex-v1" in body["storage_root"]


def test_timeline_day_advances_simulated_time(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("ENIGMA_ENVIRONMENT_MODE", "demo")
    client = TestClient(create_app())
    before = client.get("/demo/status").json()["simulated_time"]
    assert before is not None
    after = client.post("/demo/timeline/day").json()["simulated_time"]
    assert after is not None
    assert after > before


def test_timeline_step_and_speed(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("ENIGMA_ENVIRONMENT_MODE", "demo")
    client = TestClient(create_app())
    stepped = client.post("/demo/timeline/step").json()
    assert stepped["simulated_time"] is not None
    sped = client.post("/demo/timeline/speed", json={"speed": 10}).json()
    assert sped["speed"] == 10.0
    assert sped["paused"] is False
    paused = client.post("/demo/timeline/speed", json={"speed": 0}).json()
    assert paused["paused"] is True


def test_timeline_requires_demo_mode(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.delenv("ENIGMA_ENVIRONMENT_MODE", raising=False)
    client = TestClient(create_app())
    response = client.post("/demo/timeline/day")
    assert response.status_code == 409


def test_attention_and_why_omit_ground_truth(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("ENIGMA_ENVIRONMENT_MODE", "demo")
    client = TestClient(create_app())
    attention = client.get("/demo/attention").json()
    assert attention["items"]
    assert "ground_truth" not in attention
    why = client.get("/demo/why/att-atlas-review").json()
    assert why["headline"] == "WHY ENIGMA THINKS THIS MATTERS"
    assert "ground_truth" not in why
    assert "groundTruth" not in why


def test_memory_browser_categories(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("ENIGMA_ENVIRONMENT_MODE", "demo")
    client = TestClient(create_app())
    body = client.get("/demo/memory").json()
    assert "People" in body["categories"]
    assert "Open loops" in body["categories"]
    assert "ground_truth" not in body
    assert all("ground_truth" not in item for item in body["items"])
