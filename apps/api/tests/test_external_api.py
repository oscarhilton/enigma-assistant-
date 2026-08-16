from fastapi.testclient import TestClient

from personal_enigma.api.main import create_app

AUTH = {"Authorization": "Bearer local-dev-token"}


def test_external_attention_requires_auth() -> None:
    client = TestClient(create_app())
    assert client.get("/external/attention").status_code == 401
    response = client.get("/external/attention", headers=AUTH)
    assert response.status_code == 200
    items = response.json()
    assert items[0]["title"] == "Review proposal"
    assert "email" not in items[0]["body"].lower() or "@" not in items[0]["body"]


def test_external_capabilities() -> None:
    client = TestClient(create_app())
    response = client.get("/external/capabilities", headers=AUTH)
    assert response.status_code == 200
    assert response.json()["notes"]["quality"] == "best_effort"


def test_refuse_private_person() -> None:
    client = TestClient(create_app())
    response = client.get("/external/private-person/anything", headers=AUTH)
    assert response.status_code == 404
