"""Tests for Demo Mode API banner + D10 timeline / chrome stubs."""

from __future__ import annotations

import json
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from personal_enigma.api import create_app
from personal_enigma.simulation import DEMO_BANNER_TEXT
from personal_enigma.simulation.engine import assert_demo_storage_root


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
    client = TestClient(create_app())
    status = client.get("/demo/status").json()
    assert status["surfaced_count"] == 2
    assert status["suppressed_count"] == 47
    assert status["noise_suppressed_count"] == 47
    assert status["signals_considered"] == 49


def test_demo_suppressed_inspector(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("ENIGMA_ENVIRONMENT_MODE", "demo")
    client = TestClient(create_app())
    body = client.get("/demo/suppressed").json()
    assert body["developer_only"] is True
    assert body["signals_considered"] == 49
    assert body["surfaced_count"] == 2
    assert body["suppressed_count"] == 47
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
    assert attention["surfaced_count"] == len(attention["items"])
    assert attention["suppressed_count"] == 47
    assert attention["signals_considered"] == 49
    first = attention["items"][0]
    assert first["title"] == "Review Atlas proposal before Friday"
    assert "Maya" in attention["items"][1]["title"]
    assert "PERSON_A" not in first["title"]
    assert "score" not in first
    assert first["priority"] == 4
    assert first["confidence"] == 0.91
    assert first["attention_rank"] >= attention["items"][1]["attention_rank"]
    why = client.get("/demo/why/att-atlas-review").json()
    assert why["headline"] == "WHY ENIGMA THINKS THIS MATTERS"
    assert why["priority"] == 4
    assert why["confidence"] == 0.91
    assert "why_now" in why
    assert any("Surface as a high-priority" in line for line in why["decision"])
    assert why["reason_codes"] == ["USER_COMMITMENT", "DEADLINE_APPROACHING"]
    assert "ground_truth" not in why
    assert "groundTruth" not in why


def test_attention_done_and_snooze_actions(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("ENIGMA_ENVIRONMENT_MODE", "demo")
    client = TestClient(create_app())
    before = client.get("/demo/attention").json()
    assert len(before["items"]) == 2
    done = client.post("/demo/attention/att-atlas-review/done").json()
    assert done["ok"] is True
    assert done["action"] == "done"
    assert len(done["items"]) == 1
    assert done["items"][0]["id"] == "att-maya-scheduling"
    snoozed = client.post("/demo/attention/att-maya-scheduling/snooze").json()
    assert snoozed["action"] == "snooze"
    assert snoozed["items"] == []
    assert client.get("/demo/attention").json()["items"] == []


def test_memory_browser_categories(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("ENIGMA_ENVIRONMENT_MODE", "demo")
    client = TestClient(create_app())
    body = client.get("/demo/memory").json()
    assert "People" in body["categories"]
    assert "Open loops" in body["categories"]
    assert "ground_truth" not in body
    assert all("ground_truth" not in item for item in body["items"])


def test_demo_reset_clears_demo_storage_and_reseeds(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv("ENIGMA_ENVIRONMENT_MODE", "demo")
    monkeypatch.setenv("ENIGMA_HOME", str(tmp_path / "home"))
    monkeypatch.delenv("ENIGMA_DEMO_STORAGE_ROOT", raising=False)
    monkeypatch.delenv("ENIGMA_PRIVATE_STORAGE_ROOT", raising=False)
    monkeypatch.delenv("ENIGMA_SHADOW_STORAGE_ROOT", raising=False)

    home = tmp_path / "home"
    private_root = home / "private"
    shadow_root = home / "shadow"
    private_root.mkdir(parents=True)
    shadow_root.mkdir(parents=True)
    (private_root / "keep.txt").write_text("private-safe", encoding="utf-8")
    (shadow_root / "keep.txt").write_text("shadow-safe", encoding="utf-8")

    client = TestClient(create_app())
    demo_root = Path(client.get("/demo/status").json()["storage_root"])
    assert demo_root.parts[-2:] == ("demo", "alex-v1")

    junk = demo_root / "stale.json"
    junk.parent.mkdir(parents=True, exist_ok=True)
    junk.write_text('{"dirty": true}', encoding="utf-8")
    (demo_root / "vectors").mkdir(exist_ok=True)
    (demo_root / "vectors" / "old.bin").write_bytes(b"stale")

    client.post("/demo/timeline/day")
    client.post("/demo/attention/att-atlas-review/done")
    assert len(client.get("/demo/attention").json()["items"]) == 1

    body = client.post("/demo/reset").json()
    assert body["ok"] is True
    assert body["reset"] is True
    assert body["storage_wiped"] is True
    assert body["storage_bootstrapped"] is True
    assert body["scenario"] == "alex-v1"
    assert body["simulated_time"] == "2026-01-01T09:00:00+00:00"
    assert body["speed"] == 1.0
    assert body["surfaced_count"] == 2
    assert Path(body["storage_root"]) == demo_root
    assert not junk.exists()
    assert not (demo_root / "vectors" / "old.bin").exists()
    engine = demo_root / "state" / "engine.json"
    assert engine.is_file()
    state = json.loads(engine.read_text(encoding="utf-8"))
    assert state["scenario"] == "alex-v1"
    assert state["bootstrapped"] is True
    assert state["emitted_ids"] == []
    assert (demo_root / "enigma.db").is_file()
    assert (private_root / "keep.txt").read_text(encoding="utf-8") == "private-safe"
    assert (shadow_root / "keep.txt").read_text(encoding="utf-8") == "shadow-safe"
    assert len(client.get("/demo/attention").json()["items"]) == 2


def test_demo_reset_idempotent_rebootstrap(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv("ENIGMA_ENVIRONMENT_MODE", "demo")
    monkeypatch.setenv("ENIGMA_HOME", str(tmp_path / "home"))
    monkeypatch.delenv("ENIGMA_DEMO_STORAGE_ROOT", raising=False)

    client = TestClient(create_app())
    first = client.post("/demo/reset").json()
    second = client.post("/demo/timeline/reset").json()
    assert first["simulated_time"] == second["simulated_time"] == "2026-01-01T09:00:00+00:00"
    assert first["surfaced_count"] == second["surfaced_count"] == 2
    assert second["storage_bootstrapped"] is True
    demo_root = Path(second["storage_root"])
    state = json.loads((demo_root / "state" / "engine.json").read_text(encoding="utf-8"))
    assert state["bootstrapped"] is True
    assert state["emitted_ids"] == []
    for name in ("state", "vectors", "config", "checkpoints"):
        assert (demo_root / name).is_dir()


def test_demo_reset_refuses_private_and_shadow_roots(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv("ENIGMA_ENVIRONMENT_MODE", "demo")

    private = tmp_path / ".enigma" / "private" / "alex-v1"
    private.mkdir(parents=True)
    with pytest.raises(ValueError, match="not private"):
        assert_demo_storage_root(private, scenario_id="alex-v1")

    shadow = tmp_path / "shadow"
    shadow.mkdir(parents=True)
    with pytest.raises(ValueError, match="not shadow"):
        assert_demo_storage_root(shadow, scenario_id="alex-v1")

    # Nest Demo under Private so wipe must refuse before deleting anything.
    private_root = tmp_path / "private-root"
    private_root.mkdir()
    (private_root / "keep.txt").write_text("private", encoding="utf-8")
    monkeypatch.setenv("ENIGMA_PRIVATE_STORAGE_ROOT", str(private_root))
    monkeypatch.setenv("ENIGMA_DEMO_STORAGE_ROOT", str(private_root / "demo"))
    client = TestClient(create_app())
    refused = client.post("/demo/reset")
    assert refused.status_code == 409
    assert "private" in refused.json()["detail"].lower()
    assert (private_root / "keep.txt").read_text(encoding="utf-8") == "private"

    shadow_root = tmp_path / "shadow-root"
    shadow_root.mkdir()
    (shadow_root / "keep.txt").write_text("shadow", encoding="utf-8")
    monkeypatch.setenv("ENIGMA_SHADOW_STORAGE_ROOT", str(shadow_root))
    monkeypatch.setenv("ENIGMA_DEMO_STORAGE_ROOT", str(shadow_root / "demo"))
    monkeypatch.delenv("ENIGMA_PRIVATE_STORAGE_ROOT", raising=False)
    client = TestClient(create_app())
    refused_shadow = client.post("/demo/reset")
    assert refused_shadow.status_code == 409
    assert "shadow" in refused_shadow.json()["detail"].lower()
    assert (shadow_root / "keep.txt").read_text(encoding="utf-8") == "shadow"

    # Private nested *inside* the Demo wipe target must also refuse.
    demo_parent = tmp_path / "demo-parent"
    nested_private = demo_parent / "alex-v1" / "private"
    nested_private.mkdir(parents=True)
    (nested_private / "keep.txt").write_text("nested-private", encoding="utf-8")
    monkeypatch.setenv("ENIGMA_DEMO_STORAGE_ROOT", str(demo_parent))
    monkeypatch.setenv("ENIGMA_PRIVATE_STORAGE_ROOT", str(nested_private))
    monkeypatch.delenv("ENIGMA_SHADOW_STORAGE_ROOT", raising=False)
    client = TestClient(create_app())
    refused_nested = client.post("/demo/reset")
    assert refused_nested.status_code == 409
    assert "private" in refused_nested.json()["detail"].lower()
    assert (nested_private / "keep.txt").read_text(encoding="utf-8") == "nested-private"


def test_demo_reset_requires_demo_mode(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.delenv("ENIGMA_ENVIRONMENT_MODE", raising=False)
    client = TestClient(create_app())
    assert client.post("/demo/reset").status_code == 409
