"""Scenario ``background.yaml`` loading + CorpusBackgroundStream construction (D08c).

Background declarations are simulation / evaluator metadata. They must not appear
on ``SyntheticMailSource`` payloads that Enigma ingests.
"""

from __future__ import annotations

import asyncio
from collections.abc import Sequence
from dataclasses import dataclass, field
from datetime import UTC, datetime
from pathlib import Path
from typing import Any, Literal

import yaml
from pydantic import BaseModel, Field, field_validator, model_validator

from personal_enigma.simulation.corpus.models import CorpusConversation
from personal_enigma.simulation.corpus.registry import CorpusRegistry, default_registry
from personal_enigma.simulation.corpus.safety import assert_public_demo_allowed
from personal_enigma.simulation.corpus.sanitise import sanitise_conversation
from personal_enigma.simulation.corpus.selectors import select_conversations
from personal_enigma.simulation.corpus.streams import CorpusBackgroundStream
from personal_enigma.simulation.corpus.timeline import place_conversation_on_timeline
from personal_enigma.simulation.scenario import ScenarioEvent, ScenarioPackage

DemoProfileName = Literal["feature", "demo", "canonical", "stress"]

# Documented Phase-2 benchmarks (full FinePersonas; not loaded in PR CI).
CANONICAL_BACKGROUND_MESSAGE_TARGET = 5_000
DEMO_BACKGROUND_MESSAGE_TARGET = 1_000


class BackgroundDateRange(BaseModel):
    start: datetime
    end: datetime

    @field_validator("start", "end", mode="before")
    @classmethod
    def _parse(cls, value: object) -> object:
        if not isinstance(value, str):
            return value
        text = value.strip()
        if text.endswith("Z"):
            text = text[:-1] + "+00:00"
        if len(text) == 10 and text[4] == "-" and text[7] == "-":
            text = f"{text}T00:00:00+00:00"
        parsed = datetime.fromisoformat(text)
        if parsed.tzinfo is None:
            parsed = parsed.replace(tzinfo=UTC)
        return parsed

    @model_validator(mode="after")
    def _ordered(self) -> BackgroundDateRange:
        if self.start > self.end:
            raise ValueError("date_range.start must be <= date_range.end")
        return self


class BackgroundClassification(BaseModel):
    """Evaluator-only labels for background traffic."""

    signal_class: Literal["background"] = "background"
    expected_attention: bool = False


class BackgroundEmailSpec(BaseModel):
    """One background email stream declaration."""

    id: str
    corpus: str
    seed: str
    date_range: BackgroundDateRange
    classification: BackgroundClassification = Field(
        default_factory=BackgroundClassification
    )
    # Prefer conversation_count for thread-preserving CI fixtures.
    conversation_count: int | None = Field(default=None, ge=0)
    # Soft / documented message budget (canonical ~5k; demo CI uses a small count).
    message_count: int | None = Field(default=None, ge=0)

    @model_validator(mode="after")
    def _need_budget(self) -> BackgroundEmailSpec:
        if self.conversation_count is None and self.message_count is None:
            raise ValueError(
                f"background email {self.id!r}: set conversation_count and/or message_count"
            )
        return self


class BackgroundConfig(BaseModel):
    """Contents of ``background.yaml`` (simulation metadata, not Enigma input)."""

    profile: DemoProfileName = "demo"
    email: list[BackgroundEmailSpec] = Field(default_factory=list)
    profiles: dict[str, dict[str, Any]] = Field(default_factory=dict)
    notes: str | None = None

    def specs_for_profile(
        self, profile: DemoProfileName | None = None
    ) -> list[BackgroundEmailSpec]:
        """Resolve email specs for ``profile`` (named overlay or top-level email)."""
        name = profile or self.profile
        if name in self.profiles:
            block = self.profiles[name] or {}
            raw_email = block.get("email", [])
            if not isinstance(raw_email, list):
                raise ValueError(f"profiles.{name}.email must be a list")
            return [BackgroundEmailSpec.model_validate(item) for item in raw_email]
        if name == self.profile or not self.profiles:
            return list(self.email)
        raise KeyError(f"unknown background profile {name!r}")


@dataclass(frozen=True, slots=True)
class BackgroundSignalTruth:
    """Evaluator-only classification for one background mail event."""

    evidence_id: str
    signal_class: str = "background"
    expected_attention: bool = False
    stream_id: str | None = None


@dataclass
class BackgroundBuildResult:
    stream: CorpusBackgroundStream
    signals: list[BackgroundSignalTruth] = field(default_factory=list)
    events: list[ScenarioEvent] = field(default_factory=list)
    profile: DemoProfileName = "demo"


def load_background_config(path: Path | str) -> BackgroundConfig:
    root = Path(path)
    raw = yaml.safe_load(root.read_text(encoding="utf-8")) or {}
    if not isinstance(raw, dict):
        raise ValueError(f"{root}: background.yaml must be a mapping")
    return BackgroundConfig.model_validate(raw)


def load_scenario_background(package: ScenarioPackage) -> BackgroundConfig | None:
    path = package.root / "background.yaml"
    if not path.is_file():
        return None
    return load_background_config(path)


def _canonical_emails(package: ScenarioPackage) -> set[str]:
    emails: set[str] = set()
    contacts = package.entities.get("contacts") or {}
    roster = contacts.get("contacts") if isinstance(contacts, dict) else None
    if isinstance(roster, dict):
        for entry in roster.values():
            if isinstance(entry, dict) and entry.get("email"):
                emails.add(str(entry["email"]).lower())
    return emails


def canonical_contact_emails(package: ScenarioPackage) -> set[str]:
    """Public helper for disjointness tests (background vs story roster)."""
    return _canonical_emails(package)


def _self_email(package: ScenarioPackage) -> str | None:
    contacts = package.entities.get("contacts") or {}
    roster = contacts.get("contacts") if isinstance(contacts, dict) else None
    if isinstance(roster, dict):
        self_entry = roster.get("alex") or roster.get("self")
        if isinstance(self_entry, dict) and self_entry.get("email"):
            return str(self_entry["email"])
    return None


def _select_for_budget(
    conversations: Sequence[CorpusConversation],
    *,
    seed: str,
    conversation_count: int | None,
    message_count: int | None,
) -> list[CorpusConversation]:
    if conversation_count is not None:
        selected = select_conversations(
            conversations, seed=seed, count=conversation_count
        )
    else:
        selected = select_conversations(
            conversations, seed=seed, count=len(conversations)
        )
    if message_count is None:
        return selected
    out: list[CorpusConversation] = []
    total = 0
    for conv in selected:
        out.append(conv)
        total += len(conv.messages)
        if total >= message_count:
            break
    return out


async def _load_conversations(
    corpus_id: str, registry: CorpusRegistry
) -> list[CorpusConversation]:
    adapter = registry.adapter_for(corpus_id)
    return [c async for c in adapter.iterate_conversations()]


def build_background_stream(
    package: ScenarioPackage,
    *,
    profile: DemoProfileName | None = None,
    config: BackgroundConfig | None = None,
    registry: CorpusRegistry | None = None,
) -> BackgroundBuildResult:
    """Select, sanitise, and place background mail for a scenario profile."""
    cfg = config if config is not None else load_scenario_background(package)
    if cfg is None:
        return BackgroundBuildResult(
            stream=CorpusBackgroundStream(events=[]),
            profile=profile or "demo",
        )

    resolved_profile: DemoProfileName = profile or cfg.profile
    specs = cfg.specs_for_profile(resolved_profile)
    if not specs:
        return BackgroundBuildResult(
            stream=CorpusBackgroundStream(events=[]),
            profile=resolved_profile,
        )

    reg = registry or default_registry()
    self_email = _self_email(package)
    all_events: list[ScenarioEvent] = []
    signals: list[BackgroundSignalTruth] = []

    for spec in specs:
        manifest = reg.get(spec.corpus)
        assert_public_demo_allowed(manifest)
        conversations = asyncio.run(_load_conversations(spec.corpus, reg))
        selected = _select_for_budget(
            conversations,
            seed=spec.seed,
            conversation_count=spec.conversation_count,
            message_count=spec.message_count,
        )
        for conv in selected:
            try:
                cleaned = sanitise_conversation(
                    conv,
                    rewrite_domains=True,
                    rewrite_seed=spec.seed,
                    preserve_emails={self_email} if self_email else None,
                    self_email=self_email,
                )
            except ValueError:
                # Rejected by secret scanner — skip for public Demo.
                continue
            placed = place_conversation_on_timeline(
                cleaned,
                window_start=spec.date_range.start,
                window_end=spec.date_range.end,
                seed=spec.seed,
                self_email=self_email,
            )
            for event in placed:
                # Defence: never leave evaluator keys on payloads.
                payload = {
                    k: v
                    for k, v in event.payload.items()
                    if k
                    not in {
                        "signal_class",
                        "source_class",
                        "expected_attention",
                        "scenario_source",
                        "is_important",
                    }
                }
                clean_event = event.model_copy(update={"payload": payload})
                all_events.append(clean_event)
                signals.append(
                    BackgroundSignalTruth(
                        evidence_id=str(payload.get("id") or clean_event.id),
                        signal_class=spec.classification.signal_class,
                        expected_attention=spec.classification.expected_attention,
                        stream_id=spec.id,
                    )
                )

    all_events.sort(key=lambda e: (e.at, e.id))
    return BackgroundBuildResult(
        stream=CorpusBackgroundStream(events=all_events),
        signals=signals,
        events=all_events,
        profile=resolved_profile,
    )


__all__ = [
    "CANONICAL_BACKGROUND_MESSAGE_TARGET",
    "DEMO_BACKGROUND_MESSAGE_TARGET",
    "BackgroundBuildResult",
    "BackgroundClassification",
    "BackgroundConfig",
    "BackgroundDateRange",
    "BackgroundEmailSpec",
    "BackgroundSignalTruth",
    "DemoProfileName",
    "build_background_stream",
    "canonical_contact_emails",
    "load_background_config",
    "load_scenario_background",
]
