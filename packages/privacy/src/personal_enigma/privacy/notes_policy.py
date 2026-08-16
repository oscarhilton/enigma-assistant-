"""Notes remote policy: default HIGH; wholesale body never remote-safe by default."""

from __future__ import annotations

from dataclasses import dataclass

from personal_enigma.domain import SourceType
from personal_enigma.privacy.levels import PrivacyLevel, default_level_for_source


@dataclass(frozen=True, slots=True)
class NotesRemotePolicyException:
    """Explicit, audited exception to allow a *passage* (never wholesale body).

    ``passage_only`` is always True: this type cannot authorise shipping the
    full note body to a hosted model.
    """

    note_id: str
    reason: str
    passage_only: bool = True

    def __post_init__(self) -> None:
        if not self.passage_only:
            raise ValueError("NotesRemotePolicyException cannot set passage_only=False")
        if not self.reason.strip():
            raise ValueError("NotesRemotePolicyException requires a non-empty reason")


def notes_default_privacy_level() -> PrivacyLevel:
    """Notes default remote privacy level (always HIGH)."""
    level = default_level_for_source(SourceType.NOTE)
    assert level is PrivacyLevel.HIGH
    return level


def wholesale_note_body_remote_safe(
    *,
    body_text: str,
    candidate_text: str,
    exception: NotesRemotePolicyException | None = None,
) -> bool:
    """Return whether ``candidate_text`` may be treated as remote-safe for a note.

    Always False when ``candidate_text`` contains the wholesale note body.
    Without an explicit :class:`NotesRemotePolicyException`, always False.
    Even with an exception, only a strict passage (not the full body) may pass.
    """
    wholesale = body_text.strip()
    candidate = candidate_text.strip()
    if not wholesale or not candidate:
        return False
    if wholesale in candidate or candidate == wholesale:
        return False
    if exception is None:
        return False
    if not exception.passage_only:
        return False
    return len(candidate) < len(wholesale)
