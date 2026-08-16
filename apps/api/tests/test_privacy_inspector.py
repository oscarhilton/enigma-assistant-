from fastapi.testclient import TestClient

from personal_enigma.api.main import create_app


def test_privacy_inspect_preview_and_cancel() -> None:
    client = TestClient(create_app())
    preview = client.post(
        "/privacy/inspect",
        json={
            "summary": "Review proposal before Friday",
            "entities": ["PERSON_A4F91C"],
            "may_transmit_remotely": True,
            "source_type": "reminder",
            "remote_enabled": True,
        },
    )
    assert preview.status_code == 200
    data = preview.json()
    assert data["can_send"] is True
    assert data["would_send"]["summary"].startswith("Review")
    assert "apple_permission_note" in data

    cancelled = client.post(
        "/privacy/inspect",
        json={
            "summary": "Review proposal before Friday",
            "may_transmit_remotely": True,
            "remote_enabled": True,
            "cancel": True,
        },
    )
    assert cancelled.status_code == 200
    assert cancelled.json()["cancelled"] is True
    assert cancelled.json()["can_send"] is False


def test_inspector_does_not_upload_private_person() -> None:
    client = TestClient(create_app())
    response = client.post(
        "/privacy/inspect",
        json={
            "summary": "contact joe@example.com",
            "entities": [],
            "may_transmit_remotely": True,
            "remote_enabled": True,
        },
    )
    assert response.status_code == 200
    # Email in summary should fail allowlist / person field checks
    body = response.json()
    assert body["can_send"] is False or body["would_send"] is None or "@" not in str(
        body.get("would_send")
    )
