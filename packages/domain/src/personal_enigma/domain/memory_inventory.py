"""Memory inventory — projection over governed retained assertions (C29 slice 4).

Brain / Life Graph reads this view. It is not a second truth store.

```text
retained assertions (vault / DurableAssertionStore)
      ↓
MemoryInventory projection
      ↓
KNOWN | POSSIBLE | STALE | CONFLICTED | EXPIRING
```

Forgotten and expired rows are absent from current inventory. Correction is
supersession of a new retained assertion, not an in-place rewrite.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import UTC, datetime
from enum import StrEnum

from pydantic import BaseModel, Field

from personal_enigma.domain.grounding import EpistemicStatus, GroundedAssertion
from personal_enigma.domain.retention import DerivedRecord, RetentionPurpose

RETAINED_ASSERTION_RECORD_KIND = "retained_assertion"
FORGET_RETAINED_ASSERTION_ACTION = "forget_retained_assertion"

_KNOWN_EPISTEMIC = frozenset(
    {
        EpistemicStatus.USER_CONFIRMED,
        EpistemicStatus.USER_REPORTED,
        EpistemicStatus.SOURCE_OBSERVED,
        EpistemicStatus.EXTERNALLY_VERIFIED,
        EpistemicStatus.SYSTEM_VERIFIED,
        EpistemicStatus.DETERMINISTICALLY_DERIVED,
    }
)

_POSSIBLE_EPISTEMIC = frozenset(
    {
        EpistemicStatus.MODEL_INFERRED,
        EpistemicStatus.USER_UNCERTAIN,
        EpistemicStatus.UNKNOWN,
    }
)

_PROFILING_CLAIM_FRAGMENTS = (
    "emotionally",
    "dependent",
    "personality",
    "psycholog",
    "persuad",
    "self_esteem",
    "relationship_strength",
    "behavioural",
    "anxious achiever",
    "dossier",
)


class MemoryInventoryStatus(StrEnum):
    """Display status for a current inventory entry — never collapses inference to known."""

    KNOWN = "known"
    POSSIBLE = "possible"
    STALE = "stale"
    CONFLICTED = "conflicted"
    EXPIRING = "expiring"


class MemoryReviewStatus(StrEnum):
    """Expiry / review overlay, independent of how the fact was established."""

    CURRENT = "current"
    REVIEW_DUE = "review_due"


class MemoryForgetCapability(BaseModel):
    """Hook to existing forget semantics — inventory does not delete."""

    available: bool = True
    action: str = FORGET_RETAINED_ASSERTION_ACTION
    assertion_id: str


class MemoryWhy(BaseModel):
    """Inspectable answer to 'why do you remember this?' — ids and purpose, not source bodies."""

    purpose: RetentionPurpose | None = None
    provenance_refs: list[str] = Field(default_factory=list)
    derived_from: list[str] = Field(default_factory=list)
    retained_at: datetime
    rationale: str = ""
    retention_outcome: str | None = None
    retention_class: str | None = None


class MemoryInventoryEntry(BaseModel):
    """One current retained life-memory claim, safe to inspect."""

    assertion_id: str
    subject: str
    predicate: str
    value: object = None
    claim: str
    epistemic_status: EpistemicStatus
    inventory_status: MemoryInventoryStatus
    retention_purpose: RetentionPurpose | None = None
    provenance_refs: list[str] = Field(default_factory=list)
    retained_at: datetime
    expires_at: datetime | None = None
    review_status: MemoryReviewStatus = MemoryReviewStatus.CURRENT
    derived_from: list[str] = Field(default_factory=list)
    supersedes: list[str] = Field(default_factory=list)
    why: MemoryWhy
    forget: MemoryForgetCapability
    can_correct: bool = True


class MemoryInventory(BaseModel):
    """Current-memory projection — forgotten, expired, and superseded rows are absent."""

    entries: list[MemoryInventoryEntry] = Field(default_factory=list)
    generated_at: datetime

    def about(self, subject: str) -> list[MemoryInventoryEntry]:
        needle = _normalize_subject(subject)
        return [entry for entry in self.entries if _normalize_subject(entry.subject) == needle]

    def get(self, assertion_id: str) -> MemoryInventoryEntry | None:
        for entry in self.entries:
            if entry.assertion_id == assertion_id:
                return entry
        return None

    def why(self, assertion_id: str) -> MemoryWhy | None:
        entry = self.get(assertion_id)
        return entry.why if entry is not None else None


def format_memory_claim(subject: str, predicate: str, value: object) -> str:
    """Short practical claim — not a psychological dossier sentence."""
    label = subject.removeprefix("PERSON_").replace("_", " ")
    rendered = "" if value is None else str(value)
    predicate_label = predicate.replace("_", " ")
    if predicate == "likes":
        return f"{label} likes {rendered}".strip()
    if predicate == "birthday":
        return f"{label} birthday is {rendered}".strip()
    if predicate == "gift_history":
        return f"{label} gift history: {rendered}".strip()
    return f"{label} {predicate_label} {rendered}".strip()


def inventory_status_for(
    epistemic_status: EpistemicStatus,
    *,
    ttl: bool = False,
    conflicted: bool = False,
    stale: bool = False,
) -> MemoryInventoryStatus:
    """Map epistemic class to display status. MODEL_INFERRED never becomes KNOWN."""
    if conflicted or epistemic_status == EpistemicStatus.CONFLICTED:
        return MemoryInventoryStatus.CONFLICTED
    if stale or epistemic_status == EpistemicStatus.STALE:
        return MemoryInventoryStatus.STALE
    if epistemic_status in _POSSIBLE_EPISTEMIC:
        return MemoryInventoryStatus.POSSIBLE
    if ttl:
        return MemoryInventoryStatus.EXPIRING
    if epistemic_status in _KNOWN_EPISTEMIC:
        return MemoryInventoryStatus.KNOWN
    return MemoryInventoryStatus.POSSIBLE


def project_memory_inventory(
    records: list[DerivedRecord],
    *,
    subject: str | None = None,
    now: datetime | None = None,
) -> MemoryInventory:
    """Compile current inventory from retained-assertion vault rows.

    Does not read raw source blobs. Forgotten rows are absent because forget is
    SQL DELETE. Elapsed-TTL rows are also hidden here before ``expire_ttl()``
    runs, so inventory absence is not proof that GC ran. Superseded rows stay
    in the vault for lineage but are omitted from current inventory.
    """
    current = now or datetime.now(tz=UTC)
    retained = [_parse_retained_view(record) for record in records]
    retained = [view for view in retained if view is not None]
    superseded_ids = {sid for view in retained for sid in view.supersedes}
    current_views = [
        view
        for view in retained
        if view.assertion_id not in superseded_ids and not _is_expired(view, current)
    ]
    if subject is not None:
        needle = _normalize_subject(subject)
        current_views = [
            view for view in current_views if _normalize_subject(view.subject) == needle
        ]

    conflicted_ids = _conflicted_assertion_ids(current_views)
    entries = [
        _entry_from_view(view, conflicted=view.assertion_id in conflicted_ids)
        for view in current_views
    ]
    entries.sort(key=lambda entry: (entry.subject, entry.predicate, entry.assertion_id))
    return MemoryInventory(entries=entries, generated_at=current)


def inventory_contains_profiling_claim(inventory: MemoryInventory) -> bool:
    """True when a current entry looks like an inferred psychological dossier."""
    for entry in inventory.entries:
        haystack = " ".join(
            [
                entry.predicate,
                str(entry.value or ""),
                entry.claim,
            ]
        ).lower()
        if any(fragment in haystack for fragment in _PROFILING_CLAIM_FRAGMENTS):
            return True
    return False


@dataclass(frozen=True)
class _RetainedView:
    assertion_id: str
    subject: str
    predicate: str
    value: object
    epistemic_status: EpistemicStatus
    purpose: RetentionPurpose | None
    provenance_refs: list[str]
    derived_from: list[str]
    supersedes: list[str]
    retained_at: datetime
    expires_at: datetime | None
    ttl: bool
    rationale: str
    retention_outcome: str | None
    retention_class: str | None


def _parse_retained_view(record: DerivedRecord) -> _RetainedView | None:
    payload = record.payload
    kind = payload.get("record_kind")
    if kind is not None and kind != RETAINED_ASSERTION_RECORD_KIND:
        return None
    assertion_id = payload.get("assertion_id")
    subject = payload.get("subject")
    predicate = payload.get("predicate")
    if not isinstance(assertion_id, str) or not isinstance(subject, str):
        return None
    if not isinstance(predicate, str):
        return None

    epistemic_raw = payload.get("epistemic_status")
    try:
        epistemic_status = (
            EpistemicStatus(epistemic_raw)
            if isinstance(epistemic_raw, str)
            else EpistemicStatus.UNKNOWN
        )
    except ValueError:
        epistemic_status = EpistemicStatus.UNKNOWN

    decision = payload.get("retention_decision")
    decision_dict = decision if isinstance(decision, dict) else {}
    purpose = _purpose_from(decision_dict, record)
    rationale = decision_dict.get("rationale")
    rationale_text = rationale if isinstance(rationale, str) else ""
    outcome = decision_dict.get("outcome")
    outcome_text = outcome if isinstance(outcome, str) else None
    retention_class = decision_dict.get("retention_class")
    if isinstance(retention_class, str):
        retention_class_text = retention_class
    else:
        retention_class_text = record.lineage.retention_class.value

    provenance = _id_list(payload.get("evidence_refs"))
    for ref in _id_list(decision_dict.get("provenance_refs")):
        if ref not in provenance:
            provenance.append(ref)

    derived_from = _id_list(payload.get("derived_from_assertion_ids"))
    for ref in record.lineage.derived_from:
        stripped = ref.removeprefix("assertion:")
        if stripped != ref and stripped not in derived_from and stripped != assertion_id:
            derived_from.append(stripped)

    expires_at = _parse_iso(payload.get("valid_until"))
    ttl = outcome_text == "ttl" or expires_at is not None

    return _RetainedView(
        assertion_id=assertion_id,
        subject=subject,
        predicate=predicate,
        value=payload.get("value"),
        epistemic_status=epistemic_status,
        purpose=purpose,
        provenance_refs=provenance,
        derived_from=derived_from,
        supersedes=_id_list(payload.get("supersedes")),
        retained_at=record.created_at,
        expires_at=expires_at,
        ttl=ttl,
        rationale=rationale_text,
        retention_outcome=outcome_text,
        retention_class=retention_class_text,
    )


def _entry_from_view(view: _RetainedView, *, conflicted: bool) -> MemoryInventoryEntry:
    status = inventory_status_for(
        view.epistemic_status,
        ttl=view.ttl,
        conflicted=conflicted,
    )
    review = MemoryReviewStatus.REVIEW_DUE if view.ttl else MemoryReviewStatus.CURRENT
    why = MemoryWhy(
        purpose=view.purpose,
        provenance_refs=list(view.provenance_refs),
        derived_from=list(view.derived_from),
        retained_at=view.retained_at,
        rationale=view.rationale,
        retention_outcome=view.retention_outcome,
        retention_class=view.retention_class,
    )
    return MemoryInventoryEntry(
        assertion_id=view.assertion_id,
        subject=view.subject,
        predicate=view.predicate,
        value=view.value,
        claim=format_memory_claim(view.subject, view.predicate, view.value),
        epistemic_status=view.epistemic_status,
        inventory_status=status,
        retention_purpose=view.purpose,
        provenance_refs=list(view.provenance_refs),
        retained_at=view.retained_at,
        expires_at=view.expires_at,
        review_status=review,
        derived_from=list(view.derived_from),
        supersedes=list(view.supersedes),
        why=why,
        forget=MemoryForgetCapability(
            available=True,
            action=FORGET_RETAINED_ASSERTION_ACTION,
            assertion_id=view.assertion_id,
        ),
        can_correct=True,
    )


def _conflicted_assertion_ids(views: list[_RetainedView]) -> set[str]:
    conflicted: set[str] = set()
    for index, left in enumerate(views):
        for right in views[index + 1 :]:
            if left.subject != right.subject or left.predicate != right.predicate:
                continue
            if GroundedAssertion._normalize_value(left.value) == GroundedAssertion._normalize_value(
                right.value
            ):
                continue
            conflicted.add(left.assertion_id)
            conflicted.add(right.assertion_id)
    return conflicted


def _is_expired(view: _RetainedView, now: datetime) -> bool:
    if view.expires_at is None:
        return False
    expires_at = view.expires_at
    if expires_at.tzinfo is None:
        expires_at = expires_at.replace(tzinfo=UTC)
    return expires_at <= now


def _purpose_from(
    decision: dict[str, object],
    record: DerivedRecord,
) -> RetentionPurpose | None:
    raw = decision.get("purpose")
    if isinstance(raw, str):
        try:
            return RetentionPurpose(raw)
        except ValueError:
            pass
    return record.lineage.purpose


def _id_list(raw: object) -> list[str]:
    if not isinstance(raw, list):
        return []
    ids: list[str] = []
    for item in raw:
        if isinstance(item, str) and item:
            ids.append(item)
    return ids


def _parse_iso(raw: object) -> datetime | None:
    if not isinstance(raw, str) or not raw:
        return None
    parsed = datetime.fromisoformat(raw)
    if parsed.tzinfo is None:
        return parsed.replace(tzinfo=UTC)
    return parsed


def _normalize_subject(subject: str) -> str:
    return subject.strip().lower().removeprefix("person_")
