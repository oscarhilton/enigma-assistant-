"""A/B storyline-recall helpers (D08c)."""

from __future__ import annotations

from personal_enigma.evaluation.ab_eval import (
    PollutionTrace,
    attention_candidate_fingerprint,
    commitment_merge_pollution_traces,
    compare_machine_mail_merge_pollution,
    compare_storyline_ab,
    storyline_ab_report,
    storyline_recall_under_noise,
)


def test_storyline_recall_ab_passes_within_one_pp() -> None:
    spine = {"attention": {"critical_recall": 0.97}}
    with_bg = {"attention": {"critical_recall": 0.965}}
    result = storyline_recall_under_noise(spine, with_bg)
    assert result.passed
    assert abs(result.drop - 0.005) < 1e-9
    assert compare_storyline_ab(spine, with_bg).passed


def test_storyline_recall_ab_fails_when_drop_exceeds_budget() -> None:
    spine = {"attention": {"critical_recall": 1.0}}
    with_bg = {"attention": {"critical_recall": 0.97}}
    result = storyline_recall_under_noise(spine, with_bg)
    assert not result.passed
    assert abs(result.drop - 0.03) < 1e-9
    regression = compare_storyline_ab(spine, with_bg)
    assert not regression.passed
    assert any("critical_recall" in v for v in regression.violations)


def test_storyline_recall_ab_fails_on_displacement_even_if_recall_flat() -> None:
    spine = {"attention": {"critical_recall": 1.0}}
    with_bg = {"attention": {"critical_recall": 1.0}}
    result = storyline_recall_under_noise(
        spine, with_bg, critical_displacement=2
    )
    assert not result.passed
    regression = compare_storyline_ab(
        spine, with_bg, critical_displacement=2
    )
    assert not regression.passed
    assert any("critical_displacement" in v for v in regression.violations)


def test_pollution_trace_schema_and_fingerprint_stability() -> None:
    fp_a = attention_candidate_fingerprint(
        kind="inferred_commitment",
        evidence_ids=["mail-b", "mail-a"],
    )
    fp_b = attention_candidate_fingerprint(
        kind="inferred_commitment",
        evidence_ids=["mail-a", "mail-b"],
    )
    assert fp_a == fp_b
    assert len(fp_a) == 16

    clean = commitment_merge_pollution_traces(
        [
            {"kind": "inferred_commitment", "evidence_ids": ["mail-prizevault"]},
            {"kind": "inferred_commitment", "evidence_ids": ["mail-buildcloud"]},
        ],
        expected_singleton_evidence_ids=["mail-prizevault", "mail-buildcloud"],
        labels_by_evidence_id={
            "mail-prizevault": "PrizeVault",
            "mail-buildcloud": "BuildCloud",
        },
    )
    assert compare_machine_mail_merge_pollution(clean).passed

    dirty = commitment_merge_pollution_traces(
        [
            {
                "kind": "inferred_commitment",
                "evidence_ids": ["mail-prizevault", "mail-buildcloud"],
            }
        ],
        expected_singleton_evidence_ids=["mail-prizevault", "mail-buildcloud"],
        labels_by_evidence_id={
            "mail-prizevault": "PrizeVault",
            "mail-buildcloud": "BuildCloud",
        },
    )
    assert not compare_machine_mail_merge_pollution(dirty).passed

    report = storyline_ab_report(
        {"attention": {"critical_recall": 1.0}},
        {"attention": {"critical_recall": 1.0}},
        pollution_traces=[
            PollutionTrace(
                decision_id="demo",
                kind="commitment_merge",
                polluted=False,
                fingerprint=fp_a,
                evidence_ids=("mail-prizevault",),
                labels=("PrizeVault",),
            )
        ],
    )
    assert report["pollution_traces"][0]["decision_id"] == "demo"
    assert report["pollution_traces"][0]["polluted"] is False
