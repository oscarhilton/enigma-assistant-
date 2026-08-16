"""Hard invariants for Demo Mode background corpus scaffolding (D08b)."""

from __future__ import annotations

import asyncio
import json
from datetime import UTC, datetime
from pathlib import Path

import pytest

from personal_enigma.evaluation.ground_truth import ScenarioSignalClass
from personal_enigma.simulation.corpus.adapters.finepersonas import FinePersonasAdapter
from personal_enigma.simulation.corpus.manifest import CorpusManifest, load_manifest
from personal_enigma.simulation.corpus.models import CorpusProvenance
from personal_enigma.simulation.corpus.safety import (
    PublicDemoCorpusError,
    assert_public_demo_allowed,
)
from personal_enigma.simulation.corpus.sanitise import (
    GENERATION_METADATA_KEYS,
    sanitise_raw_record,
)
from personal_enigma.simulation.corpus.selectors import select_conversations
from personal_enigma.simulation.corpus.streams import (
    CanonicalScenarioStream,
    CorpusBackgroundStream,
    GeneratedNoiseStream,
)
from personal_enigma.simulation.scenario import ScenarioEvent
from personal_enigma.simulation.sources.mail import SyntheticMailSource

FIXTURE = Path(__file__).resolve().parent / "fixtures" / "corpus" / "finepersonas-mini"


def test_scenario_signal_class_enum_values() -> None:
    assert ScenarioSignalClass.CANONICAL.value == "canonical"
    assert ScenarioSignalClass.BACKGROUND.value == "background"
    assert ScenarioSignalClass.NOISE.value == "noise"
    assert ScenarioSignalClass.ADVERSARIAL.value == "adversarial"


def test_public_demo_rejects_non_synthetic_confirmed() -> None:
    bad = CorpusManifest(
        id="enron-sample",
        provenance=CorpusProvenance.PUBLIC_REAL,
        profiles_allowed={"public_demo": True, "developer": True, "stress": True},
    )
    with pytest.raises(PublicDemoCorpusError, match="synthetic_confirmed"):
        assert_public_demo_allowed(bad)

    unknown = CorpusManifest(
        id="mystery",
        provenance=CorpusProvenance.UNKNOWN,
        profiles_allowed={"public_demo": True, "developer": True, "stress": True},
    )
    with pytest.raises(PublicDemoCorpusError):
        assert_public_demo_allowed(unknown)


def test_public_demo_accepts_finepersonas_mini() -> None:
    manifest = load_manifest(FIXTURE / "manifest.yaml")
    assert manifest.provenance == CorpusProvenance.SYNTHETIC_CONFIRMED
    assert_public_demo_allowed(manifest)


def test_seeded_selection_deterministic_for_mini_fixture() -> None:
    async def _load() -> list:
        adapter = FinePersonasAdapter(
            load_manifest(FIXTURE / "manifest.yaml"),
            root=FIXTURE,
        )
        return [c async for c in adapter.iterate_conversations()]

    conversations = asyncio.run(_load())
    assert len(conversations) == 3
    a = select_conversations(conversations, seed="alex-v1-email-background-v1", count=2)
    b = select_conversations(conversations, seed="alex-v1-email-background-v1", count=2)
    assert [c.id for c in a] == [c.id for c in b]
    different = select_conversations(conversations, seed="other-seed", count=2)
    # Different seed may or may not differ for n=2 of 3; ensure API is stable and
    # same seed never drifts across calls (already checked). Prefer inequality when possible.
    assert len(different) == 2


def test_sanitiser_strips_generation_metadata_fields() -> None:
    raw = json.loads((FIXTURE / "conversations.jsonl").read_text(encoding="utf-8").splitlines()[0])
    assert any(key in raw for key in GENERATION_METADATA_KEYS)
    cleaned = sanitise_raw_record(raw)
    assert GENERATION_METADATA_KEYS.isdisjoint(cleaned.keys())
    for email in cleaned["emails"]:
        assert GENERATION_METADATA_KEYS.isdisjoint(email.keys())


def test_signal_class_never_visible_on_synthetic_mail_messages() -> None:
    canonical = ScenarioEvent(
        id="canon-1",
        at=datetime(2026, 1, 10, 9, 0, tzinfo=UTC),
        source="mail",
        type="email.receive",
        payload={
            "id": "canon-1",
            "subject": "Atlas review",
            "body_text": "Please review Atlas",
            "from": "maya@northstar.example",
            "to": ["alex@morgan.example"],
            # Maliciously attempt to sneak evaluator metadata onto the event:
            "signal_class": ScenarioSignalClass.CANONICAL.value,
            "expected_attention": True,
        },
    )
    background = ScenarioEvent(
        id="bg-1",
        at=datetime(2026, 1, 10, 10, 0, tzinfo=UTC),
        source="mail",
        type="email.receive",
        payload={
            "id": "bg-1",
            "subject": "Invoice copy",
            "body_text": "FYI",
            "from": "sam@company-0001.example",
            "to": ["alex@morgan.example"],
            "signal_class": ScenarioSignalClass.BACKGROUND.value,
        },
    )
    noise = ScenarioEvent(
        id="noise-1",
        at=datetime(2026, 1, 10, 11, 0, tzinfo=UTC),
        source="mail",
        type="email.receive",
        payload={
            "id": "noise-1",
            "subject": "BuildCloud notification",
            "body_text": "Build finished",
            "from": "noreply@buildcloud.example",
            "to": ["alex@morgan.example"],
            "signal_class": ScenarioSignalClass.NOISE.value,
        },
    )

    source = SyntheticMailSource(
        streams=[
            CanonicalScenarioStream(events=[canonical]),
            CorpusBackgroundStream(events=[background]),
            GeneratedNoiseStream(events=[noise]),
        ]
    )

    async def _run() -> list[dict]:
        batch = await source.get_changes(None)
        return list(batch.items)

    items = asyncio.run(_run())
    assert len(items) == 3
    for item in items:
        assert "signal_class" not in item
        assert "expected_attention" not in item
        assert "scenario_source" not in item
        assert "is_important" not in item
