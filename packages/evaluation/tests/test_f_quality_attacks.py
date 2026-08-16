"""F-quality attacks: volume-vs-importance + retrieval-keyword-pollution."""

from __future__ import annotations

from datetime import UTC, datetime
from pathlib import Path

from personal_enigma.attention import AttentionItem, HeuristicAttentionEngine
from personal_enigma.attention.kinds import AttentionKind
from personal_enigma.embeddings import (
    FakeEmbeddingModel,
    InMemoryVectorIndex,
    RetrievalPipeline,
    passages_from_calendar,
    passages_from_email,
    passages_from_reminder,
)
from personal_enigma.evaluation import (
    EvaluationObservations,
    EvaluationRunner,
    ScenarioSignalClass,
    load_ground_truth,
)
from personal_enigma.evaluation.metrics import retrieval as retrieval_metrics
from personal_enigma.evaluation.observations import RetrievalObservation, SurfacedAlert
from personal_enigma.simulation.scenario import load_scenario

REPO = Path(__file__).resolve().parents[3]
FEATURE = REPO / "scenarios" / "feature"

EVALUATOR_KEYS = frozenset(
    {
        "signal_class",
        "source_class",
        "expected_attention",
        "scenario_source",
        "is_important",
    }
)


def test_volume_vs_importance_package_and_gt() -> None:
    pkg = load_scenario(FEATURE / "background-volume-vs-importance")
    assert pkg.manifest.id == "background-volume-vs-importance"
    mail = [e for e in pkg.events if e.type in {"email.receive", "email.send"}]
    volume = [e for e in mail if str(e.payload.get("thread_id")) == "thread-emoji-day"]
    critical = [e for e in mail if str(e.payload.get("thread_id")) == "thread-visa-letter"]
    assert len(volume) >= 30
    assert 1 <= len(critical) <= 3
    assert all(EVALUATOR_KEYS.isdisjoint(e.payload.keys()) for e in pkg.events)

    truth = load_ground_truth(FEATURE / "background-volume-vs-importance" / "ground_truth")
    bg = truth.signals_for_class(ScenarioSignalClass.BACKGROUND)
    assert len(bg) >= 30
    assert all(s.expected_attention is False for s in bg)
    assert truth.obligation_by_id("obligation_visa_letter") is not None


def test_volume_vs_importance_attention_prefers_obligation_not_frequency() -> None:
    """High raw scores on many fluff inferences must not beat the critical reminder."""
    engine = HeuristicAttentionEngine()
    critical = AttentionItem(
        title="Sign visa letter for Jordan",
        body="HR needs signed letter before Friday noon",
        kind=AttentionKind.EXPLICIT_REMINDER,
        score=5.0,
        evidence_ids=["mail-critical-visa", "rem-visa-letter"],
    )
    # Frequency-biased failure mode: invent one high-score inference per fluff mail.
    fluff = [
        AttentionItem(
            title=f"Emoji of the day #{i}",
            body=f"Fluff thread message {i}",
            kind=AttentionKind.INFERRED_COMMITMENT,
            score=99.0,  # naive frequency/similarity bias
            evidence_ids=[f"mail-vol-{i:02d}"],
        )
        for i in range(1, 31)
    ]
    ranked = engine.rank([*fluff, critical])
    assert ranked[0].evidence_ids == critical.evidence_ids
    assert ranked[0].kind == AttentionKind.EXPLICIT_REMINDER
    # Volume must not dominate the top of the surface.
    top_evidence = {eid for item in ranked[:3] for eid in item.evidence_ids}
    assert "mail-critical-visa" in top_evidence or "rem-visa-letter" in top_evidence
    assert sum(1 for item in ranked[:5] if item.kind == AttentionKind.INFERRED_COMMITMENT) < 5


def test_volume_vs_importance_critical_recall_holds(tmp_path: Path) -> None:
    truth = load_ground_truth(FEATURE / "background-volume-vs-importance" / "ground_truth")
    at = datetime(2026, 4, 7, 12, 0, tzinfo=UTC)
    oid = "obligation_visa_letter"
    alerts = [
        SurfacedAlert(
            id=oid,
            obligation_ids=[oid],
            evidence_ids=["mail-critical-visa", "rem-visa-letter"],
            surfaced_at=at,
        )
    ]
    # Even if fluff also surfaces, critical recall must remain 1.0 for the obligation.
    fluff_alerts = [
        SurfacedAlert(
            id=f"fluff-{i}",
            evidence_ids=[f"mail-vol-{i:02d}"],
            surfaced_at=at,
            score=0.1,
        )
        for i in range(1, 6)
    ]
    obs = EvaluationObservations(evaluated_at=at, alerts=[*alerts, *fluff_alerts])
    report = EvaluationRunner(reports_root=tmp_path / "reports").run(
        "volume-vs-importance",
        ground_truth=truth,
        observations=obs,
        run_id="bv-quality",
        write=False,
    )
    assert float(report.metrics["attention"]["critical_recall"]) == 1.0
    assert report.metrics["attention"]["surfaced_critical"] == 1


def test_keyword_pollution_package_and_gt() -> None:
    pkg = load_scenario(FEATURE / "retrieval-keyword-pollution")
    assert pkg.manifest.id == "retrieval-keyword-pollution"
    mail = [e for e in pkg.events if e.type == "email.receive"]
    pollution = [
        e
        for e in mail
        if str(e.payload.get("id", "")).startswith("mail-review-pollute-")
    ]
    assert len(pollution) >= 20
    assert all("review" in str(e.payload.get("subject", "")).lower() for e in pollution)
    assert any(
        e.payload.get("id") == "mail-atlas-review" for e in mail
    ), "canonical Atlas evidence required"
    assert all(EVALUATOR_KEYS.isdisjoint(e.payload.keys()) for e in pkg.events)

    truth = load_ground_truth(FEATURE / "retrieval-keyword-pollution" / "ground_truth")
    assert truth.obligation_by_id("obligation_atlas_review") is not None
    bg = truth.signals_for_class(ScenarioSignalClass.BACKGROUND)
    assert len(bg) >= 20


def test_keyword_pollution_canonical_evidence_recall_at_k() -> None:
    """Shared 'review' keyword must not drown Atlas evidence in top-k."""
    pkg = load_scenario(FEATURE / "retrieval-keyword-pollution")
    passages = []
    for event in pkg.events:
        payload = event.payload
        if event.type in {"email.receive", "email.send"}:
            passages.extend(
                passages_from_email(
                    message_id=str(payload["id"]),
                    subject=str(payload.get("subject") or ""),
                    body_text=str(payload.get("body_text") or payload.get("snippet") or ""),
                )
            )
        elif event.type == "reminder.upsert":
            passages.extend(
                passages_from_reminder(
                    reminder_id=str(payload["id"]),
                    title=str(payload.get("title") or ""),
                    notes=str(payload.get("notes") or ""),
                )
            )
        elif event.type == "calendar.upsert":
            passages.extend(
                passages_from_calendar(
                    event_id=str(payload["id"]),
                    title=str(payload.get("title") or ""),
                    description=str(payload.get("notes") or ""),
                )
            )

    pipeline = RetrievalPipeline(
        model=FakeEmbeddingModel(dimensions=64),
        index=InMemoryVectorIndex(),
    )
    assert pipeline.index_passages(passages) == len(passages)

    query = "Review Atlas proposal before Friday"
    k = 5
    hits = pipeline.retrieve(query, limit=k)
    assert hits

    def _evidence_id(passage_id: str) -> str:
        # passages use prefixes like email:mail-atlas-review:0
        parts = passage_id.split(":")
        return parts[1] if len(parts) >= 2 else passage_id

    hit_evidence = [_evidence_id(h.id) for h in hits]
    relevant = ["mail-atlas-review", "rem-atlas-review", "cal-atlas-standup"]
    recall = retrieval_metrics.canonical_evidence_recall_at_k(
        retrieved_ids=hit_evidence,
        relevant_ids=relevant,
        k=k,
    )
    precision = retrieval_metrics.precision_at_k(
        retrieved_ids=hit_evidence,
        relevant_ids=relevant,
        k=k,
    )
    # At least one Atlas evidence chunk must survive keyword pollution.
    assert recall >= 1.0 / len(relevant)
    assert any(eid in relevant for eid in hit_evidence)
    assert "mail-atlas-review" in hit_evidence or any(
        "atlas" in h.text.lower() for h in hits[:3]
    )
    # Pollution-only top-k would yield precision 0.
    assert precision > 0.0

    obs = RetrievalObservation(
        query_id="atlas-review",
        hits=hit_evidence,
        relevant_ids=relevant,
        k=k,
    )
    metrics = retrieval_metrics.compute_retrieval_metrics([obs])
    assert metrics.canonical_evidence_recall_at_k == recall
    assert metrics.precision_at_k == precision
    assert metrics.queries == 1


def test_canonical_evidence_recall_metric_unit() -> None:
    assert (
        retrieval_metrics.canonical_evidence_recall_at_k(
            retrieved_ids=["a", "x", "b"],
            relevant_ids=["a", "b", "c"],
            k=3,
        )
        == 2 / 3
    )
    assert (
        retrieval_metrics.precision_at_k(
            retrieved_ids=["a", "x", "b"],
            relevant_ids=["a", "b", "c"],
            k=3,
        )
        == 2 / 3
    )
