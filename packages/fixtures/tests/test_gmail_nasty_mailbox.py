"""Regression tests for gmail_nasty_mailbox catalog."""

from __future__ import annotations

from personal_enigma.fixtures.adversarial_email_cases import ContainmentLayer
from personal_enigma.fixtures.gmail_nasty_mailbox import NASTY_MAILBOX_MESSAGES
from personal_enigma.fixtures.nasty_mailbox_manifest import NASTY_MAILBOX_MATRIX


def test_catalog_matches_manifest_row_count() -> None:
    assert len(NASTY_MAILBOX_MESSAGES) == len(NASTY_MAILBOX_MATRIX)


def test_every_message_has_containment_layers() -> None:
    for row in NASTY_MAILBOX_MESSAGES:
        assert row.expected_containment_layers
        assert all(isinstance(layer, ContainmentLayer) for layer in row.expected_containment_layers)


def test_canary_rows_expect_egress_containment() -> None:
    canary_rows = [row for row in NASTY_MAILBOX_MESSAGES if row.body_ref_kind.value == "canary"]
    assert canary_rows
    for row in canary_rows:
        assert ContainmentLayer.EGRESS in row.expected_containment_layers
