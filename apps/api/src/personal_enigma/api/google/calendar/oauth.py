"""Google Calendar OAuth stubs for Enigma Core (ticket M12).

Scaffold only — no live Google OAuth until credentials are configured.
"""

from __future__ import annotations

from dataclasses import dataclass

from personal_enigma.ingestion.sources.google_calendar import CALENDAR_READONLY_SCOPE

OAUTH_AUTHORIZE_URL = "https://accounts.google.com/o/oauth2/v2/auth"
OAUTH_TOKEN_URL = "https://oauth2.googleapis.com/token"


@dataclass(frozen=True, slots=True)
class GoogleCalendarOAuthConfig:
    """Client settings for read-only Google Calendar OAuth."""

    client_id: str | None = None
    client_secret: str | None = None
    redirect_uri: str = "http://127.0.0.1:8000/google/calendar/oauth/callback"
    scopes: tuple[str, ...] = (CALENDAR_READONLY_SCOPE,)


@dataclass(frozen=True, slots=True)
class GoogleCalendarOAuthStart:
    """Browser redirect payload for the OAuth authorize step."""

    authorize_url: str
    state: str
    scope: str


def google_calendar_oauth_start(
    config: GoogleCalendarOAuthConfig, *, state: str
) -> GoogleCalendarOAuthStart:
    """Build an authorize URL without contacting Google (stub)."""
    if not config.client_id:
        raise ValueError("Google Calendar OAuth client_id is not configured")
    scope = " ".join(config.scopes)
    authorize_url = (
        f"{OAUTH_AUTHORIZE_URL}?client_id={config.client_id}"
        f"&redirect_uri={config.redirect_uri}"
        f"&response_type=code&scope={scope}&state={state}&access_type=offline"
    )
    return GoogleCalendarOAuthStart(authorize_url=authorize_url, state=state, scope=scope)


def google_calendar_oauth_configured(config: GoogleCalendarOAuthConfig) -> bool:
    """Return True when Core has enough config to begin OAuth."""
    return bool(config.client_id and config.client_secret)
