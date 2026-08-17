"""SEC-04 nasty mailbox fixture manifest regression."""

from __future__ import annotations

from personal_enigma.fixtures.adversarial_email_cases import ADVERSARIAL_EMAIL_CASES
from personal_enigma.fixtures.alex_sensitive_canaries import ALEX_SENSITIVE_CANARIES
from personal_enigma.fixtures.nasty_mailbox_manifest import (
    NASTY_MAILBOX_MATRIX,
    REQUIRED_CATEGORIES,
    NastyMailboxCategory,
    assert_nasty_mailbox_manifest_complete,
    matrix_summary,
)


def test_nasty_mailbox_manifest_complete() -> None:
    assert_nasty_mailbox_manifest_complete()


def test_every_required_category_present() -> None:
    covered = {entry.category for entry in NASTY_MAILBOX_MATRIX}
    assert covered == set(REQUIRED_CATEGORIES)


def test_matrix_includes_all_canary_secrets() -> None:
    canary_rows = [
        entry
        for entry in NASTY_MAILBOX_MATRIX
        if entry.category == NastyMailboxCategory.CANARY_SECRETS
    ]
    assert len(canary_rows) == len(ALEX_SENSITIVE_CANARIES)


def test_matrix_references_known_adversarial_cases() -> None:
    adversarial_ids = {case.case_id for case in ADVERSARIAL_EMAIL_CASES}
    for entry in NASTY_MAILBOX_MATRIX:
        if entry.adversarial_case_id is not None:
            assert entry.adversarial_case_id in adversarial_ids


def test_matrix_summary_row_count() -> None:
    assert len(matrix_summary()) == len(NASTY_MAILBOX_MATRIX)
