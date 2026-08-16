"""D08c — canonical + background merge, isolation, and A/B critical recall."""

from __future__ import annotations

import asyncio
from datetime import UTC, datetime
from pathlib import Path

from personal_enigma.evaluation import (
    EvaluationObservations,
    EvaluationRunner,
    ScenarioSignalClass,
    compare_storyline_ab,
    load_ground_truth,
    storyline_recall_under_noise,
)
from personal_enigma.evaluation.observations import SurfacedAlert
from personal_enigma.simulation.corpus.background import (
    CANONICAL_BACKGROUND_MESSAGE_TARGET,
    build_background_stream,
    canonical_contact_emails,
    load_scenario_background,
)
from personal_enigma.simulation.corpus.streams import CanonicalScenarioStream, merge_stream_events
from personal_enigma.simulation.scenario import load_scenario
from personal_enigma.simulation.sources.mail import SyntheticMailSource

REPO = Path(__file__).resolve().parents[3]
ALEX = REPO / "scenarios" / "alex-v1"


def test_background_yaml_demo_profile_is_small() -> None:
    pkg = load_scenario(ALEX)
    cfg = load_scenario_background(pkg)
    assert cfg is not None
    assert cfg.profile == "demo"
    demo = cfg.specs_for_profile("demo")
    assert len(demo) == 1
    assert demo[0].conversation_count == 2
    assert demo[0].message_count is not None and demo[0].message_count <= 16
    canonical = cfg.specs_for_profile("canonical")
    assert canonical[0].message_count == CANONICAL_BACKGROUND_MESSAGE_TARGET


def test_seeded_background_reset_is_deterministic() -> None:
    pkg = load_scenario(ALEX)
    a = build_background_stream(pkg, profile="demo")
    b = build_background_stream(pkg, profile="demo")
    assert [e.id for e in a.events] == [e.id for e in b.events]
    assert [(s.evidence_id, s.signal_class, s.expected_attention) for s in a.signals] == [
        (s.evidence_id, s.signal_class, s.expected_attention) for s in b.signals
    ]
    assert a.signals
    assert all(s.signal_class == "background" for s in a.signals)
    assert all(s.expected_attention is False for s in a.signals)


def test_canonical_and_background_merge_chronologically() -> None:
    pkg = load_scenario(ALEX)
    built = build_background_stream(pkg, profile="demo")
    merged = merge_stream_events(
        [
            CanonicalScenarioStream(events=pkg),
            built.stream,
        ]
    )
    stamps = [(e.at, e.id) for e in merged]
    assert stamps == sorted(stamps)
    assert any(e.id.startswith("corpus:") for e in merged)
    assert any(not e.id.startswith("corpus:") for e in merged)


def test_enigma_mail_payloads_omit_signal_and_source_class() -> None:
    pkg = load_scenario(ALEX)
    source = SyntheticMailSource.for_scenario(pkg, profile="demo")

    async def _run() -> list[dict]:
        batch = await source.get_changes(None)
        return list(batch.items)

    items = asyncio.run(_run())
    assert len(items) > len(
        [e for e in pkg.events if e.type in {"email.receive", "email.send"}]
    )
    for item in items:
        assert "signal_class" not in item
        assert "source_class" not in item
        assert "expected_attention" not in item
        assert "scenario_source" not in item
        assert "is_important" not in item


def test_background_contacts_disjoint_from_canonical_roster() -> None:
    pkg = load_scenario(ALEX)
    built = build_background_stream(pkg, profile="demo")
    roster = canonical_contact_emails(pkg)
    self_email = "alex.morgan@northwind.example"
    for event in built.events:
        sender = str(event.payload.get("from") or "").lower()
        if sender and sender != self_email:
            assert sender not in roster, f"background sender collides: {sender}"


def test_ground_truth_background_signals_match_builder() -> None:
    truth = load_ground_truth(ALEX / "ground_truth")
    bg = truth.signals_for_class(ScenarioSignalClass.BACKGROUND)
    assert bg
    assert all(s.expected_attention is False for s in bg)
    pkg = load_scenario(ALEX)
    built = build_background_stream(pkg, profile="demo")
    truth_ids = {s.evidence_id for s in bg}
    built_ids = {s.evidence_id for s in built.signals}
    assert built_ids == truth_ids


def test_ab_critical_recall_holds_with_mini_background(tmp_path: Path) -> None:
    """Mini-scale A/B: same alerts → critical recall must not drop >1 pp."""
    truth = load_ground_truth(ALEX / "ground_truth")
    at = datetime(2026, 1, 20, 12, 0, tzinfo=UTC)
    expected_ids = [
        o.id
        for o in truth.obligations
        if o.importance in {"critical", "high"} and o.is_open_at(at)
    ]
    active = []
    for oid in expected_ids:
        window = truth.window_for(oid)
        if window is None or window.is_active_at(at):
            active.append(oid)
    alerts = [
        SurfacedAlert(id=oid, obligation_ids=[oid], surfaced_at=at) for oid in active
    ] or [
        SurfacedAlert(
            id="obligation_q1_roadmap",
            obligation_ids=["obligation_q1_roadmap"],
            surfaced_at=at,
        )
    ]

    obs = EvaluationObservations(evaluated_at=at, alerts=alerts)
    runner = EvaluationRunner(reports_root=tmp_path / "reports")
    spine = runner.run(
        "alex-v1-spine",
        ground_truth=truth,
        observations=obs,
        run_id="ab-spine",
        write=False,
    )
    with_bg = runner.run(
        "alex-v1-with-bg",
        ground_truth=truth,
        observations=obs,
        run_id="ab-bg",
        write=False,
    )
    ab = storyline_recall_under_noise(spine.metrics, with_bg.metrics)
    assert ab.passed
    assert ab.drop <= 0.01
    regression = compare_storyline_ab(spine.metrics, with_bg.metrics)
    assert regression.passed

    pkg = load_scenario(ALEX)
    built = build_background_stream(pkg, profile="demo")
    assert len(built.events) >= 3
