"""Privacy gate: only TransformedContext may leave the machine via PAYG."""

from __future__ import annotations

import re
from typing import Any

from personal_enigma.reasoning.errors import PrivacyGateError
from personal_enigma.transformation import TransformedContext
from personal_enigma.transformation.title_sanitisation import assert_no_raw_identity_in_text

# Raw attendee / contact emails must never appear in remote payloads.
_EMAIL_RE = re.compile(r"\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}\b")
_PHONE_RE = re.compile(
    r"(?<!\w)(?:\+?\d{1,3}[\s.-]?)?(?:\(?\d{3}\)?[\s.-]?)?\d{3}[\s.-]?\d{4}(?!\w)"
)

# Domain private model type names that must not be smuggled through metadata.
_FORBIDDEN_TYPE_MARKERS = (
    "PrivatePerson",
    "PrivateNote",
    "PrivateCalendarEvent",
    "PrivateReminder",
    "PrivateMessage",
)


def assert_remote_safe(payload: Any) -> TransformedContext:
    """Validate ``payload`` is a remote-safe ``TransformedContext``.

    Raises:
        PrivacyGateError: if the payload is unsanitised or not cleared for remote send.
    """
    if not isinstance(payload, TransformedContext):
        raise PrivacyGateError(
            "PAYG reasoning only accepts TransformedContext; "
            f"got {type(payload).__name__}"
        )

    if not payload.may_transmit_remotely:
        raise PrivacyGateError(
            "privacy gate refused remote transmission "
            "(TransformedContext.may_transmit_remotely is False)"
        )

    _reject_forbidden_markers(payload)
    _reject_raw_emails(payload)
    _reject_raw_phones(payload)
    _reject_raw_identity(payload)
    return payload


def _reject_forbidden_markers(context: TransformedContext) -> None:
    blob = _flatten_text(context)
    for marker in _FORBIDDEN_TYPE_MARKERS:
        if marker in blob:
            raise PrivacyGateError(
                f"privacy gate refused unsanitised payload containing {marker!r}"
            )


def _reject_raw_emails(context: TransformedContext) -> None:
    blob = _flatten_text(context)
    match = _EMAIL_RE.search(blob)
    if match is not None:
        raise PrivacyGateError(
            "privacy gate refused raw email address in TransformedContext "
            f"({match.group(0)!r})"
        )


def _reject_raw_phones(context: TransformedContext) -> None:
    blob = _flatten_text(context)
    match = _PHONE_RE.search(blob)
    if match is not None:
        raise PrivacyGateError(
            "privacy gate refused raw phone number in TransformedContext "
            f"({match.group(0)!r})"
        )


def _reject_raw_identity(context: TransformedContext) -> None:
    blob = _flatten_text(context)
    try:
        assert_no_raw_identity_in_text(blob)
    except ValueError as exc:
        raise PrivacyGateError(str(exc)) from exc


def _flatten_text(context: TransformedContext) -> str:
    parts: list[str] = [context.summary, *context.entities]
    for rel in context.relations:
        parts.append(rel.model_dump_json())
    for key, value in context.metadata.items():
        parts.append(str(key))
        parts.append(str(value))
    return "\n".join(parts)
