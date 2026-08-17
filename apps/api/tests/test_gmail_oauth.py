"""Smoke tests for Gmail OAuth stubs."""

import pytest

from personal_enigma.api.google.gmail.oauth import (
    GMAIL_READONLY_SCOPE,
    GmailOAuthConfig,
    GmailScopeError,
    gmail_oauth_configured,
    gmail_oauth_live_allowed,
    gmail_oauth_start,
    validate_gmail_oauth_scopes,
)


def test_gmail_oauth_not_configured_by_default() -> None:
    assert gmail_oauth_configured(GmailOAuthConfig()) is False


def test_gmail_oauth_start_builds_authorize_url() -> None:
    config = GmailOAuthConfig(client_id="client", client_secret="secret")
    start = gmail_oauth_start(config, state="xyz")
    assert start.state == "xyz"
    assert "client_id=client" in start.authorize_url
    assert "gmail.readonly" in start.scope


def test_gmail_oauth_rejects_modify_scope_in_config() -> None:
    config = GmailOAuthConfig(
        client_id="client",
        client_secret="secret",
        scopes=(
            GMAIL_READONLY_SCOPE,
            "https://www.googleapis.com/auth/gmail.modify",
        ),
    )
    with pytest.raises(GmailScopeError, match="exceed gmail.readonly"):
        gmail_oauth_start(config, state="abc")


def test_validate_gmail_oauth_scopes_readonly_only() -> None:
    validate_gmail_oauth_scopes(GMAIL_READONLY_SCOPE)


def test_gmail_live_disabled_by_default(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.delenv("ENIGMA_GMAIL_LIVE", raising=False)
    assert gmail_oauth_live_allowed() is False
