"""F-unrelated-machine-mail-not-merged: PrizeVault-style commitment merge pollution."""

from __future__ import annotations

from pathlib import Path

from personal_enigma.attention.kinds import AttentionKind
from personal_enigma.evaluation import (
    ScenarioSignalClass,
    attention_candidate_fingerprint,
    commitment_merge_pollution_traces,
    compare_machine_mail_merge_pollution,
    load_ground_truth,
    storyline_ab_report,
)
from personal_enigma.fixtures import build_message, build_person_ref
from personal_enigma.obligations import merge_sources_to_attention
from personal_enigma.simulation.scenario import load_scenario

REPO = Path(__file__).resolve().parents[3]
FEATURE = REPO / "scenarios" / "feature"
SCENARIO = FEATURE / "unrelated-machine-mail-not-merged"

MACHINE_MAIL_IDS = (
    "mail-prizevault",
    "mail-buildcloud",
    "mail-productpulse",
    "mail-growthkit",
    "mail-designledger",
)
BRAND_BY_ID = {
    "mail-prizevault": "PrizeVault",
    "mail-buildcloud": "BuildCloud",
    "mail-productpulse": "ProductPulse",
    "mail-growthkit": "GrowthKit",
    "mail-designledger": "DesignLedger",
}

EVALUATOR_KEYS = frozenset(
    {
        "signal_class",
        "source_class",
        "expected_attention",
        "scenario_source",
        "is_important",
    }
)


def test_pollution_trace_schema_in_storyline_ab_report() -> None:
    traces = commitment_merge_pollution_traces(
        [
            {
                "kind": AttentionKind.INFERRED_COMMITMENT.value,
                "evidence_ids": list(MACHINE_MAIL_IDS),
            }
        ],
        expected_singleton_evidence_ids=MACHINE_MAIL_IDS,
        labels_by_evidence_id=BRAND_BY_ID,
    )
    report = storyline_ab_report(
        {"attention": {"critical_recall": 1.0}},
        {"attention": {"critical_recall": 1.0}},
        pollution_traces=traces,
        corpus_id="unrelated-machine-mail-mini",
        seed="test",
        n_messages=5,
    )
    assert "pollution_traces" in report
    assert report["pollution_traces"]
    assert report["pollution_traces"][0]["kind"] == "commitment_merge"
    assert report["pollution_traces"][0]["polluted"] is True
    assert set(report["pollution_traces"][0]["labels"]) >= {
        "PrizeVault",
        "BuildCloud",
    }


def test_pollution_detector_flags_collapsed_fingerprint() -> None:
    traces = commitment_merge_pollution_traces(
        [
            {
                "kind": "inferred_commitment",
                "evidence_ids": ["mail-prizevault", "mail-buildcloud"],
            }
        ],
        expected_singleton_evidence_ids=("mail-prizevault", "mail-buildcloud"),
        labels_by_evidence_id=BRAND_BY_ID,
    )
    result = compare_machine_mail_merge_pollution(traces)
    assert not result.passed
    assert any("collapsed" in v for v in result.violations)


def test_pollution_detector_passes_on_distinct_singletons() -> None:
    candidates = [
        {"kind": "inferred_commitment", "evidence_ids": [eid]}
        for eid in MACHINE_MAIL_IDS
    ]
    traces = commitment_merge_pollution_traces(
        candidates,
        expected_singleton_evidence_ids=MACHINE_MAIL_IDS,
        labels_by_evidence_id=BRAND_BY_ID,
    )
    result = compare_machine_mail_merge_pollution(traces)
    assert result.passed
    fps = {
        attention_candidate_fingerprint(kind="inferred_commitment", evidence_ids=[eid])
        for eid in MACHINE_MAIL_IDS
    }
    assert len(fps) == len(MACHINE_MAIL_IDS)


def test_unrelated_machine_mail_package_and_gt() -> None:
    pkg = load_scenario(SCENARIO)
    assert pkg.manifest.id == "unrelated-machine-mail-not-merged"
    mail = [e for e in pkg.events if e.type in {"email.receive", "email.send"}]
    assert len(mail) >= 4
    ids = {str(e.payload.get("id")) for e in mail}
    assert set(MACHINE_MAIL_IDS).issubset(ids)
    subjects = " ".join(str(e.payload.get("subject", "")) for e in mail)
    for brand in BRAND_BY_ID.values():
        assert brand in subjects
    assert all(EVALUATOR_KEYS.isdisjoint(e.payload.keys()) for e in pkg.events)

    truth = load_ground_truth(SCENARIO / "ground_truth")
    noise = truth.signals_for_class(ScenarioSignalClass.NOISE)
    assert len(noise) >= 4
    assert all(s.expected_attention is False for s in noise)
    assert truth.obligations == [] or len(truth.obligations) == 0


def test_unrelated_machine_mails_not_merged_into_one_commitment() -> None:
    """Live merge must keep one INFERRED_COMMITMENT fingerprint per brand mail."""
    pkg = load_scenario(SCENARIO)
    messages = []
    for event in pkg.events:
        if event.type not in {"email.receive", "email.send"}:
            continue
        payload = event.payload
        mid = str(payload["id"])
        brand = BRAND_BY_ID.get(mid, "Machine")
        messages.append(
            build_message(
                id=mid,
                provider_message_id=mid,
                thread_id=str(payload.get("thread_id") or f"thread-{mid}"),
                subject=str(payload.get("subject") or ""),
                snippet=str(payload.get("snippet") or ""),
                body_text=str(payload.get("body_text") or payload.get("snippet") or ""),
                from_person=build_person_ref(
                    display_name=brand,
                    email=str(payload.get("from") or f"noreply@{brand.lower()}.example"),
                    provider_id=f"person_{mid}",
                ),
            )
        )

    items = merge_sources_to_attention(messages=messages)
    machine_items = [
        item
        for item in items
        if any(eid in MACHINE_MAIL_IDS for eid in item.evidence_ids)
    ]
    assert machine_items
    assert all(item.kind == AttentionKind.INFERRED_COMMITMENT for item in machine_items)

    candidates = [
        {"kind": item.kind.value, "evidence_ids": list(item.evidence_ids)}
        for item in machine_items
    ]
    traces = commitment_merge_pollution_traces(
        candidates,
        expected_singleton_evidence_ids=MACHINE_MAIL_IDS,
        labels_by_evidence_id=BRAND_BY_ID,
    )
    result = compare_machine_mail_merge_pollution(traces)
    assert result.passed, result.violations

    fps = {
        attention_candidate_fingerprint(
            kind=item.kind.value, evidence_ids=item.evidence_ids
        )
        for item in machine_items
    }
    assert len(fps) == len(MACHINE_MAIL_IDS)
    assert all(len(item.evidence_ids) == 1 for item in machine_items)
