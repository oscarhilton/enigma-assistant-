"""Smoke tests for Gmail OAuth stubs."""

from personal_enigma.api.google.gmail import (
    GmailOAuthConfig,
    gmail_oauth_configured,
    gmail_oauth_start,
)


def test_gmail_oauth_not_configured_by_default() -> None:
    assert gmail_oauth_configured(GmailOAuthConfig()) is False


def test_gmail_oauth_start_builds_authorize_url() -> None:
    config = GmailOAuthConfig(client_id="client", client_secret="secret")
    start = gmail_oauth_start(config, state="xyz")
    assert start.state == "xyz"
    assert "client_id=client" in start.authorize_url
    assert "gmail.readonly" in start.scope
