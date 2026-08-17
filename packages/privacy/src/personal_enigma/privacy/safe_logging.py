"""Redaction-first logging helpers for Private mode (ADR-022)."""

from __future__ import annotations

import hashlib
import json
import os
import re
from typing import Any

ENV_DEBUG_RAW_LOGGING = "ENIGMA_DEBUG_RAW_LOGGING"

_EMAIL_RE = re.compile(r"\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}\b")
_BEARER_RE = re.compile(r"Bearer\s+[A-Za-z0-9\-._~+/]+=*", re.IGNORECASE)
_REFRESH_TOKEN_RE = re.compile(r"ya29\.[A-Za-z0-9\-._~+/]+", re.IGNORECASE)

_SENSITIVE_KEY_SUBSTRINGS = (
    "token",
    "secret",
    "password",
    "refresh",
    "body",
    "subject",
    "attachment",
    "prompt",
    "email",
    "oauth",
    "api_key",
)


def debug_raw_logging_enabled() -> bool:
    """True when explicit dev switch allows raw private content in logs."""
    return os.environ.get(ENV_DEBUG_RAW_LOGGING, "").strip() == "1"


def content_hash(value: str | bytes) -> str:
    """Return SHA-256 hex digest suitable for log fields."""
    data = value.encode("utf-8") if isinstance(value, str) else value
    return hashlib.sha256(data).hexdigest()


def redact_string(value: str) -> str:
    """Redact obvious secret / PII patterns from a string."""
    if debug_raw_logging_enabled():
        return value
    redacted = _BEARER_RE.sub("Bearer [REDACTED]", value)
    redacted = _REFRESH_TOKEN_RE.sub("[REDACTED_OAUTH_TOKEN]", redacted)
    redacted = _EMAIL_RE.sub("[REDACTED_EMAIL]", redacted)
    return redacted


def safe_log_fields(**fields: Any) -> dict[str, Any]:
    """Build a log-safe dict — ids/hashes/metadata only unless debug switch is on."""
    if debug_raw_logging_enabled():
        return dict(fields)
    safe: dict[str, Any] = {}
    for key, value in fields.items():
        lower_key = key.lower()
        if any(part in lower_key for part in _SENSITIVE_KEY_SUBSTRINGS):
            if isinstance(value, (str, bytes)):
                safe[key] = content_hash(value)
            else:
                safe[key] = "[REDACTED]"
            continue
        if isinstance(value, str):
            safe[key] = redact_string(value)
        elif isinstance(value, bytes):
            safe[key] = content_hash(value)
        elif isinstance(value, dict):
            safe[key] = safe_log_fields(**value)
        else:
            safe[key] = value
    return safe


def format_safe_log_event(event: str, **fields: Any) -> str:
    """JSON log line with redaction applied."""
    payload = {"event": event, **safe_log_fields(**fields)}
    return json.dumps(payload, sort_keys=True, default=str)
