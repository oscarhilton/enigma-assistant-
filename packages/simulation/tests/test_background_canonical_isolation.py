"""F-background-canonical-isolation — evaluator labels never reach Enigma mail."""

from __future__ import annotations

import asyncio
from pathlib import Path

from personal_enigma.evaluation import ScenarioSignalClass, load_ground_truth
from personal_enigma.simulation.corpus.background import build_background_stream
from personal_enigma.simulation.scenario import load_scenario
from personal_enigma.simulation.sources.mail import SyntheticMailSource

REPO = Path(__file__).resolve().parents[3]
FEATURE = REPO / "scenarios" / "feature" / "background-canonical-isolation"

EVALUATOR_KEYS = frozenset(
    {
        "signal_class",
        "source_class",
        "expected_attention",
        "scenario_source",
        "is_important",
    }
)


def test_ground_truth_store_is_separate_from_scenario_events() -> None:
    """GroundTruth corpus lives under ground_truth/ — never mixed into ingest events."""
    pkg = load_scenario(FEATURE)
    gt_root = FEATURE / "ground_truth"
    assert gt_root.is_dir()
    assert gt_root.parent == pkg.root
    assert gt_root != pkg.root
    assert not (pkg.root / "signal_class").exists()

    truth = load_ground_truth(gt_root)
    assert truth.obligations
    assert any("background_signals.yaml" in p for p in truth.source_paths)

    canonical = truth.signals_for_class(ScenarioSignalClass.CANONICAL)
    background = truth.signals_for_class(ScenarioSignalClass.BACKGROUND)
    assert any(s.evidence_id == "mail-isolation-critical" for s in canonical)
    assert all(s.expected_attention is True for s in canonical)
    assert background
    assert all(s.expected_attention is False for s in background)

    for event in pkg.events:
        assert EVALUATOR_KEYS.isdisjoint(event.payload.keys())


def test_merged_mail_dumps_omit_evaluator_keys() -> None:
    pkg = load_scenario(FEATURE)
    built = build_background_stream(pkg, profile="feature")
    assert built.signals
    assert all(s.signal_class == "background" for s in built.signals)

    source = SyntheticMailSource.for_scenario(pkg, profile="feature", include_noise=False)

    async def _run() -> list[dict]:
        batch = await source.get_changes(None)
        return list(batch.items)

    items = asyncio.run(_run())
    assert items
    # Canonical + background merge: more than authored scenario mail alone.
    authored = [e for e in pkg.events if e.type in {"email.receive", "email.send"}]
    assert len(items) > len(authored)
    assert any(
        item.get("provider_message_id") == "mail-isolation-critical"
        or (item.get("subject") and "Board pack" in str(item.get("subject")))
        for item in items
    )

    for item in items:
        assert EVALUATOR_KEYS.isdisjoint(item.keys())
        blob = str(item)
        assert "signal_class" not in blob
        assert "expected_attention" not in blob
        assert "source_class" not in blob


def test_builder_ground_truth_ids_match_store() -> None:
    pkg = load_scenario(FEATURE)
    truth = load_ground_truth(FEATURE / "ground_truth")
    built = build_background_stream(pkg, profile="feature")
    truth_bg = {
        s.evidence_id for s in truth.signals_for_class(ScenarioSignalClass.BACKGROUND)
    }
    built_ids = {s.evidence_id for s in built.signals}
    assert built_ids == truth_bg
