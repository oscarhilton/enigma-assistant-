"""Disclosure API — GET /private/disclosure/recent must return JSON, not HTML."""

from __future__ import annotations

from fastapi.testclient import TestClient

from personal_enigma.api.main import create_app
from personal_enigma.privacy.egress import set_audited_egress_gate

AUTH = {"Authorization": "Bearer local-dev-token"}


def test_recent_disclosures_requires_auth() -> None:
    client = TestClient(create_app())
    assert client.get("/private/disclosure/recent").status_code == 401


def test_recent_disclosures_returns_json_list() -> None:
    set_audited_egress_gate(None)
    client = TestClient(create_app())
    response = client.get("/private/disclosure/recent", headers=AUTH)
    assert response.status_code == 200
    assert "application/json" in response.headers["content-type"]
    body = response.json()
    assert body == {"disclosures": []}
    assert not response.text.lstrip().startswith("<")
