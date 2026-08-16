"""Privacy inspector — preview what would leave the machine (M17)."""

from __future__ import annotations

from typing import Any

from pydantic import BaseModel, Field

from personal_enigma.domain import SourceType
from personal_enigma.privacy.allowlist import REMOTE_PAYLOAD_ALLOWLIST_DOC
from personal_enigma.privacy.invariants import (
    PrivacyInvariantError,
    assert_remote_payload_safe,
)
from personal_enigma.privacy.levels import PrivacyLevel, default_level_for_source
from personal_enigma.privacy.remote import RemoteInferenceConfig, may_send_remotely
from personal_enigma.transformation import TransformedContext


class RedactionNote(BaseModel):
    field: str
    reason: str


class InspectionResult(BaseModel):
    """What the user sees before any remote send."""

    would_send: dict[str, Any] | None = None
    privacy_level: PrivacyLevel
    source_type: SourceType | None = None
    redactions: list[RedactionNote] = Field(default_factory=list)
    allowlist_doc: str = REMOTE_PAYLOAD_ALLOWLIST_DOC
    apple_permission_note: str = (
        "Revoking Calendar, Reminders, Contacts, or Notes in System Settings "
        "stops new ingestion for that source; already-local data remains until deleted."
    )
    can_send: bool = False
    blocked_reason: str | None = None
    cancelled: bool = False


def inspect_transformed_context(
    ctx: TransformedContext,
    *,
    source_type: SourceType | None = None,
    remote: RemoteInferenceConfig | None = None,
    cancel: bool = False,
) -> InspectionResult:
    """Build an inspection preview; never uploads."""
    level = (
        default_level_for_source(source_type)
        if source_type is not None
        else PrivacyLevel.MEDIUM
    )
    remote = remote or RemoteInferenceConfig(enabled=False)
    redactions: list[RedactionNote] = []
    if not ctx.may_transmit_remotely:
        redactions.append(
            RedactionNote(
                field="may_transmit_remotely",
                reason="Context marked local-only; remote send refused",
            )
        )
    if source_type == SourceType.NOTE:
        redactions.append(
            RedactionNote(
                field="body_text",
                reason="Notes default HIGH — only minimal passages may ever be considered",
            )
        )

    if cancel:
        return InspectionResult(
            would_send=None,
            privacy_level=level,
            source_type=source_type,
            redactions=redactions,
            can_send=False,
            blocked_reason="User cancelled remote send",
            cancelled=True,
        )

    metadata = {
        k: str(v)
        for k, v in ctx.metadata.items()
        if k in {"source_type", "provider", "passage_chars", "record_id"}
    }
    if source_type is not None:
        metadata.setdefault("source_type", source_type.value)
    payload = {
        "summary": ctx.summary,
        "entities": list(ctx.entities),
        "metadata": metadata,
        "may_transmit_remotely": ctx.may_transmit_remotely,
    }

    # Surface obvious emails left in summary as blocked (inspector preview honesty).
    if "@" in ctx.summary:
        return InspectionResult(
            would_send=None,
            privacy_level=level,
            source_type=source_type,
            redactions=redactions
            + [RedactionNote(field="summary", reason="Email address detected in summary")],
            can_send=False,
            blocked_reason="Email address detected in summary",
        )

    try:
        assert_remote_payload_safe(payload)
    except PrivacyInvariantError as exc:
        return InspectionResult(
            would_send=None,
            privacy_level=level,
            source_type=source_type,
            redactions=redactions,
            can_send=False,
            blocked_reason=str(exc),
        )

    if not may_send_remotely(remote, payload_allows_remote=ctx.may_transmit_remotely):
        return InspectionResult(
            would_send=payload,
            privacy_level=level,
            source_type=source_type,
            redactions=redactions,
            can_send=False,
            blocked_reason="Remote inference disabled or context not cleared for transmit",
        )

    return InspectionResult(
        would_send=payload,
        privacy_level=level,
        source_type=source_type,
        redactions=redactions,
        can_send=True,
    )
