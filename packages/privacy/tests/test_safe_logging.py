"""Safe logging redaction tests."""

from __future__ import annotations

import json

import pytest

from personal_enigma.privacy.safe_logging import (
    format_safe_log_event,
    redact_string,
    safe_log_fields,
)


def test_safe_log_fields_redacts_sensitive_keys(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.delenv("ENIGMA_DEBUG_RAW_LOGGING", raising=False)
    fields = safe_log_fields(
        record_id="src_123",
        email_body="secret body text",
        refresh_token="ya29.super_secret_token_value",
        duration_ms=12,
    )
    assert fields["record_id"] == "src_123"
    assert fields["duration_ms"] == 12
    assert "secret body" not in str(fields["email_body"])
    assert "ya29." not in str(fields["refresh_token"])


def test_debug_switch_allows_raw_values(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("ENIGMA_DEBUG_RAW_LOGGING", "1")
    raw = "oscar.hilts@example.com"
    assert redact_string(raw) == raw
    fields = safe_log_fields(email_body=raw)
    assert fields["email_body"] == raw


def test_format_safe_log_event_is_json_without_raw_body(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.delenv("ENIGMA_DEBUG_RAW_LOGGING", raising=False)
    line = format_safe_log_event(
        "ingest_complete",
        record_id="r1",
        subject="Private subject line",
        body="Full email body must not appear",
    )
    payload = json.loads(line)
    assert payload["event"] == "ingest_complete"
    assert payload["record_id"] == "r1"
    blob = json.dumps(payload)
    assert "Full email body must not appear" not in blob
    assert "Private subject line" not in blob
