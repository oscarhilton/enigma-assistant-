"""D08d — machine-noise layer, quiet-day gate, false-alert headline metric."""

from __future__ import annotations

import asyncio
from pathlib import Path

import pytest

from personal_enigma.attention import collect_attention_items
from personal_enigma.evaluation import (
    MAX_BACKGROUND_FALSE_ALERTS_PER_1000,
    ScenarioSignalClass,
    background_false_alerts_per_1000,
    load_ground_truth,
    quiet_day_attention_empty,
)
from personal_enigma.evaluation.observations import (
    EvaluationObservations,
    SurfacedAlert,
)
from personal_enigma.simulation.corpus.noise import (
    NOISE_CATEGORIES,
    QUIET_DAY_MESSAGE_COUNT,
    build_noise_stream,
    category_distribution,
    looks_like_machine_noise,
)
from personal_enigma.simulation.corpus.streams import (
    CanonicalScenarioStream,
    GeneratedNoiseStream,
    merge_stream_events,
)
from personal_enigma.simulation.scenario import load_scenario
from personal_enigma.simulation.sources.mail import SyntheticMailSource, message_from_event

REPO = Path(__file__).resolve().parents[3]
ALEX = REPO / "scenarios" / "alex-v1"
QUIET = REPO / "scenarios" / "feature" / "quiet-day"
NO_ALERT = REPO / "scenarios" / "feature" / "background-no-alert"


def test_noise_templates_cover_distinct_categories() -> None:
    pkg = load_scenario(ALEX)
    built = build_noise_stream(pkg, profile="demo")
    assert len(built.events) == 16
    dist = category_distribution(built.signals)
    present = {k for k, v in dist.items() if v > 0}
    # Mini profile should still hit several categories.
    assert len(present) >= 4
    assert present <= set(NOISE_CATEGORIES)
    assert all(s.signal_class == "noise" for s in built.signals)
    assert all(s.expected_attention is False for s in built.signals)
    brands = " ".join(
        str(e.payload.get("from_name") or "") + " " + str(e.payload.get("subject") or "")
        for e in built.events
    )
    assert "BuildCloud" in brands or "ParcelPost" in brands or "DesignLedger" in brands


def test_seeded_noise_reset_is_deterministic() -> None:
    pkg = load_scenario(ALEX)
    a = build_noise_stream(pkg, profile="demo")
    b = build_noise_stream(pkg, profile="demo")
    assert [e.id for e in a.events] == [e.id for e in b.events]
    assert [(s.evidence_id, s.category) for s in a.signals] == [
        (s.evidence_id, s.category) for s in b.signals
    ]


def test_canonical_background_and_noise_merge_chronologically() -> None:
    pkg = load_scenario(ALEX)
    source = SyntheticMailSource.for_scenario(pkg, profile="demo")

    async def _run() -> list[dict]:
        batch = await source.get_changes(None)
        return list(batch.items)

    items = asyncio.run(_run())
    # Canonical + background (5) + noise (16) at minimum.
    assert len(items) >= 20
    stamps = [
        (
            item.get("received_at") or item.get("sent_at") or "",
            item.get("provider_message_id") or item.get("id"),
        )
        for item in items
    ]
    assert stamps == sorted(stamps)
    for item in items:
        assert "signal_class" not in item
        assert "source_class" not in item
        assert "expected_attention" not in item


def test_ground_truth_noise_signals_match_builder() -> None:
    truth = load_ground_truth(ALEX / "ground_truth")
    noise = truth.signals_for_class(ScenarioSignalClass.NOISE)
    assert noise
    assert all(s.expected_attention is False for s in noise)
    pkg = load_scenario(ALEX)
    built = build_noise_stream(pkg, profile="demo")
    assert {s.evidence_id for s in noise} == {s.evidence_id for s in built.signals}


def test_mini_profile_background_false_alert_rate_under_threshold() -> None:
    """Headline metric on alex-v1 demo (mini) profile — correct silence scores 0."""
    truth = load_ground_truth(ALEX / "ground_truth")
    pkg = load_scenario(ALEX)
    noise = build_noise_stream(pkg, profile="demo")
    message_count = len(noise.events)
    assert message_count == 16

    # Product-correct: no alerts citing noise/background evidence.
    silent = background_false_alerts_per_1000(
        truth,
        [],
        message_count=message_count,
    )
    assert silent.false_alerts == 0
    assert silent.per_1000 == 0.0
    assert silent.passed
    assert silent.per_1000 <= MAX_BACKGROUND_FALSE_ALERTS_PER_1000

    # Naive: alert on every noise evidence → fails the gate.
    naive = [
        SurfacedAlert(id=s.evidence_id, evidence_ids=[s.evidence_id])
        for s in noise.signals
    ]
    noisy = background_false_alerts_per_1000(
        truth,
        naive,
        message_count=message_count,
    )
    assert noisy.false_alerts == message_count
    assert noisy.per_1000 == 1000.0
    assert not noisy.passed


def test_quiet_day_hard_gate_attention_empty() -> None:
    """183 sludge messages, 0 obligations → attention_items == 0 exactly."""
    pkg = load_scenario(QUIET)
    truth = load_ground_truth(QUIET / "ground_truth")
    assert truth.obligations == []

    built = build_noise_stream(pkg, profile="quiet_day")
    assert len(built.events) == QUIET_DAY_MESSAGE_COUNT == 183

    source = SyntheticMailSource.for_scenario(
        pkg,
        profile="quiet_day",
        include_background=False,
    )

    async def _messages() -> list:
        batch = await source.get_changes(None)
        from personal_enigma.domain import PrivateMessage

        return [PrivateMessage.model_validate(item) for item in batch.items]

    messages = asyncio.run(_messages())
    assert len(messages) == 183
    assert all(looks_like_machine_noise(m) for m in messages)

    # Product path: suppress machine sludge before collecting attention.
    surviving = [m for m in messages if not looks_like_machine_noise(m)]
    attention_items = collect_attention_items(messages=surviving)
    assert len(attention_items) == 0
    assert quiet_day_attention_empty(
        attention_items=attention_items,
        obligation_count=len(truth.obligations),
    )

    rate = background_false_alerts_per_1000(
        truth,
        EvaluationObservations(alerts=[]).alerts,
        message_count=len(messages),
    )
    assert rate.false_alerts == 0
    assert rate.passed


def test_background_no_alert_feature_scenario() -> None:
    pkg = load_scenario(NO_ALERT)
    assert pkg.manifest.id == "background-no-alert"
    built = build_noise_stream(pkg)
    assert len(built.events) == 183
    truth = load_ground_truth(NO_ALERT / "ground_truth")
    assert truth.obligations == []
    noise = truth.signals_for_class(ScenarioSignalClass.NOISE)
    assert len(noise) == 183

    events = merge_stream_events(
        [
            CanonicalScenarioStream(events=pkg),
            GeneratedNoiseStream(events=built.events),
        ]
    )
    mail = [e for e in events if e.type in {"email.receive", "email.send"}]
    assert len(mail) == 183
    for event in mail:
        msg = message_from_event(event)
        assert looks_like_machine_noise(msg)
        dump = msg.model_dump(mode="json")
        assert "signal_class" not in dump

    attention_items = collect_attention_items(
        messages=[
            message_from_event(e)
            for e in mail
            if not looks_like_machine_noise(message_from_event(e))
        ]
    )
    assert len(attention_items) == 0


def test_looks_like_machine_noise_on_template_payloads() -> None:
    pkg = load_scenario(ALEX)
    built = build_noise_stream(pkg, profile="demo")
    for event in built.events:
        assert looks_like_machine_noise(event.payload)
        assert looks_like_machine_noise(message_from_event(event))


def test_unknown_noise_profile_raises() -> None:
    pkg = load_scenario(ALEX)
    with pytest.raises(KeyError, match="unknown noise profile"):
        build_noise_stream(pkg, profile="not-a-real-profile")
