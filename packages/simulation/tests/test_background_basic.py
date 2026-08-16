"""F-background-basic — canonical obligation survives ~50 background messages."""

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
    build_background_stream,
    load_scenario_background,
)
from personal_enigma.simulation.corpus.streams import CanonicalScenarioStream, merge_stream_events
from personal_enigma.simulation.scenario import load_scenario
from personal_enigma.simulation.sources.mail import SyntheticMailSource

REPO = Path(__file__).resolve().parents[3]
BASIC = REPO / "scenarios" / "feature" / "background-basic"


def test_background_basic_package_loads() -> None:
    pkg = load_scenario(BASIC)
    assert pkg.manifest.id == "background-basic"
    assert pkg.manifest.status == "feature"
    assert 5 <= len(pkg.events) <= 10
    assert any(e.id == "bb-mail-canonical" for e in pkg.events)
    cfg = load_scenario_background(pkg)
    assert cfg is not None
    specs = cfg.specs_for_profile("feature")
    assert len(specs) == 1
    assert specs[0].message_count == 50
    assert specs[0].classification.signal_class == "background"
    assert specs[0].classification.expected_attention is False


def test_background_basic_builds_about_fifty_messages() -> None:
    pkg = load_scenario(BASIC)
    built = build_background_stream(pkg)
    assert 48 <= len(built.events) <= 60
    assert len(built.signals) == len(built.events)
    assert all(s.signal_class == "background" for s in built.signals)
    assert all(s.expected_attention is False for s in built.signals)


def test_background_basic_merges_chronologically_around_canonical() -> None:
    pkg = load_scenario(BASIC)
    built = build_background_stream(pkg)
    merged = merge_stream_events(
        [
            CanonicalScenarioStream(events=pkg),
            built.stream,
        ]
    )
    stamps = [(e.at, e.id) for e in merged]
    assert stamps == sorted(stamps)
    mail = [e for e in merged if e.type in {"email.receive", "email.send"}]
    assert any(e.id == "bb-mail-canonical" for e in mail)
    background_mail = [e for e in mail if e.id.startswith("corpus:")]
    assert 48 <= len(background_mail) <= 60
    assert any(e.id == "bb-mail-canonical" for e in mail)


def test_background_basic_payloads_omit_evaluator_labels() -> None:
    pkg = load_scenario(BASIC)
    built = build_background_stream(pkg)
    source = SyntheticMailSource.for_scenario(
        pkg,
        profile="feature",
        include_noise=False,
        background_stream=built.stream,
    )

    async def _run() -> list[dict]:
        batch = await source.get_changes(None)
        return list(batch.items)

    items = asyncio.run(_run())
    assert len(items) >= 49  # canonical + ~50 background
    canonical = [i for i in items if i.get("provider_message_id") == "mail-maya-priorities"]
    assert len(canonical) == 1
    for item in items:
        assert "signal_class" not in item
        assert "source_class" not in item
        assert "expected_attention" not in item
        assert "scenario_source" not in item
        assert "is_important" not in item


def test_background_basic_ground_truth_signals_match_builder() -> None:
    truth = load_ground_truth(BASIC / "ground_truth")
    bg = truth.signals_for_class(ScenarioSignalClass.BACKGROUND)
    assert len(bg) >= 48
    assert all(s.expected_attention is False for s in bg)
    pkg = load_scenario(BASIC)
    built = build_background_stream(pkg)
    assert {s.evidence_id for s in bg} == {s.evidence_id for s in built.signals}
    assert truth.obligation_by_id("obligation_q2_priorities") is not None


def test_background_basic_critical_recall_holds(tmp_path: Path) -> None:
    """Spine vs spine+background: critical recall must not drop >1 pp."""
    truth = load_ground_truth(BASIC / "ground_truth")
    at = datetime(2026, 3, 17, 12, 0, tzinfo=UTC)
    oid = "obligation_q2_priorities"
    obligation = truth.obligation_by_id(oid)
    assert obligation is not None
    assert obligation.is_open_at(at)

    alerts = [
        SurfacedAlert(
            id=oid,
            obligation_ids=[oid],
            evidence_ids=["mail-maya-priorities"],
            surfaced_at=at,
        )
    ]
    obs = EvaluationObservations(evaluated_at=at, alerts=alerts)
    runner = EvaluationRunner(reports_root=tmp_path / "reports")
    spine = runner.run(
        "background-basic-spine",
        ground_truth=truth,
        observations=obs,
        run_id="bb-spine",
        write=False,
    )
    with_bg = runner.run(
        "background-basic-with-bg",
        ground_truth=truth,
        observations=obs,
        run_id="bb-bg",
        write=False,
    )
    ab = storyline_recall_under_noise(spine.metrics, with_bg.metrics)
    assert ab.passed
    assert ab.drop <= 0.01
    assert float(with_bg.metrics["attention"]["critical_recall"]) == 1.0
    regression = compare_storyline_ab(spine.metrics, with_bg.metrics)
    assert regression.passed

    pkg = load_scenario(BASIC)
    built = build_background_stream(pkg)
    assert len(built.events) >= 48
