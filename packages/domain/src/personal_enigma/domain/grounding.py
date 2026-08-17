"""Grounded evidence primitives for proposition-shaped truth handling."""

from __future__ import annotations

from datetime import datetime
from enum import StrEnum
from typing import Any

from pydantic import BaseModel, Field

from personal_enigma.domain.retention import RetentionClass


class EpistemicStatus(StrEnum):
    """How Enigma knows a proposition, independent of confidence."""

    USER_REPORTED = "user_reported"
    USER_CONFIRMED = "user_confirmed"
    SOURCE_OBSERVED = "source_observed"
    EXTERNALLY_VERIFIED = "externally_verified"
    SYSTEM_VERIFIED = "system_verified"
    DETERMINISTICALLY_DERIVED = "deterministically_derived"
    USER_UNCERTAIN = "user_uncertain"
    MODEL_INFERRED = "model_inferred"
    CONFLICTED = "conflicted"
    STALE = "stale"
    UNKNOWN = "unknown"


class AssertionKind(StrEnum):
    """Promotion boundary for what a proposition represents."""

    FACT = "fact"
    HYPOTHESIS = "hypothesis"
    PATTERN = "pattern"
    PREFERENCE = "preference"
    DELEGATION = "delegation"


class AssertionSensitivity(StrEnum):
    LOW = "low"
    PERSONAL = "personal"
    HIGH = "high"


class AssertionEgressClass(StrEnum):
    REMOTE_SAFE = "remote_safe"
    LOCAL_ONLY = "local_only"


class UnknownReason(StrEnum):
    MISSING_EVIDENCE = "missing_evidence"
    CONFLICTING_EVIDENCE = "conflicting_evidence"
    UNRESOLVED_REFERENT = "unresolved_referent"
    UNAVAILABLE_CAPABILITY = "unavailable_capability"
    STALE = "stale"


class ChallengeDisposition(StrEnum):
    CONFIRMS = "confirms"
    QUALIFIES = "qualifies"
    CONFLICTS = "conflicts"
    DOES_NOT_ADDRESS = "does_not_address"


class GroundedAssertion(BaseModel):
    """Inspectable proposition with provenance and retention metadata."""

    id: str
    kind: AssertionKind = AssertionKind.FACT
    subject: str
    predicate: str
    value: Any
    epistemic_status: EpistemicStatus
    confidence: float | None = None
    evidence_refs: list[str] = Field(default_factory=list)
    observed_at: datetime | None = None
    valid_from: datetime | None = None
    valid_until: datetime | None = None
    sensitivity: AssertionSensitivity = AssertionSensitivity.PERSONAL
    purpose_tags: list[str] = Field(default_factory=list)
    retention_class: RetentionClass = RetentionClass.EPHEMERAL_ANSWER_ONLY
    egress_class: AssertionEgressClass = AssertionEgressClass.REMOTE_SAFE
    derived_from: list[str] = Field(default_factory=list)
    supersedes: list[str] = Field(default_factory=list)


class EvidenceUnknown(BaseModel):
    """A proposition Enigma knows it has not established yet."""

    subject: str
    predicate: str
    reason: UnknownReason
    missing_sources: list[str] = Field(default_factory=list)


class AssertionChallenge(BaseModel):
    """How current evidence relates to a material claim or conclusion."""

    subject: str
    predicate: str
    disposition: ChallengeDisposition
    summary: str
    evidence_refs: list[str] = Field(default_factory=list)


__all__ = [
    "AssertionChallenge",
    "AssertionEgressClass",
    "AssertionKind",
    "AssertionSensitivity",
    "ChallengeDisposition",
    "EpistemicStatus",
    "EvidenceUnknown",
    "GroundedAssertion",
    "UnknownReason",
]
