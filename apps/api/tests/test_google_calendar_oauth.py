"""Smoke tests for Google Calendar OAuth stubs."""

from personal_enigma.api.google.calendar import (
    GoogleCalendarOAuthConfig,
    google_calendar_oauth_configured,
    google_calendar_oauth_start,
)


def test_google_calendar_oauth_not_configured_by_default() -> None:
    assert google_calendar_oauth_configured(GoogleCalendarOAuthConfig()) is False


def test_google_calendar_oauth_start_builds_authorize_url() -> None:
    config = GoogleCalendarOAuthConfig(client_id="client", client_secret="secret")
    start = google_calendar_oauth_start(config, state="xyz")
    assert start.state == "xyz"
    assert "client_id=client" in start.authorize_url
    assert "calendar.readonly" in start.scope
