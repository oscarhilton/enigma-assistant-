"""Scenario package loader and validator (D3).

Scenarios describe **source-layer** evidence only (mail, calendar, reminders,
notes, contacts). They must not embed pre-baked ``Obligation`` / attention
objects — Enigma discovers those downstream.
"""

from __future__ import annotations

from collections import Counter
from dataclasses import dataclass, field
from datetime import UTC, datetime, timedelta
from pathlib import Path
from random import Random
from typing import Any, Literal, TypeGuard

import yaml
from pydantic import BaseModel, Field, ValidationError, field_validator, model_validator

from personal_enigma.simulation.scenario_rng import rng_for_package, scenario_rng

SOURCE_EVENT_TYPES = frozenset(
    {
        "email.receive",
        "email.send",
        "calendar.upsert",
        "calendar.cancel",
        "reminder.upsert",
        "reminder.complete",
        "note.upsert",
        "contact.upsert",
    }
)

SOURCE_KINDS = frozenset({"mail", "calendar", "reminders", "notes", "contacts"})

FORBIDDEN_PAYLOAD_KEYS = frozenset(
    {
        "obligation",
        "obligations",
        "attention_item",
        "attention_items",
        "commitment",
        "commitments",
    }
)


class ScenarioValidationError(ValueError):
    """Malformed scenario package with actionable messages."""

    def __init__(self, errors: list[str]) -> None:
        self.errors = errors
        super().__init__(";\n".join(errors))


class ScenarioManifest(BaseModel):
    """Contents of ``scenario.yaml``."""

    id: str
    version: str
    status: Literal["scaffold", "feature", "benchmark", "product-demo"] = "feature"
    timezone: str = "UTC"
    description: str = ""
    persona: str | None = None
    start_at: datetime | None = None
    seed: str | None = None

    @field_validator("start_at", mode="before")
    @classmethod
    def _parse_start(cls, value: object) -> object:
        if isinstance(value, str):
            return _parse_instant(value)
        return value


class ScenarioEvent(BaseModel):
    """One source-layer timeline event."""

    id: str
    at: datetime
    type: str
    source: str
    payload: dict[str, Any] = Field(default_factory=dict)
    content_ref: str | None = None

    @field_validator("at", mode="before")
    @classmethod
    def _parse_at(cls, value: object) -> object:
        if isinstance(value, str):
            return _parse_instant(value)
        return value

    @model_validator(mode="after")
    def _check_source_layer(self) -> ScenarioEvent:
        errors: list[str] = []
        if self.type not in SOURCE_EVENT_TYPES:
            errors.append(
                f"event {self.id!r}: unknown type {self.type!r}; "
                f"expected one of {sorted(SOURCE_EVENT_TYPES)}"
            )
        if self.source not in SOURCE_KINDS:
            errors.append(
                f"event {self.id!r}: unknown source {self.source!r}; "
                f"expected one of {sorted(SOURCE_KINDS)}"
            )
        banned = FORBIDDEN_PAYLOAD_KEYS.intersection(self.payload)
        if banned:
            errors.append(
                f"event {self.id!r}: payload must not embed world-model keys {sorted(banned)}"
            )
        if errors:
            raise ValueError("; ".join(errors))
        return self


class ScenarioPackage(BaseModel):
    """Validated on-disk scenario package."""

    root: Path
    manifest: ScenarioManifest
    events: list[ScenarioEvent] = Field(default_factory=list)
    entities: dict[str, Any] = Field(default_factory=dict)
    persona: dict[str, Any] = Field(default_factory=dict)
    ground_truth_paths: list[str] = Field(default_factory=list)
    attack_paths: list[str] = Field(default_factory=list)

    model_config = {"arbitrary_types_allowed": True}

    @property
    def effective_seed(self) -> str:
        """Seed used for deterministic generation (manifest seed or scenario id)."""
        return self.manifest.seed or self.manifest.id

    def rng(self) -> Random:
        """Return a seeded RNG for corpus / adapter generation helpers."""
        return rng_for_package(self)


@dataclass
class ScenarioLoadResult:
    package: ScenarioPackage | None = None
    errors: list[str] = field(default_factory=list)

    @property
    def ok(self) -> bool:
        return self.package is not None and not self.errors


def _parse_instant(value: str) -> datetime:
    """Parse ISO-8601 instants; bare dates become midnight UTC."""
    text = value.strip()
    if text.endswith("Z"):
        text = text[:-1] + "+00:00"
    try:
        parsed = datetime.fromisoformat(text)
    except ValueError as exc:
        raise ValueError(f"invalid instant {value!r}") from exc
    if parsed.tzinfo is None:
        parsed = parsed.replace(tzinfo=UTC)
    return parsed


def resolve_relative_instant(base: datetime, value: str) -> datetime:
    """Resolve ``+2d`` / ``+3h`` / ``+30m`` offsets relative to ``base``."""
    text = value.strip()
    if not text.startswith("+") and not text.startswith("-"):
        return _parse_instant(text)
    sign = 1 if text[0] == "+" else -1
    body = text[1:]
    if body.endswith("d"):
        return base + sign * timedelta(days=float(body[:-1]))
    if body.endswith("h"):
        return base + sign * timedelta(hours=float(body[:-1]))
    if body.endswith("m"):
        return base + sign * timedelta(minutes=float(body[:-1]))
    raise ValueError(f"unsupported relative instant {value!r}; use +Nd / +Nh / +Nm")


def _read_yaml(path: Path) -> Any:
    with path.open(encoding="utf-8") as handle:
        return yaml.safe_load(handle)


def _try_read_yaml(path: Path, *, label: str) -> tuple[Any | None, str | None]:
    """Read YAML, returning ``(data, error)`` instead of raising."""
    try:
        return _read_yaml(path), None
    except (OSError, UnicodeDecodeError, yaml.YAMLError) as exc:
        return None, f"{label}: {exc}"


def _collect_timeline_files(timeline_dir: Path) -> list[Path]:
    if not timeline_dir.is_dir():
        return []
    return sorted(p for p in timeline_dir.glob("*.yaml") if p.is_file())


def _is_relative_instant(value: object) -> TypeGuard[str]:
    return isinstance(value, str) and (value.startswith("+") or value.startswith("-"))


def _load_events(
    raw_events: list[Any],
    *,
    start_at: datetime | None,
    origin: str,
) -> tuple[list[ScenarioEvent], list[str]]:
    events: list[ScenarioEvent] = []
    errors: list[str] = []
    for index, raw in enumerate(raw_events):
        if not isinstance(raw, dict):
            errors.append(f"{origin}[{index}]: expected mapping")
            continue
        data = dict(raw)
        at_value = data.get("at")
        if isinstance(at_value, str) and _is_relative_instant(at_value):
            if start_at is None:
                errors.append(
                    f"{origin}[{index}]: relative instant {at_value!r} requires "
                    "manifest start_at"
                )
                continue
            try:
                data["at"] = resolve_relative_instant(start_at, at_value)
            except ValueError as exc:
                errors.append(f"{origin}[{index}]: {exc}")
                continue
        try:
            events.append(ScenarioEvent.model_validate(data))
        except (ValidationError, ValueError) as exc:
            errors.append(f"{origin}[{index}]: {exc}")
    return events, errors


def load_scenario(path: Path | str) -> ScenarioPackage:
    """Load and validate a scenario package directory. Raises on failure."""
    result = try_load_scenario(path)
    if not result.ok or result.package is None:
        raise ScenarioValidationError(result.errors or ["unknown load failure"])
    return result.package


def try_load_scenario(path: Path | str) -> ScenarioLoadResult:
    """Load a scenario package, collecting actionable validation errors."""
    root = Path(path).resolve()
    errors: list[str] = []
    if not root.is_dir():
        return ScenarioLoadResult(errors=[f"scenario root is not a directory: {root}"])

    manifest_path = root / "scenario.yaml"
    if not manifest_path.is_file():
        return ScenarioLoadResult(errors=[f"missing scenario.yaml in {root}"])

    try:
        raw_manifest = _read_yaml(manifest_path) or {}
        if not isinstance(raw_manifest, dict):
            raise ValueError("scenario.yaml must be a mapping")
        manifest = ScenarioManifest.model_validate(
            {k: v for k, v in raw_manifest.items() if k != "events"}
        )
    except (OSError, ValidationError, ValueError, yaml.YAMLError) as exc:
        return ScenarioLoadResult(errors=[f"scenario.yaml: {exc}"])

    if root.name != manifest.id:
        errors.append(
            f"directory name {root.name!r} must match manifest id {manifest.id!r}"
        )

    persona: dict[str, Any] = {}
    if manifest.persona:
        persona_path = root / manifest.persona
        if persona_path.is_file():
            loaded, read_err = _try_read_yaml(persona_path, label=manifest.persona)
            if read_err:
                errors.append(read_err)
            elif isinstance(loaded, dict) or loaded is None:
                persona = loaded or {}
            else:
                errors.append(f"{manifest.persona}: expected mapping")
        else:
            errors.append(f"persona file missing: {manifest.persona}")

    entities: dict[str, Any] = {}
    entities_dir = root / "entities"
    if entities_dir.is_dir():
        for entity_file in sorted(entities_dir.glob("*.yaml")):
            loaded, read_err = _try_read_yaml(
                entity_file, label=f"entities/{entity_file.name}"
            )
            if read_err:
                errors.append(read_err)
            elif isinstance(loaded, dict) or loaded is None:
                entities[entity_file.stem] = loaded or {}
            else:
                errors.append(f"entities/{entity_file.name}: expected mapping")

    all_events: list[ScenarioEvent] = []
    timeline_dir = root / "timeline"
    for timeline_file in _collect_timeline_files(timeline_dir):
        loaded, read_err = _try_read_yaml(
            timeline_file, label=f"timeline/{timeline_file.name}"
        )
        if read_err:
            errors.append(read_err)
            continue
        if loaded is None:
            continue
        if isinstance(loaded, dict) and "events" in loaded:
            raw_list = loaded["events"]
        elif isinstance(loaded, list):
            raw_list = loaded
        else:
            errors.append(
                f"timeline/{timeline_file.name}: expected list or {{events: [...]}}"
            )
            continue
        if not isinstance(raw_list, list):
            errors.append(f"timeline/{timeline_file.name}: events must be a list")
            continue
        events, event_errors = _load_events(
            raw_list,
            start_at=manifest.start_at,
            origin=f"timeline/{timeline_file.name}",
        )
        all_events.extend(events)
        errors.extend(event_errors)

    inline = raw_manifest.get("events")
    if inline is not None:
        if not isinstance(inline, list):
            errors.append("scenario.yaml events: expected list")
        else:
            events, event_errors = _load_events(
                inline,
                start_at=manifest.start_at,
                origin="scenario.yaml events",
            )
            all_events.extend(events)
            errors.extend(event_errors)

    counts = Counter(e.id for e in all_events)
    dupes = sorted(event_id for event_id, count in counts.items() if count > 1)
    if dupes:
        errors.append(f"duplicate event ids: {dupes}")

    all_events.sort(key=lambda e: (e.at, e.id))

    ground_truth = (
        sorted(
            str(p.relative_to(root))
            for p in (root / "ground_truth").glob("*.yaml")
            if p.is_file()
        )
        if (root / "ground_truth").is_dir()
        else []
    )
    attacks = (
        sorted(
            str(p.relative_to(root))
            for p in (root / "attacks").glob("*.yaml")
            if p.is_file()
        )
        if (root / "attacks").is_dir()
        else []
    )

    if errors:
        return ScenarioLoadResult(errors=errors)

    return ScenarioLoadResult(
        package=ScenarioPackage(
            root=root,
            manifest=manifest,
            events=all_events,
            entities=entities,
            persona=persona,
            ground_truth_paths=ground_truth,
            attack_paths=attacks,
        )
    )


def discover_scenarios(base: Path | str) -> list[Path]:
    """Return scenario roots under ``base`` that contain ``scenario.yaml``."""
    root = Path(base)
    if not root.is_dir():
        return []
    return sorted(p.parent for p in root.rglob("scenario.yaml"))


__all__ = [
    "ScenarioEvent",
    "ScenarioLoadResult",
    "ScenarioManifest",
    "ScenarioPackage",
    "ScenarioValidationError",
    "discover_scenarios",
    "load_scenario",
    "resolve_relative_instant",
    "rng_for_package",
    "scenario_rng",
    "try_load_scenario",
]
