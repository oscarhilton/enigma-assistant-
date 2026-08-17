"""Gmail OAuth stubs for Enigma Core (ticket M11 / SEC-04).

Scaffold only — no live Google OAuth until credentials are configured.
Live sync requires ``ENIGMA_GMAIL_LIVE=1`` (see ``pipeline.gmail_live_sync_enabled``).
"""

from __future__ import annotations

import os
from dataclasses import dataclass
from urllib.parse import urlencode

from personal_enigma.ingestion.sources.gmail import GMAIL_READONLY_SCOPE

OAUTH_AUTHORIZE_URL = "https://accounts.google.com/o/oauth2/v2/auth"
OAUTH_TOKEN_URL = "https://oauth2.googleapis.com/token"
ALLOWED_GMAIL_SCOPES = frozenset({GMAIL_READONLY_SCOPE})


class GmailScopeError(ValueError):
    """OAuth consent returned scopes broader than gmail.readonly."""


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


def validate_gmail_oauth_scopes(granted_scopes: str | list[str] | tuple[str, ...]) -> None:
    """Reject OAuth consent when scopes exceed ``gmail.readonly`` (SEC-04)."""
    if isinstance(granted_scopes, str):
        scope_set = {part for part in granted_scopes.split() if part}
    else:
        scope_set = {part for part in granted_scopes if part}
    extra = scope_set - ALLOWED_GMAIL_SCOPES
    if extra:
        raise GmailScopeError(
            f"Gmail OAuth refused: scopes exceed gmail.readonly: {sorted(extra)}"
        )
    if GMAIL_READONLY_SCOPE not in scope_set:
        raise GmailScopeError(
            f"Gmail OAuth refused: required scope missing: {GMAIL_READONLY_SCOPE}"
        )


def gmail_oauth_start(config: GmailOAuthConfig, *, state: str) -> GmailOAuthStart:
    """Build an authorize URL without contacting Google (stub)."""
    if not config.client_id:
        raise ValueError("Gmail OAuth client_id is not configured")
    validate_gmail_oauth_scopes(config.scopes)
    scope = " ".join(config.scopes)
    query = urlencode(
        {
            "client_id": config.client_id,
            "redirect_uri": config.redirect_uri,
            "response_type": "code",
            "scope": scope,
            "state": state,
            "access_type": "offline",
        }
    )
    authorize_url = f"{OAUTH_AUTHORIZE_URL}?{query}"
    return GmailOAuthStart(authorize_url=authorize_url, state=state, scope=scope)


def gmail_oauth_configured(config: GmailOAuthConfig) -> bool:
    """Return True when Core has enough config to begin OAuth."""
    return bool(config.client_id and config.client_secret)


def gmail_oauth_live_allowed() -> bool:
    """Live OAuth/sync requires explicit operator opt-in."""
    return os.environ.get("ENIGMA_GMAIL_LIVE", "").strip().lower() in {"1", "true", "yes"}
