"""Tests for Demo Mode API banner + live alex-v1 attention (D10 / D14)."""

from __future__ import annotations

import pytest
from fastapi.testclient import TestClient

from personal_enigma.api import create_app
from personal_enigma.simulation import DEMO_BANNER_TEXT


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


def test_demo_status_includes_suppression_stats(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("ENIGMA_ENVIRONMENT_MODE", "demo")
    monkeypatch.setenv("ENIGMA_DEMO_BACKGROUND_PROFILE", "none")
    client = TestClient(create_app())
    status = client.get("/demo/status").json()
    assert status["live_attention"] is True
    assert status["surfaced_count"] is not None
    assert status["suppressed_count"] is not None
    assert status["signals_considered"] == status["surfaced_count"] + status["suppressed_count"]
    assert status["noise_suppressed_count"] == status["suppressed_count"]


def test_demo_suppressed_inspector(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("ENIGMA_ENVIRONMENT_MODE", "demo")
    monkeypatch.setenv("ENIGMA_DEMO_BACKGROUND_PROFILE", "none")
    client = TestClient(create_app())
    body = client.get("/demo/suppressed").json()
    assert body["developer_only"] is True
    assert body["surfaced_count"] is not None
    assert body["suppressed_count"] is not None
    assert body["signals_considered"] == body["surfaced_count"] + body["suppressed_count"]
    assert "newsletter" in body["filters"]
    assert body["items"]
    first = body["items"][0]
    assert "why_not" in first
    assert "suppression_reason" in first
    assert "signal_class" not in first
    assert "ground_truth" not in body
    filtered = client.get("/demo/suppressed", params={"reason": "spam"}).json()
    assert filtered["filter"] == "spam"
    assert all(row["suppression_reason"] == "spam" for row in filtered["items"])
    bad = client.get("/demo/suppressed", params={"reason": "signal_class"})
    assert bad.status_code == 400
    empty = client.get("/demo/suppressed", params={"reason": ""})
    assert empty.status_code == 400


def test_timeline_step_and_speed(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("ENIGMA_ENVIRONMENT_MODE", "demo")
    client = TestClient(create_app())
    status = client.get("/demo/status").json()
    assert status["speed"] == 0.0
    assert status["paused"] is True
    stepped = client.post("/demo/timeline/step").json()
    assert stepped["simulated_time"] is not None
    assert stepped["simulated_time"] > status["simulated_time"]
    # Manual step works while auto-play is paused.
    assert stepped["paused"] is True
    sped = client.post("/demo/timeline/speed", json={"speed": 10}).json()
    assert sped["speed"] == 10.0
    assert sped["paused"] is False
    paused = client.post("/demo/timeline/speed", json={"speed": 0}).json()
    assert paused["paused"] is True
    before = paused["simulated_time"]
    after_pause_step = client.post("/demo/timeline/step").json()
    assert after_pause_step["simulated_time"] > before


def test_timeline_requires_demo_mode(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.delenv("ENIGMA_ENVIRONMENT_MODE", raising=False)
    client = TestClient(create_app())
    response = client.post("/demo/timeline/day")
    assert response.status_code == 409


def test_attention_live_from_alex_not_atlas_stubs(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv("ENIGMA_ENVIRONMENT_MODE", "demo")
    monkeypatch.setenv("ENIGMA_DEMO_BACKGROUND_PROFILE", "demo")
    client = TestClient(create_app())
    for _ in range(3):
        client.post("/demo/timeline/step")
    attention = client.get("/demo/attention").json()
    assert attention["items"]
    assert attention["live"] is True
    assert "ground_truth" not in attention
    assert attention["surfaced_count"] == len(attention["items"])
    assert attention["suppressed_count"] >= 0
    assert attention["signals_considered"] == attention["surfaced_count"] + attention["suppressed_count"]
    titles = [item["title"] for item in attention["items"]]
    blob = " | ".join(titles)
    assert "Atlas proposal" not in blob
    assert "att-atlas-review" not in {item["id"] for item in attention["items"]}
    first = attention["items"][0]
    assert "PERSON_A" not in first["title"]
    assert "score" not in first
    assert 1 <= first["priority"] <= 5
    assert 0.0 <= first["confidence"] <= 1.0
    assert first["attention_rank"] >= attention["items"][-1]["attention_rank"]
    why = client.get(f"/demo/why/{first['id']}").json()
    assert why["headline"] == "WHY ENIGMA THINKS THIS MATTERS"
    assert why["item_id"] == first["id"]
    assert why["evidence"]
    assert "why_now" in why
    assert "ground_truth" not in why
    assert "signal_class" not in why


def test_attention_changes_after_day_advance(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("ENIGMA_ENVIRONMENT_MODE", "demo")
    monkeypatch.setenv("ENIGMA_DEMO_BACKGROUND_PROFILE", "feature")
    client = TestClient(create_app())
    for _ in range(3):
        client.post("/demo/timeline/step")
    day0 = {item["title"] for item in client.get("/demo/attention").json()["items"]}
    assert any("Maya" in title for title in day0)
    for _ in range(8):
        client.post("/demo/timeline/day")
    later = {item["title"] for item in client.get("/demo/attention").json()["items"]}
    assert later != day0
    assert "Send Q1 design priorities to Maya" not in later
    assert any("checkout" in title.casefold() for title in later)


def test_attention_done_and_snooze_actions(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("ENIGMA_ENVIRONMENT_MODE", "demo")
    monkeypatch.setenv("ENIGMA_DEMO_BACKGROUND_PROFILE", "feature")
    client = TestClient(create_app())
    for _ in range(3):
        client.post("/demo/timeline/step")
    before = client.get("/demo/attention").json()
    assert len(before["items"]) >= 1
    first_id = before["items"][0]["id"]
    done = client.post(f"/demo/attention/{first_id}/done").json()
    assert done["ok"] is True
    assert done["action"] == "done"
    assert all(item["id"] != first_id for item in done["items"])
    if done["items"]:
        second_id = done["items"][0]["id"]
        snoozed = client.post(f"/demo/attention/{second_id}/snooze").json()
        assert snoozed["action"] == "snooze"
        assert all(item["id"] != second_id for item in snoozed["items"])


def test_memory_browser_categories(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("ENIGMA_ENVIRONMENT_MODE", "demo")
    client = TestClient(create_app())
    body = client.get("/demo/memory").json()
    assert "People" in body["categories"]
    assert "Open loops" in body["categories"]
    assert "ground_truth" not in body
    assert all("ground_truth" not in item for item in body["items"])
