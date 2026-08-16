"""Classify mail asks: commitment vs pending reply vs noise."""

from __future__ import annotations

import re

from personal_enigma.attention.kinds import AttentionKind
from personal_enigma.attention.noise import (
    looks_like_machine_noise,
    looks_like_newsletter,
    looks_like_package_notification,
)
from personal_enigma.domain import PrivateMessage

_COMMITMENT_RE = re.compile(
    r"\b("
    r"i('ll| will)|we('ll| will)|need (you )?to|please (send|review|confirm|share)|"
    r"action required|by (monday|tuesday|wednesday|thursday|friday|saturday|sunday)|"
    r"due |deadline|can you (review|send|share|draft)|still on for"
    r")\b",
    re.IGNORECASE,
)

_QUESTION_RE = re.compile(
    r"(\?$|^(can|could|would|will|are|is|do|did|have|should|when|where|what)\b)",
    re.IGNORECASE | re.MULTILINE,
)


def message_attention_kind(message: PrivateMessage) -> AttentionKind | None:
    """Map a message to an attention kind, or ``None`` to suppress entirely.

    Noise / newsletter / package mail → ``None``.
    Unanswered social questions → ``PENDING_REPLY``.
    Otherwise weak ``INFERRED_COMMITMENT``.
    """
    if (
        looks_like_machine_noise(message)
        or looks_like_newsletter(message)
        or looks_like_package_notification(message)
    ):
        return None

    subject = message.subject or ""
    body = message.body_text or message.snippet or ""
    blob = f"{subject}\n{body}".strip()
    if not blob:
        return None

    if _COMMITMENT_RE.search(blob):
        return AttentionKind.INFERRED_COMMITMENT

    subject_stripped = subject.strip()
    if subject_stripped.endswith("?") or _QUESTION_RE.search(subject_stripped):
        return AttentionKind.PENDING_REPLY

    # Default: do not promote ambient threads to commitments (0.55 spam).
    if _QUESTION_RE.search(blob):
        return AttentionKind.PENDING_REPLY

    return None
