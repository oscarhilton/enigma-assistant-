"""Grounded evidence primitives for proposition-shaped truth handling."""

from __future__ import annotations

import hashlib
import json
from datetime import datetime
from enum import StrEnum
from typing import Any

from pydantic import BaseModel, Field, model_validator

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


class AssertionValidityKind(StrEnum):
    """How an assertion remains usable over time."""

    STABLE = "stable"
    TTL = "ttl"
    UNTIL_EVENT = "until_event"
    SOURCE_LIFETIME = "source_lifetime"
    DERIVED_LIFETIME = "derived_lifetime"


class AssertionUsability(StrEnum):
    """Whether an assertion is currently safe to use."""

    CURRENT = "current"
    STALE = "stale"
    SUPERSEDED = "superseded"


class DerivationKind(StrEnum):
    """How a derived assertion was produced."""

    DIRECT_OBSERVATION = "direct_observation"
    USER_CONFIRMATION = "user_confirmation"
    SOURCE_CONFIRMATION = "source_confirmation"
    DETERMINISTIC_RULE = "deterministic_rule"
    INFERENCE = "inference"
    SEMANTIC_SIMILARITY = "semantic_similarity"
    DIALOGUE_HISTORY = "dialogue_history"
    HIGH_CONFIDENCE = "high_confidence"


class GroundedAssertion(BaseModel):
    """Inspectable proposition with provenance and retention metadata."""

    id: str
    kind: AssertionKind = AssertionKind.FACT
    subject: str
    predicate: str
    value: Any
    scope: str | None = None
    epistemic_status: EpistemicStatus
    confidence: float | None = None
    evidence_refs: list[str] = Field(default_factory=list)
    observed_at: datetime | None = None
    valid_from: datetime | None = None
    valid_until: datetime | None = None
    temporal_scope: str | None = None
    validity_kind: AssertionValidityKind = AssertionValidityKind.STABLE
    sensitivity: AssertionSensitivity = AssertionSensitivity.PERSONAL
    purpose_tags: list[str] = Field(default_factory=list)
    retention_class: RetentionClass = RetentionClass.EPHEMERAL_ANSWER_ONLY
    egress_class: AssertionEgressClass = AssertionEgressClass.REMOTE_SAFE
    derived_from: list[str] = Field(default_factory=list)
    derivation_kind: DerivationKind | None = None
    supersedes: list[str] = Field(default_factory=list)
    invalidated_by: list[str] = Field(default_factory=list)

    @staticmethod
    def _normalize_value(value: Any) -> Any:
        if isinstance(value, datetime):
            return value.isoformat()
        if isinstance(value, StrEnum):
            return value.value
        if isinstance(value, dict):
            return {
                str(key): GroundedAssertion._normalize_value(row)
                for key, row in sorted(value.items(), key=lambda item: str(item[0]))
            }
        if isinstance(value, (list, tuple)):
            return [GroundedAssertion._normalize_value(row) for row in value]
        return value

    @property
    def proposition_identity(self) -> str:
        """Deterministic proposition identity without similarity heuristics."""
        payload = {
            "subject": self.subject,
            "predicate": self.predicate,
            "value": self._normalize_value(self.value),
            "scope": self.scope,
            "temporal_scope": self.temporal_scope,
            "valid_from": self.valid_from.isoformat() if self.valid_from else None,
            "valid_until": self.valid_until.isoformat() if self.valid_until else None,
        }
        encoded = json.dumps(payload, sort_keys=True, separators=(",", ":"))
        return hashlib.sha256(encoded.encode("utf-8")).hexdigest()

    @property
    def claim_frame(self) -> tuple[str, str, str | None, str | None]:
        """Frame used to compare claims that may disagree."""
        return (self.subject, self.predicate, self.scope, self.temporal_scope)

    def refers_to_same_proposition(self, other: GroundedAssertion) -> bool:
        return self.proposition_identity == other.proposition_identity

    def is_usable_now(
        self,
        *,
        now: datetime,
        active_source_refs: set[str] | None = None,
        invalidating_assertion_ids: set[str] | None = None,
        supporting_assertions: dict[str, GroundedAssertion] | None = None,
        superseded_ids: set[str] | None = None,
    ) -> bool:
        if superseded_ids and self.id in superseded_ids:
            return False
        if self.valid_from is not None and now < self.valid_from:
            return False
        if self.valid_until is not None and now > self.valid_until:
            return False
        if self.validity_kind == AssertionValidityKind.UNTIL_EVENT:
            invalidators = invalidating_assertion_ids or set()
            if invalidators & set(self.invalidated_by):
                return False
        if self.validity_kind == AssertionValidityKind.SOURCE_LIFETIME:
            if (
                active_source_refs is not None
                and not set(self.evidence_refs).issubset(active_source_refs)
            ):
                return False
        if self.validity_kind == AssertionValidityKind.DERIVED_LIFETIME and supporting_assertions:
            for assertion_id in self.derived_from:
                parent = supporting_assertions.get(assertion_id)
                if parent is None:
                    return False
                if not parent.is_usable_now(
                    now=now,
                    active_source_refs=active_source_refs,
                    invalidating_assertion_ids=invalidating_assertion_ids,
                    supporting_assertions=supporting_assertions,
                    superseded_ids=superseded_ids,
                ):
                    return False
        return True

    def usability(
        self,
        *,
        now: datetime,
        active_source_refs: set[str] | None = None,
        invalidating_assertion_ids: set[str] | None = None,
        supporting_assertions: dict[str, GroundedAssertion] | None = None,
        superseded_ids: set[str] | None = None,
    ) -> AssertionUsability:
        if superseded_ids and self.id in superseded_ids:
            return AssertionUsability.SUPERSEDED
        if self.is_usable_now(
            now=now,
            active_source_refs=active_source_refs,
            invalidating_assertion_ids=invalidating_assertion_ids,
            supporting_assertions=supporting_assertions,
            superseded_ids=superseded_ids,
        ):
            return AssertionUsability.CURRENT
        return AssertionUsability.STALE

    @model_validator(mode="after")
    def _validate_validity_shape(self) -> GroundedAssertion:
        if self.validity_kind == AssertionValidityKind.TTL and self.valid_until is None:
            msg = "TTL assertions must define valid_until."
            raise ValueError(msg)
        if self.validity_kind == AssertionValidityKind.UNTIL_EVENT and not self.invalidated_by:
            msg = "UNTIL_EVENT assertions must declare invalidated_by."
            raise ValueError(msg)
        if self.validity_kind == AssertionValidityKind.DERIVED_LIFETIME and not self.derived_from:
            msg = "DERIVED_LIFETIME assertions must declare derived_from."
            raise ValueError(msg)
        return self


class EvidenceUnknown(BaseModel):
    """A proposition Enigma knows it has not established yet."""

    subject: str
    predicate: str
    reason: UnknownReason
    missing_sources: list[str] = Field(default_factory=list)


class AssertionChallenge(BaseModel):
    """How current evidence relates to a material claim or conclusion."""

    claim_id: str | None = None
    related_assertion_ids: list[str] = Field(default_factory=list)
    subject: str
    predicate: str
    disposition: ChallengeDisposition
    summary: str
    evidence_refs: list[str] = Field(default_factory=list)
    unresolved: bool = False


def classify_assertion_challenge(
    claim: GroundedAssertion,
    related: GroundedAssertion,
    *,
    relevant_context: bool = False,
    unresolved: bool = False,
) -> ChallengeDisposition:
    """Canonical relation between a claim and another assertion."""
    if unresolved:
        return ChallengeDisposition.DOES_NOT_ADDRESS
    if claim.refers_to_same_proposition(related):
        return ChallengeDisposition.CONFIRMS
    if claim.claim_frame == related.claim_frame:
        return ChallengeDisposition.CONFLICTS
    if relevant_context:
        return ChallengeDisposition.QUALIFIES
    return ChallengeDisposition.DOES_NOT_ADDRESS


def conflicting_assertion_ids(assertions: list[GroundedAssertion]) -> list[tuple[str, str]]:
    """Return conflicting assertion pairs while preserving both sides."""
    conflicts: list[tuple[str, str]] = []
    for index, left in enumerate(assertions):
        for right in assertions[index + 1 :]:
            if left.claim_frame != right.claim_frame:
                continue
            if left.refers_to_same_proposition(right):
                continue
            conflicts.append((left.id, right.id))
    return conflicts


def current_assertions(
    assertions: list[GroundedAssertion],
    *,
    now: datetime,
    active_source_refs: set[str] | None = None,
    invalidating_assertion_ids: set[str] | None = None,
) -> list[GroundedAssertion]:
    """Projection of currently usable assertions, without erasing conflicts."""
    superseded_ids: set[str] = set()
    supporting_assertions = {assertion.id: assertion for assertion in assertions}
    for assertion in assertions:
        superseded_ids.update(assertion.supersedes)
    return [
        assertion
        for assertion in assertions
        if assertion.is_usable_now(
            now=now,
            active_source_refs=active_source_refs,
            invalidating_assertion_ids=invalidating_assertion_ids,
            supporting_assertions=supporting_assertions,
            superseded_ids=superseded_ids,
        )
    ]


_PROMOTION_AUTHORITIES: dict[EpistemicStatus, set[DerivationKind]] = {
    EpistemicStatus.USER_REPORTED: {DerivationKind.DIRECT_OBSERVATION},
    EpistemicStatus.USER_CONFIRMED: {DerivationKind.USER_CONFIRMATION},
    EpistemicStatus.SOURCE_OBSERVED: {DerivationKind.DIRECT_OBSERVATION},
    EpistemicStatus.EXTERNALLY_VERIFIED: {DerivationKind.SOURCE_CONFIRMATION},
    EpistemicStatus.SYSTEM_VERIFIED: {DerivationKind.DETERMINISTIC_RULE},
    EpistemicStatus.DETERMINISTICALLY_DERIVED: {DerivationKind.DETERMINISTIC_RULE},
    EpistemicStatus.USER_UNCERTAIN: {
        DerivationKind.DIRECT_OBSERVATION,
        DerivationKind.USER_CONFIRMATION,
    },
    EpistemicStatus.MODEL_INFERRED: {
        DerivationKind.INFERENCE,
        DerivationKind.SEMANTIC_SIMILARITY,
        DerivationKind.DIALOGUE_HISTORY,
        DerivationKind.HIGH_CONFIDENCE,
    },
    EpistemicStatus.CONFLICTED: {DerivationKind.DETERMINISTIC_RULE},
    EpistemicStatus.STALE: {DerivationKind.DETERMINISTIC_RULE},
    EpistemicStatus.UNKNOWN: {DerivationKind.DETERMINISTIC_RULE},
}


def is_epistemic_transition_permitted(
    *,
    target_status: EpistemicStatus,
    derivation_kind: DerivationKind,
    supporting_statuses: list[EpistemicStatus],
) -> bool:
    """Guard against silent promotion from weak or internal evidence."""
    if derivation_kind not in _PROMOTION_AUTHORITIES.get(target_status, set()):
        return False
    if target_status in {
        EpistemicStatus.USER_CONFIRMED,
        EpistemicStatus.SOURCE_OBSERVED,
        EpistemicStatus.EXTERNALLY_VERIFIED,
        EpistemicStatus.SYSTEM_VERIFIED,
    }:
        return all(status == target_status for status in supporting_statuses)
    if target_status == EpistemicStatus.DETERMINISTICALLY_DERIVED:
        return all(
            status
            in {
                EpistemicStatus.USER_CONFIRMED,
                EpistemicStatus.SOURCE_OBSERVED,
                EpistemicStatus.EXTERNALLY_VERIFIED,
                EpistemicStatus.SYSTEM_VERIFIED,
                EpistemicStatus.DETERMINISTICALLY_DERIVED,
            }
            for status in supporting_statuses
        )
    if target_status == EpistemicStatus.MODEL_INFERRED:
        return True
    return bool(supporting_statuses)


__all__ = [
    "AssertionChallenge",
    "AssertionEgressClass",
    "AssertionKind",
    "AssertionSensitivity",
    "AssertionUsability",
    "AssertionValidityKind",
    "ChallengeDisposition",
    "DerivationKind",
    "EpistemicStatus",
    "EvidenceUnknown",
    "GroundedAssertion",
    "UnknownReason",
    "classify_assertion_challenge",
    "conflicting_assertion_ids",
    "current_assertions",
    "is_epistemic_transition_permitted",
]
