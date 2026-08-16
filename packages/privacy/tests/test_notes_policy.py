"""Notes HIGH default / passage policy tests (M13 / ADR-004)."""

from __future__ import annotations

import pytest

from personal_enigma.privacy.levels import PrivacyLevel
from personal_enigma.privacy.notes_policy import (
    NotesRemotePolicyException,
    extract_passage_stub,
    local_relevance_passages,
    may_transmit_note_remotely_by_default,
    notes_default_privacy_level,
    wholesale_note_body_remote_safe,
)


def test_notes_default_privacy_is_high() -> None:
    assert notes_default_privacy_level() is PrivacyLevel.HIGH


def test_full_body_never_may_transmit_remotely_by_default() -> None:
    body = "Secret diary line that must not ship wholesale."
    assert may_transmit_note_remotely_by_default(body_text=body) is False
    assert local_relevance_passages(body_text=body) == []
    assert extract_passage_stub(body) is None
    assert (
        wholesale_note_body_remote_safe(
            body_text=body,
            candidate_text=body,
            exception=None,
        )
        is False
    )


def test_wholesale_body_rejected_even_with_passage_exception() -> None:
    body = "First paragraph only.\n\n" + ("pad " * 50)
    exc = NotesRemotePolicyException(note_id="n1", reason="audited passage")
    assert (
        wholesale_note_body_remote_safe(
            body_text=body,
            candidate_text=body,
            exception=exc,
        )
        is False
    )
    assert (
        wholesale_note_body_remote_safe(
            body_text=body,
            candidate_text="First paragraph only.",
            exception=exc,
        )
        is True
    )
    assert (
        wholesale_note_body_remote_safe(
            body_text=body,
            candidate_text="Unrelated shorter text",
            exception=exc,
        )
        is False
    )


def test_notes_policy_exception_rejects_wholesale_flag() -> None:
    with pytest.raises(ValueError, match="passage_only"):
        NotesRemotePolicyException(note_id="n", reason="x", passage_only=False)


def test_notes_policy_exception_requires_reason() -> None:
    with pytest.raises(ValueError, match="reason"):
        NotesRemotePolicyException(note_id="n", reason="   ")
