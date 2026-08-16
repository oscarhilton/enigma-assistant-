from fastapi.testclient import TestClient

from personal_enigma.api import create_app
from personal_enigma.api.routes.settings import (
    calendars_scheduled_for_sync,
    reset_settings_store,
)


def setup_function() -> None:
    reset_settings_store()


def test_get_settings_lists_calendars_and_permissions() -> None:
    client = TestClient(create_app())
    response = client.get("/settings")
    assert response.status_code == 200
    payload = response.json()
    assert {c["id"] for c in payload["calendars"]} == {
        "apple:work",
        "apple:personal",
        "google:team",
    }
    assert [p["id"] for p in payload["apple_permissions"]] == [
        "calendar",
        "reminders",
        "contacts",
        "notes",
    ]
    # Privacy: no note bodies or full contact records in the payload.
    assert "note_body" not in response.text
    assert "emails" not in response.text
    assert "phone_numbers" not in response.text
    assert payload["scheduled_for_sync"] == ["apple:work", "apple:personal"]


def test_calendar_selection_persists() -> None:
    client = TestClient(create_app())
    response = client.put(
        "/settings/calendars",
        json={"enabled_ids": ["apple:personal"]},
    )
    assert response.status_code == 200
    payload = response.json()
    enabled = {c["id"]: c["enabled"] for c in payload["calendars"]}
    assert enabled["apple:personal"] is True
    assert enabled["apple:work"] is False
    assert enabled["google:team"] is False
    assert payload["scheduled_for_sync"] == ["apple:personal"]

    reread = client.get("/settings").json()
    assert reread["scheduled_for_sync"] == ["apple:personal"]
    assert {c["id"] for c in reread["calendars"] if c["enabled"]} == {"apple:personal"}


def test_disabled_sources_are_not_scheduled_for_sync() -> None:
    client = TestClient(create_app())
    client.put("/settings/calendars", json={"enabled_ids": ["apple:work"]})
    assert calendars_scheduled_for_sync() == ["apple:work"]

    client.put("/settings/calendars", json={"enabled_ids": []})
    assert calendars_scheduled_for_sync() == []
    assert client.get("/settings").json()["scheduled_for_sync"] == []
