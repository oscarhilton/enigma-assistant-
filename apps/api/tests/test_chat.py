from fastapi.testclient import TestClient

from personal_enigma.api.main import create_app

AUTH = {"Authorization": "Bearer local-dev-token"}


def test_chat_preview_default_nothing_leaves() -> None:
    client = TestClient(create_app())
    response = client.post(
        "/external/chat",
        headers=AUTH,
        json={
            "summary": "Review proposal",
            "entities": ["PERSON_A4F91C"],
            "may_transmit_remotely": True,
            "preview_only": True,
        },
    )
    assert response.status_code == 200
    data = response.json()
    assert data["answer"] is None
    assert data["left_the_machine"] is False
    assert "Preview" in data["label"]


def test_chat_disabled_mode() -> None:
    import os

    os.environ["ENIGMA_REASONING_MODE"] = "disabled"
    client = TestClient(create_app())
    response = client.post(
        "/external/chat",
        headers=AUTH,
        json={
            "summary": "Review proposal",
            "entities": ["PERSON_A4F91C"],
            "may_transmit_remotely": True,
            "preview_only": False,
            "confirm_send": True,
        },
    )
    assert response.status_code == 200
    data = response.json()
    assert data["remote_disabled"] is True
    assert data["left_the_machine"] is False
