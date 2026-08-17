"""Tests for remote-safe title pseudonymisation (R-L09)."""

from __future__ import annotations

import pytest

from personal_enigma.transformation.title_sanitisation import (
    assert_no_raw_identity_in_text,
    pseudonymise_remote_text,
)


def test_possessive_name_becomes_pseudonym() -> None:
    out = pseudonymise_remote_text("Book Saturday brunch for Elena's parents")
    assert "Elena" not in out
    assert "PERSON_" in out
    assert_no_raw_identity_in_text(out)


def test_reply_to_name_becomes_pseudonym() -> None:
    out = pseudonymise_remote_text("Reply to Sam on empty-state decision")
    assert "Sam" not in out
    assert "PERSON_" in out


def test_assert_no_raw_identity_rejects_leak() -> None:
    with pytest.raises(ValueError, match="raw possessive"):
        assert_no_raw_identity_in_text("Meeting with Elena's team")
