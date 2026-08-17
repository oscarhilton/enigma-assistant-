"""SEC-04 Gmail readonly scope audit — no write endpoints in connector code."""

from __future__ import annotations

import inspect
from pathlib import Path

import pytest

from personal_enigma.ingestion.sources.gmail import (
    FORBIDDEN_GMAIL_WRITE_PATHS,
    GMAIL_READONLY_SCOPE,
    GmailError,
    GmailSource,
)


def test_readonly_scope_constant() -> None:
    assert GMAIL_READONLY_SCOPE == "https://www.googleapis.com/auth/gmail.readonly"


def test_forbidden_write_paths_defined() -> None:
    assert "/users/me/messages/send" in FORBIDDEN_GMAIL_WRITE_PATHS
    assert "/users/me/messages/trash" in FORBIDDEN_GMAIL_WRITE_PATHS


def test_gmail_source_refuses_write_paths() -> None:
    source = GmailSource(access_token="token")
    with pytest.raises(GmailError, match="write path refused"):
        source._assert_readonly_path("/users/me/messages/send")
    with pytest.raises(GmailError, match="write path refused"):
        source._assert_readonly_path("/users/me/messages/trash")


def test_gmail_source_allows_read_paths() -> None:
    source = GmailSource(access_token="token")
    source._assert_readonly_path("/users/me/messages/msg_1")
    source._assert_readonly_path("/users/me/history")


def test_connector_source_has_no_post_put_delete() -> None:
    """Static audit — connector uses GET-only Gmail API surface."""
    gmail_path = Path(inspect.getfile(GmailSource)).resolve()
    text = gmail_path.read_text(encoding="utf-8")
    assert ".post(" not in text
    assert ".put(" not in text
    assert ".delete(" not in text
    assert "FORBIDDEN_GMAIL_WRITE_PATHS" in text
