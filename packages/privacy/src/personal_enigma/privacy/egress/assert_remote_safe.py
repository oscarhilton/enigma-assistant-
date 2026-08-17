"""Runtime guard — only REMOTE_SAFE payloads may cross the egress boundary."""

from __future__ import annotations

import re
from typing import Any

from personal_enigma.privacy.egress.classification import PrivateDerived, PrivateRaw
from personal_enigma.privacy.egress.errors import EgressBlockedError
from personal_enigma.privacy.invariants import PrivacyInvariantError, assert_remote_payload_safe
from personal_enigma.transformation import TransformedContext

_EMAIL_RE = re.compile(r"\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}\b")
_PHONE_RE = re.compile(
    r"(?<!\w)(?:\+?\d{1,3}[\s.-]?)?(?:\(?\d{3}\)?[\s.-]?)?\d{3}[\s.-]?\d{4}(?!\w)"
)
_RAW_POSSESSIVE_LEAK = re.compile(r"\b[A-Z][a-z]+'s\b")
_FORBIDDEN_TYPE_MARKERS = (
    "PrivatePerson",
    "PrivateNote",
    "PrivateCalendarEvent",
    "PrivateReminder",
    "PrivateMessage",
)


def assert_remote_safe(payload: Any) -> TransformedContext:
    """Validate ``payload`` immediately before transmission.

    Raises:
        EgressBlockedError: if the payload is unsanitised or not cleared for remote send.
    """
    if isinstance(payload, PrivateRaw):
        raise EgressBlockedError(
            "PRIVATE_RAW cannot cross egress gate — transform to REMOTE_SAFE first"
        )
    if isinstance(payload, PrivateDerived):
        raise EgressBlockedError(
            "PRIVATE_DERIVED cannot cross egress gate — transform to REMOTE_SAFE first"
        )
    if isinstance(payload, str):
        raise EgressBlockedError(
            "raw string payloads cannot cross egress gate — wrap as RemoteSafeContext"
        )
    if not isinstance(payload, TransformedContext):
        raise EgressBlockedError(
            "egress gate only accepts TransformedContext or RemoteSafeContext; "
            f"got {type(payload).__name__}"
        )

    if not payload.may_transmit_remotely:
        raise EgressBlockedError(
            "privacy gate refused remote transmission "
            "(TransformedContext.may_transmit_remotely is False)"
        )

    try:
        assert_remote_payload_safe(payload)
        _reject_forbidden_markers(payload)
        _reject_raw_emails(payload)
        _reject_raw_phones(payload)
        _reject_raw_identity(payload)
    except PrivacyInvariantError as exc:
        raise EgressBlockedError(str(exc)) from exc
    return payload


def _flatten_text(context: TransformedContext) -> str:
    parts: list[str] = [context.summary, *context.entities]
    for rel in getattr(context, "relations", None) or []:
        parts.append(rel.model_dump_json())
    for key, value in context.metadata.items():
        parts.append(str(key))
        parts.append(str(value))
    return "\n".join(parts)


def _reject_forbidden_markers(context: TransformedContext) -> None:
    blob = _flatten_text(context)
    for marker in _FORBIDDEN_TYPE_MARKERS:
        if marker in blob:
            raise EgressBlockedError(
                f"privacy gate refused unsanitised payload containing {marker!r}"
            )


def _reject_raw_emails(context: TransformedContext) -> None:
    blob = _flatten_text(context)
    match = _EMAIL_RE.search(blob)
    if match is not None:
        raise EgressBlockedError(
            "privacy gate refused raw email address in TransformedContext "
            f"({match.group(0)!r})"
        )


def _reject_raw_phones(context: TransformedContext) -> None:
    blob = _flatten_text(context)
    match = _PHONE_RE.search(blob)
    if match is not None:
        raise EgressBlockedError(
            "privacy gate refused raw phone number in TransformedContext "
            f"({match.group(0)!r})"
        )


def _reject_raw_identity(context: TransformedContext) -> None:
    blob = _flatten_text(context)
    if _RAW_POSSESSIVE_LEAK.search(blob):
        raise EgressBlockedError(
            "privacy gate refused raw possessive identity in TransformedContext"
        )
