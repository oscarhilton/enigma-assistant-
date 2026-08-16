"""Gmail OAuth stubs for Enigma Core (ticket M11).

Scaffold only — no live Google OAuth until credentials are configured.
"""

from __future__ import annotations

from dataclasses import dataclass

GMAIL_READONLY_SCOPE = "https://www.googleapis.com/auth/gmail.readonly"
OAUTH_AUTHORIZE_URL = "https://accounts.google.com/o/oauth2/v2/auth"
OAUTH_TOKEN_URL = "https://oauth2.googleapis.com/token"


@dataclass(frozen=True, slots=True)
class GmailOAuthConfig:
    """Client settings for read-only Gmail OAuth."""

    client_id: str | None = None
    client_secret: str | None = None
    redirect_uri: str = "http://127.0.0.1:8000/google/gmail/oauth/callback"
    scopes: tuple[str, ...] = (GMAIL_READONLY_SCOPE,)


@dataclass(frozen=True, slots=True)
class GmailOAuthStart:
    """Browser redirect payload for the OAuth authorize step."""

    authorize_url: str
    state: str
    scope: str


def gmail_oauth_start(config: GmailOAuthConfig, *, state: str) -> GmailOAuthStart:
    """Build an authorize URL without contacting Google (stub)."""
    if not config.client_id:
        raise ValueError("Gmail OAuth client_id is not configured")
    scope = " ".join(config.scopes)
    # Query construction is deferred to a real OAuth client in a later pass.
    authorize_url = (
        f"{OAUTH_AUTHORIZE_URL}?client_id={config.client_id}"
        f"&redirect_uri={config.redirect_uri}"
        f"&response_type=code&scope={scope}&state={state}&access_type=offline"
    )
    return GmailOAuthStart(authorize_url=authorize_url, state=state, scope=scope)


def gmail_oauth_configured(config: GmailOAuthConfig) -> bool:
    """Return True when Core has enough config to begin OAuth."""
    return bool(config.client_id and config.client_secret)
