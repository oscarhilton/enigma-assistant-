"""Privacy gate rejects raw identity in remote-safe context."""

from __future__ import annotations

import pytest

from personal_enigma.reasoning.errors import PrivacyGateError
from personal_enigma.reasoning.privacy_gate import assert_remote_safe
from personal_enigma.transformation import TransformedContext


def test_privacy_gate_rejects_possessive_identity_in_summary() -> None:
    ctx = TransformedContext(
        summary="Book brunch for Elena's parents",
        entities=[],
        metadata={"source_type": "email"},
        may_transmit_remotely=True,
    )
    with pytest.raises(PrivacyGateError, match="raw possessive"):
        assert_remote_safe(ctx)
