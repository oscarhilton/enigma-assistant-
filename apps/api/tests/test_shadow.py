"""Tests for Shadow Mode API banner stubs (S01)."""

from __future__ import annotations

import pytest
from fastapi.testclient import TestClient

from personal_enigma.api import create_app
from personal_enigma.simulation import SHADOW_BANNER_TEXT


def test_shadow_banner_inactive_by_default(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.delenv("ENIGMA_ENVIRONMENT_MODE", raising=False)
    client = TestClient(create_app())
    response = client.get("/shadow/banner")
    assert response.status_code == 200
    body = response.json()
    assert body["active"] is False
    assert body["mode"] == "private"
    assert body["text"] == ""


def test_shadow_banner_active_in_shadow_mode(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("ENIGMA_ENVIRONMENT_MODE", "shadow")
    client = TestClient(create_app())
    response = client.get("/shadow/banner")
    assert response.status_code == 200
    body = response.json()
    assert body["active"] is True
    assert body["mode"] == "shadow"
    assert body["text"] == SHADOW_BANNER_TEXT


def test_shadow_environment_payload(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("ENIGMA_ENVIRONMENT_MODE", "shadow")
    client = TestClient(create_app())
    response = client.get("/shadow/environment")
    assert response.status_code == 200
    body = response.json()
    assert body["mode"] == "shadow"
    assert body["banner"] == SHADOW_BANNER_TEXT
    assert body["storage_root"] is not None
    assert "shadow" in body["storage_root"]
    assert body["notifications_suppressed"] is True
