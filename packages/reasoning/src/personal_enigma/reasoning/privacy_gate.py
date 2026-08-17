"""Privacy gate: only TransformedContext may leave the machine via PAYG."""

from __future__ import annotations

from typing import Any

from personal_enigma.privacy.egress import assert_remote_safe as _assert_remote_safe
from personal_enigma.privacy.egress.errors import EgressBlockedError
from personal_enigma.reasoning.errors import PrivacyGateError
from personal_enigma.transformation import TransformedContext


def assert_remote_safe(payload: Any) -> TransformedContext:
    """Validate ``payload`` is a remote-safe ``TransformedContext``.

    Raises:
        PrivacyGateError: if the payload is unsanitised or not cleared for remote send.
    """
    try:
        return _assert_remote_safe(payload)
    except EgressBlockedError as exc:
        raise PrivacyGateError(str(exc)) from exc
