"""User attestation — append-only evidence that the private world changed.

Reports are evidence. Commands grant authority. Recording a report does not
require an approval ceremony and does not perform external mutations.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Literal
from uuid import uuid4

from personal_enigma.attention.projection import AttentionState, NextActionView

AttestedState = Literal["COMPLETED", "OPEN", "CANCELLED"]
AttestationEvidence = Literal["USER_ATTESTED", "EXTERNALLY_VERIFIED"]

ATTESTATION_TOOL = "world.record_user_attestation"


@dataclass
class UserAttestation:
    """One append-only user report. Later rows for the same target supersede."""

    id: str
    target_id: str
    state: AttestedState
    evidence: AttestationEvidence = "USER_ATTESTED"
    recorded_at: str = ""
    supersedes: str | None = None
    utterance: str = ""


def latest_attestation(
    attestations: list[UserAttestation],
    target_id: str,
) -> UserAttestation | None:
    for row in reversed(attestations):
        if row.target_id == target_id:
            return row
    return None


def drop_cached_next_actions(
    advances: dict[str, NextActionView],
    target_id: str,
) -> None:
    """Drop any cached NextActionView keyed by or pointing at ``target_id``."""
    advances.pop(target_id, None)
    advances.pop(f"next-{target_id}", None)
    for key in list(advances):
        row = advances[key]
        if (
            row.id == target_id
            or row.id == f"next-{target_id}"
            or (row.source_candidate_id or "") == target_id
        ):
            advances.pop(key, None)


def apply_user_attestation(
    *,
    attestations: list[UserAttestation],
    completed_item_ids: set[str],
    advances: dict[str, NextActionView],
    target_id: str,
    state: AttestedState,
    at: str,
    utterance: str = "",
    evidence: AttestationEvidence = "USER_ATTESTED",
) -> UserAttestation:
    """Append evidence and project obligation status. Frozen snapshots untouched.

    COMPLETED / CANCELLED → leave next-action projection.
    OPEN → supersede a prior completion; obligation becomes actionable again.
    Cached NextActionView for the target is always dropped; callers must
    re-overlay from the frozen checkpoint, not from a stripped copy.
    """
    previous = latest_attestation(attestations, target_id)
    record = UserAttestation(
        id=f"attest-{uuid4().hex[:12]}",
        target_id=target_id,
        state=state,
        evidence=evidence,
        recorded_at=at,
        supersedes=previous.id if previous is not None else None,
        utterance=utterance,
    )
    attestations.append(record)
    drop_cached_next_actions(advances, target_id)
    if state in {"COMPLETED", "CANCELLED"}:
        completed_item_ids.add(target_id)
    elif state == "OPEN":
        completed_item_ids.discard(target_id)
    return record


def attestation_title(state: AttentionState, target_id: str) -> str:
    """Best-effort label from the live projection — never invents a new fact."""
    for item in (*state.needs_you, *state.context):
        if item.id == target_id:
            return item.title
    for action in state.next_actions:
        if action.id == target_id or action.source_candidate_id == target_id:
            return action.title
    return "that"


__all__ = [
    "ATTESTATION_TOOL",
    "AttestationEvidence",
    "AttestedState",
    "UserAttestation",
    "apply_user_attestation",
    "attestation_title",
    "drop_cached_next_actions",
    "latest_attestation",
]
