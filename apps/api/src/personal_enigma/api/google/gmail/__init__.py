"""Gmail Google API surface for Enigma Core (OAuth + SEC-04 pipeline)."""

from personal_enigma.api.google.gmail.oauth import (
    ALLOWED_GMAIL_SCOPES,
    GmailOAuthConfig,
    GmailOAuthStart,
    GmailScopeError,
    gmail_oauth_configured,
    gmail_oauth_live_allowed,
    gmail_oauth_start,
    validate_gmail_oauth_scopes,
)
from personal_enigma.api.google.gmail.pipeline import (
    GmailIngestResult,
    gmail_live_sync_enabled,
    ingest_gmail_to_vault,
)

__all__ = [
    "ALLOWED_GMAIL_SCOPES",
    "GmailIngestResult",
    "GmailOAuthConfig",
    "GmailOAuthStart",
    "GmailScopeError",
    "gmail_live_sync_enabled",
    "gmail_oauth_configured",
    "gmail_oauth_live_allowed",
    "gmail_oauth_start",
    "ingest_gmail_to_vault",
    "validate_gmail_oauth_scopes",
]
