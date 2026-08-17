"""Developer-only Demo Mode ground truth (D6).

Authoritative to the **evaluator** only. Must never be imported into Enigma
reasoning, attention, obligations, transformation, or Private Mode paths.
"""

from __future__ import annotations

from collections.abc import Collection, Iterable, Mapping
from datetime import UTC, datetime
from enum import StrEnum
from pathlib import Path
from typing import Any, Literal, Self

import yaml
from pydantic import BaseModel, Field, ValidationError, field_validator, model_validator

CRITICAL_IMPORTANCE = frozenset({"critical", "high"})


class ScenarioSignalClass(StrEnum):
    """Evaluator-only classification of scenario evidence (D06 amendment / D08).

    Never attached to ``SyntheticMailSource`` / Enigma ingest payloads.
    """

    CANONICAL = "canonical"
    BACKGROUND = "background"
    NOISE = "noise"
    ADVERSARIAL = "adversarial"


_KIND_TO_SECTION = {
    "obligation": "obligations",
    "commitment": "commitments",
    "attention_window": "attention_windows",
    "attention_expectation": "attention_windows",
    "memory_checkpoint": "memory_checkpoints",
    "checkpoint": "memory_checkpoints",
}


class GroundTruthValidationError(ValueError):
    """Malformed ground-truth document(s) with actionable messages."""

    def __init__(self, errors: list[str]) -> None:
        self.errors = errors
        super().__init__(";\n".join(errors))


class ObligationStatus(StrEnum):
    OPEN = "open"
    RESOLVED = "resolved"
    CANCELLED = "cancelled"


class CommitmentTruthKind(StrEnum):
    INFERRED = "inferred"
    EXPLICIT_REMINDER = "explicit_reminder"


class CommitmentTruthStatus(StrEnum):
    OPEN = "open"
    STALE = "stale"
    COMPLETED = "completed"
    CANCELLED = "cancelled"


def _parse_instant(value: object) -> object:
    if not isinstance(value, str):
        return value
    text = value.strip()
    if text.endswith("Z"):
        text = text[:-1] + "+00:00"
    if len(text) == 10 and text[4] == "-" and text[7] == "-":
        text = f"{text}T00:00:00+00:00"
    try:
        parsed = datetime.fromisoformat(text)
    except ValueError as exc:
        raise ValueError(f"invalid instant {value!r}") from exc
    if parsed.tzinfo is None:
        parsed = parsed.replace(tzinfo=UTC)
    return parsed


class StatusPoint(BaseModel):
    """Point-in-time status on an obligation or commitment timeline."""

    at: datetime
    status: str

    @field_validator("at", mode="before")
    @classmethod
    def _parse_at(cls, value: object) -> object:
        return _parse_instant(value)


class ObligationTruth(BaseModel):
    """Authoritative obligation record for evaluation — not an Enigma domain object."""

    id: str
    description: str
    actor: str | None = None
    beneficiary: str | None = None
    created_at: datetime
    due_at: datetime | None = None
    importance: Literal["critical", "high", "medium", "low"] = "medium"
    status_timeline: list[StatusPoint] = Field(default_factory=list)
    evidence_ids: list[str] = Field(default_factory=list)

    @field_validator("created_at", "due_at", mode="before")
    @classmethod
    def _parse_times(cls, value: object) -> object:
        return _parse_instant(value)

    @model_validator(mode="after")
    def _default_timeline(self) -> Self:
        if not self.status_timeline:
            self.status_timeline = [
                StatusPoint(at=self.created_at, status=ObligationStatus.OPEN.value)
            ]
        allowed = {s.value for s in ObligationStatus}
        for point in self.status_timeline:
            if point.status not in allowed:
                raise ValueError(
                    f"obligation {self.id!r}: invalid status {point.status!r}; "
                    f"expected one of {sorted(allowed)}"
                )
        return self

    def status_at(self, when: datetime) -> str:
        """Latest status whose ``at`` is <= ``when`` (open if none yet)."""
        applicable = [p for p in self.status_timeline if p.at <= when]
        if not applicable:
            return ObligationStatus.OPEN.value
        return max(applicable, key=lambda p: p.at).status

    def is_open_at(self, when: datetime) -> bool:
        return self.status_at(when) == ObligationStatus.OPEN.value


class CommitmentTruth(BaseModel):
    """Authoritative commitment record for evaluation."""

    id: str
    description: str
    kind: CommitmentTruthKind = CommitmentTruthKind.INFERRED
    created_at: datetime
    due_at: datetime | None = None
    obligation_id: str | None = None
    status_timeline: list[StatusPoint] = Field(default_factory=list)
    evidence_ids: list[str] = Field(default_factory=list)

    @field_validator("created_at", "due_at", mode="before")
    @classmethod
    def _parse_times(cls, value: object) -> object:
        return _parse_instant(value)

    @model_validator(mode="after")
    def _default_timeline(self) -> Self:
        if not self.status_timeline:
            self.status_timeline = [
                StatusPoint(
                    at=self.created_at,
                    status=CommitmentTruthStatus.OPEN.value,
                )
            ]
        allowed = {s.value for s in CommitmentTruthStatus}
        for point in self.status_timeline:
            if point.status not in allowed:
                raise ValueError(
                    f"commitment {self.id!r}: invalid status {point.status!r}; "
                    f"expected one of {sorted(allowed)}"
                )
        return self

    def status_at(self, when: datetime) -> str:
        applicable = [p for p in self.status_timeline if p.at <= when]
        if not applicable:
            return CommitmentTruthStatus.OPEN.value
        return max(applicable, key=lambda p: p.at).status


class AttentionWindow(BaseModel):
    """Acceptable window for surfacing an obligation (not a single timestamp)."""

    id: str | None = None
    obligation_id: str
    earliest: datetime
    ideal: datetime | None = None
    latest: datetime
    minimum_priority: int | None = None

    @field_validator("earliest", "ideal", "latest", mode="before")
    @classmethod
    def _parse_times(cls, value: object) -> object:
        return _parse_instant(value)

    @model_validator(mode="before")
    @classmethod
    def _normalize_obligation_key(cls, data: Any) -> Any:
        if not isinstance(data, Mapping):
            return data
        payload = dict(data)
        if "obligation_id" not in payload and "obligation" in payload:
            payload["obligation_id"] = payload.pop("obligation")
        return payload

    @model_validator(mode="after")
    def _check_order(self) -> Self:
        if self.earliest > self.latest:
            raise ValueError(
                f"attention window for {self.obligation_id!r}: "
                f"earliest {self.earliest.isoformat()} is after "
                f"latest {self.latest.isoformat()}"
            )
        if self.ideal is not None and not (self.earliest <= self.ideal <= self.latest):
            raise ValueError(
                f"attention window for {self.obligation_id!r}: "
                f"ideal must fall between earliest and latest"
            )
        if self.id is None:
            self.id = f"attn-{self.obligation_id}"
        return self

    def is_active_at(self, when: datetime) -> bool:
        """Window has opened (``earliest`` reached); used for missed detection."""
        return when >= self.earliest


class MemoryCheckpoint(BaseModel):
    """What Enigma should know by a simulation instant."""

    id: str | None = None
    at: datetime
    expected_memories: list[str] = Field(min_length=1)
    min_confidence: float | None = Field(default=None, ge=0.0, le=1.0)

    @field_validator("at", mode="before")
    @classmethod
    def _parse_at(cls, value: object) -> object:
        return _parse_instant(value)

    @model_validator(mode="after")
    def _default_id(self) -> Self:
        if self.id is None:
            self.id = f"checkpoint-{self.at.date().isoformat()}"
        return self


class SignalTruth(BaseModel):
    """Per-evidence evaluator metadata (never fed to Enigma ingest)."""

    evidence_id: str
    signal_class: ScenarioSignalClass = ScenarioSignalClass.BACKGROUND
    expected_attention: bool = False

    @model_validator(mode="before")
    @classmethod
    def _normalize_keys(cls, data: Any) -> Any:
        if not isinstance(data, Mapping):
            return data
        payload = dict(data)
        if "evidence_id" not in payload:
            for alt in ("id", "event_id", "message_id"):
                if alt in payload:
                    payload["evidence_id"] = payload.pop(alt)
                    break
        return payload


class GroundTruthCorpus(BaseModel):
    """Merged ground truth for one scenario package."""

    obligations: list[ObligationTruth] = Field(default_factory=list)
    commitments: list[CommitmentTruth] = Field(default_factory=list)
    attention_windows: list[AttentionWindow] = Field(default_factory=list)
    memory_checkpoints: list[MemoryCheckpoint] = Field(default_factory=list)
    signals: list[SignalTruth] = Field(default_factory=list)
    source_paths: list[str] = Field(default_factory=list)

    def obligation_by_id(self, obligation_id: str) -> ObligationTruth | None:
        for item in self.obligations:
            if item.id == obligation_id:
                return item
        return None

    def window_for(self, obligation_id: str) -> AttentionWindow | None:
        for window in self.attention_windows:
            if window.obligation_id == obligation_id:
                return window
        return None

    def signals_for_class(self, signal_class: ScenarioSignalClass) -> list[SignalTruth]:
        return [s for s in self.signals if s.signal_class == signal_class]


class MissedObligation(BaseModel):
    """An open critical obligation that attention failed to surface in time."""

    obligation_id: str
    description: str
    importance: str
    window_id: str | None = None
    earliest: datetime | None = None
    latest: datetime | None = None
    evaluated_at: datetime
    reason: str


def _as_mapping_list(value: Any) -> list[dict[str, Any]]:
    if value is None:
        return []
    if isinstance(value, Mapping):
        return [dict(value)]
    if isinstance(value, list):
        out: list[dict[str, Any]] = []
        for item in value:
            if not isinstance(item, Mapping):
                raise GroundTruthValidationError(
                    [f"expected mapping entries, got {type(item).__name__}"]
                )
            out.append(dict(item))
        return out
    raise GroundTruthValidationError(
        [f"expected list or mapping, got {type(value).__name__}"]
    )


def _append_validated(
    corpus: GroundTruthCorpus,
    *,
    path: str,
    obligations: Any = None,
    commitments: Any = None,
    attention_windows: Any = None,
    memory_checkpoints: Any = None,
    signals: Any = None,
) -> None:
    errors: list[str] = []
    try:
        for item in _as_mapping_list(obligations):
            corpus.obligations.append(ObligationTruth.model_validate(item))
        for item in _as_mapping_list(commitments):
            corpus.commitments.append(CommitmentTruth.model_validate(item))
        for item in _as_mapping_list(attention_windows):
            corpus.attention_windows.append(AttentionWindow.model_validate(item))
        for item in _as_mapping_list(memory_checkpoints):
            corpus.memory_checkpoints.append(MemoryCheckpoint.model_validate(item))
        for item in _as_mapping_list(signals):
            corpus.signals.append(SignalTruth.model_validate(item))
    except GroundTruthValidationError as exc:
        errors.extend(f"{path}: {msg}" for msg in exc.errors)
    except ValidationError as exc:
        errors.extend(f"{path}: {err['loc']}: {err['msg']}" for err in exc.errors())
    except ValueError as exc:
        errors.append(f"{path}: {exc}")
    if errors:
        raise GroundTruthValidationError(errors)


def _normalize_wrappers(data: dict[str, Any]) -> dict[str, Any]:
    """Lift Phase 2 singular wrappers into list sections."""
    out = dict(data)
    if "attention_expectation" in out and "attention_windows" not in out:
        out["attention_windows"] = out.pop("attention_expectation")
    if "checkpoint" in out and "memory_checkpoints" not in out:
        out["memory_checkpoints"] = out.pop("checkpoint")
    if "obligation" in out and "obligations" not in out:
        out["obligations"] = out.pop("obligation")
    if "commitment" in out and "commitments" not in out:
        out["commitments"] = out.pop("commitment")
    return out


def _parse_and_merge(corpus: GroundTruthCorpus, data: dict[str, Any], *, path: str) -> None:
    """Parse one YAML document into ``corpus``."""
    data = _normalize_wrappers(data)

    kind = data.get("kind")
    if isinstance(kind, str):
        kind_l = kind.strip().lower()
        section = _KIND_TO_SECTION.get(kind_l)
        if section is not None:
            # Document-type discriminator (kind: obligation|commitment|...).
            # Commitment field values like kind: inferred fall through below.
            body = {k: v for k, v in data.items() if k != "kind"}
            _append_validated(corpus, path=path, **{section: body})
            corpus.source_paths.append(path)
            return

    section_keys = {
        "obligations",
        "commitments",
        "attention_windows",
        "memory_checkpoints",
        "signals",
    }
    if section_keys.intersection(data):
        _append_validated(
            corpus,
            path=path,
            obligations=data.get("obligations"),
            commitments=data.get("commitments"),
            attention_windows=data.get("attention_windows"),
            memory_checkpoints=data.get("memory_checkpoints"),
            signals=data.get("signals"),
        )
        corpus.source_paths.append(path)
        return

    if {"signal_class", "expected_attention"}.issubset(data) or (
        "signal_class" in data and ("evidence_id" in data or "id" in data)
    ):
        _append_validated(corpus, path=path, signals=data)
        corpus.source_paths.append(path)
        return

    if {"earliest", "latest"}.issubset(data) and (
        "obligation" in data or "obligation_id" in data
    ):
        _append_validated(corpus, path=path, attention_windows=data)
        corpus.source_paths.append(path)
        return

    if "expected_memories" in data and "at" in data:
        _append_validated(corpus, path=path, memory_checkpoints=data)
        corpus.source_paths.append(path)
        return

    if "id" in data and "description" in data and "created_at" in data:
        is_commitment = data.get("obligation_id") is not None or str(
            data.get("kind", "")
        ).lower() in {"inferred", "explicit_reminder"}
        if is_commitment and "importance" not in data and "actor" not in data:
            _append_validated(corpus, path=path, commitments=data)
        else:
            _append_validated(corpus, path=path, obligations=data)
        corpus.source_paths.append(path)
        return

    raise GroundTruthValidationError(
        [
            f"{path}: unrecognised ground-truth document; "
            "expected obligations/commitments/attention_windows/"
            "memory_checkpoints/signals or a kind discriminator"
        ]
    )


def _ingest_raw(corpus: GroundTruthCorpus, raw: Any, *, path: str) -> None:
    if raw is None:
        return
    if isinstance(raw, list):
        for index, item in enumerate(raw):
            if not isinstance(item, Mapping):
                raise GroundTruthValidationError(
                    [f"{path}[{index}]: expected mapping, got {type(item).__name__}"]
                )
            _parse_and_merge(corpus, dict(item), path=f"{path}[{index}]")
        return
    if isinstance(raw, Mapping):
        _parse_and_merge(corpus, dict(raw), path=path)
        return
    raise GroundTruthValidationError(
        [f"{path}: expected YAML mapping or list, got {type(raw).__name__}"]
    )


_GROUND_TRUTH_SKIP_FILES = frozenset({"support_contracts.yaml"})


def load_ground_truth(path: str | Path) -> GroundTruthCorpus:
    """Load and validate all ``*.yaml`` files under a ``ground_truth/`` directory.

    Also accepts a single YAML file path. Empty directories yield an empty corpus.
    Evaluator-only ``support_contracts.yaml`` is loaded via :func:`load_evaluation_truth`.
    """
    root = Path(path)
    corpus = GroundTruthCorpus()

    if root.is_file():
        files = [root]
    elif root.is_dir():
        files = sorted(
            p
            for p in root.glob("*.yaml")
            if p.is_file() and p.name not in _GROUND_TRUTH_SKIP_FILES
        )
    else:
        raise GroundTruthValidationError([f"ground truth path not found: {root}"])

    if not files:
        return corpus

    all_errors: list[str] = []
    for file_path in files:
        try:
            text = file_path.read_text(encoding="utf-8")
            documents = list(yaml.safe_load_all(text))
            if not documents or all(doc is None for doc in documents):
                all_errors.append(f"{file_path}: empty document")
                continue
            for index, doc in enumerate(documents):
                label = (
                    str(file_path) if len(documents) == 1 else f"{file_path}#{index}"
                )
                try:
                    _ingest_raw(corpus, doc, path=label)
                except GroundTruthValidationError as exc:
                    all_errors.extend(exc.errors)
        except yaml.YAMLError as exc:
            all_errors.append(f"{file_path}: YAML error: {exc}")

    if all_errors:
        raise GroundTruthValidationError(all_errors)

    _validate_cross_refs(corpus)
    return corpus


def _validate_cross_refs(corpus: GroundTruthCorpus) -> None:
    obligation_ids = {o.id for o in corpus.obligations}
    errors: list[str] = []
    for window in corpus.attention_windows:
        if window.obligation_id not in obligation_ids:
            errors.append(
                f"attention window {window.id!r} references unknown obligation "
                f"{window.obligation_id!r}"
            )
    for commitment in corpus.commitments:
        if commitment.obligation_id and commitment.obligation_id not in obligation_ids:
            errors.append(
                f"commitment {commitment.id!r} references unknown obligation "
                f"{commitment.obligation_id!r}"
            )
    dup_obl = _duplicates(o.id for o in corpus.obligations)
    if dup_obl:
        errors.append(f"duplicate obligation ids: {sorted(dup_obl)}")
    dup_cmt = _duplicates(c.id for c in corpus.commitments)
    if dup_cmt:
        errors.append(f"duplicate commitment ids: {sorted(dup_cmt)}")
    if errors:
        raise GroundTruthValidationError(errors)


def _duplicates(ids: Iterable[str]) -> set[str]:
    seen: set[str] = set()
    dups: set[str] = set()
    for item in ids:
        if item in seen:
            dups.add(item)
        else:
            seen.add(item)
    return dups


def detect_missed_obligations(
    truth: GroundTruthCorpus,
    *,
    surfaced_obligation_ids: Collection[str],
    at: datetime,
    importance: Collection[str] = CRITICAL_IMPORTANCE,
) -> list[MissedObligation]:
    """Flag open critical obligations whose window opened but were not surfaced.

    ``surfaced_obligation_ids`` are ids Enigma attention claimed to cover
    (evaluation input only — never written back into the reasoning path).
    """
    if at.tzinfo is None:
        at = at.replace(tzinfo=UTC)

    surfaced = set(surfaced_obligation_ids)
    importance_set = {str(i).lower() for i in importance}
    missed: list[MissedObligation] = []

    for obligation in truth.obligations:
        if obligation.importance not in importance_set:
            continue
        if not obligation.is_open_at(at):
            continue
        if obligation.id in surfaced:
            continue

        window = truth.window_for(obligation.id)
        if window is not None:
            if not window.is_active_at(at):
                continue
            if at > window.latest:
                reason = (
                    f"critical obligation not surfaced by window latest "
                    f"({window.latest.isoformat()})"
                )
            else:
                reason = (
                    f"critical obligation not surfaced after window earliest "
                    f"({window.earliest.isoformat()})"
                )
            missed.append(
                MissedObligation(
                    obligation_id=obligation.id,
                    description=obligation.description,
                    importance=obligation.importance,
                    window_id=window.id,
                    earliest=window.earliest,
                    latest=window.latest,
                    evaluated_at=at,
                    reason=reason,
                )
            )
            continue

        threshold = obligation.due_at or obligation.created_at
        if at >= threshold:
            missed.append(
                MissedObligation(
                    obligation_id=obligation.id,
                    description=obligation.description,
                    importance=obligation.importance,
                    window_id=None,
                    earliest=None,
                    latest=threshold,
                    evaluated_at=at,
                    reason=(
                        "critical obligation not surfaced by due/created threshold"
                    ),
                )
            )

    return missed


__all__ = [
    "AttentionWindow",
    "CommitmentTruth",
    "CommitmentTruthKind",
    "CommitmentTruthStatus",
    "CRITICAL_IMPORTANCE",
    "GroundTruthCorpus",
    "GroundTruthValidationError",
    "MemoryCheckpoint",
    "MissedObligation",
    "ObligationStatus",
    "ObligationTruth",
    "ScenarioSignalClass",
    "SignalTruth",
    "StatusPoint",
    "detect_missed_obligations",
    "load_ground_truth",
]
