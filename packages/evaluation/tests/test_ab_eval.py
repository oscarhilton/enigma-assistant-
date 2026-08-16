"""A/B storyline-recall + D08c scientific gate hardening."""

from __future__ import annotations

from pathlib import Path

from personal_enigma.evaluation.ab_eval import (
    AB_METRIC_KEYS,
    attention_ranks_from_surface,
    build_comparison_artefact,
    build_pollution_hit,
    build_pollution_trace,
    compare_storyline_ab,
    compute_attention_displacement,
    evaluate_comparison_artefact,
    load_comparison_artefact,
    storyline_recall_under_noise,
    validate_comparison_schema,
    write_comparison_artefact,
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


def _full_metrics(
    *,
    critical_recall: float,
    precision: float = 1.0,
    total_alerts: int = 3,
    recall_at_k: float = 1.0,
    precision_at_k: float = 1.0,
    input_tokens: int = 100,
    total_usd: float = 0.01,
    processing_time: float = 1.0,
    remote_calls: int = 2,
) -> dict:
    return {
        "attention": {
            "critical_recall": critical_recall,
            "precision": precision,
            "duplicate_rate": 0.0,
            "stale_alert_rate": 0.0,
            "total_alerts": total_alerts,
        },
        "retrieval": {
            "recall_at_k": recall_at_k,
            "precision_at_k": precision_at_k,
        },
        "cost": {
            "input_tokens": input_tokens,
            "total_usd": total_usd,
            "remote_calls": remote_calls,
        },
        "runtime": {"processing_time": processing_time},
    }


def test_comparison_artefact_golden_schema_and_delta_pp(tmp_path: Path) -> None:
    artefact = build_comparison_artefact(
        baseline="alex-v1-spine",
        treatment="alex-v1-background",
        baseline_metrics=_full_metrics(critical_recall=0.97),
        treatment_metrics=_full_metrics(critical_recall=0.965),
        git_commit="abc123",
        corpus_revision="rev-fp-mini",
        sanitiser_version="1",
        seed="42",
        critical_ids=["obl_atlas"],
        baseline_ranks={"obl_atlas": 1},
        treatment_ranks={"obl_atlas": 1},
        surface_threshold=3,
    )
    assert artefact.passed
    recall = artefact.metrics["critical_recall"]
    assert abs(recall.baseline - 0.97) < 1e-9
    assert abs(recall.treatment - 0.965) < 1e-9
    assert recall.delta_pp is not None
    assert abs(recall.delta_pp - (-0.5)) < 1e-9
    assert set(artefact.metrics) == set(AB_METRIC_KEYS)

    path = write_comparison_artefact(tmp_path / "comparison.json", artefact)
    loaded = load_comparison_artefact(path)
    assert validate_comparison_schema(loaded) == []
    assert loaded["baseline"] == "alex-v1-spine"
    assert loaded["treatment"] == "alex-v1-background"
    assert loaded["git_commit"] == "abc123"
    assert loaded["corpus_revision"] == "rev-fp-mini"
    assert loaded["sanitiser_version"] == "1"
    assert loaded["seed"] == "42"
    assert abs(loaded["metrics"]["critical_recall"]["delta_pp"] - (-0.5)) < 1e-9
    gate = evaluate_comparison_artefact(loaded)
    assert gate.passed


def test_forced_rank_drop_recall_green_displacement_fails() -> None:
    """Recall stays 1.0 but #1 → #7 with surface=3 is a functional miss."""
    artefact = build_comparison_artefact(
        baseline="alex-v1-spine",
        treatment="alex-v1-background",
        baseline_metrics=_full_metrics(critical_recall=1.0),
        treatment_metrics=_full_metrics(critical_recall=1.0),
        git_commit="deadbeef",
        corpus_revision="rev",
        sanitiser_version="1",
        seed="seed",
        critical_ids=["obl_atlas"],
        baseline_ranks={"obl_atlas": 1},
        treatment_ranks={"obl_atlas": 7},
        surface_threshold=3,
    )
    assert abs(artefact.metrics["critical_recall"].delta_pp or 0.0) < 1e-9
    assert artefact.displacement.critical_displaced_below_surface == 1
    assert abs(artefact.displacement.mean_rank_delta - 6.0) < 1e-9
    assert not artefact.displacement.passed
    assert not artefact.passed
    assert any("displaced" in v for v in artefact.violations)

    gate = evaluate_comparison_artefact(artefact.as_dict())
    assert not gate.passed


def test_attention_displacement_mean_rank_delta() -> None:
    disp = compute_attention_displacement(
        ["a", "b"],
        {"a": 1, "b": 2},
        {"a": 2, "b": 3},
        surface_threshold=3,
    )
    assert abs(disp.mean_rank_delta - 1.0) < 1e-9
    assert disp.critical_displaced_below_surface == 0
    assert disp.passed

    ranks = attention_ranks_from_surface(["x", "y", "x"])
    assert ranks == {"x": 1, "y": 2}


def test_pollution_trace_schema_evaluator_only_signal_class() -> None:
    hit = build_pollution_hit(
        rank=1,
        source="mail",
        signal_class="background",
        similarity=0.91,
        entity_overlap=0.1,
        project_overlap=0.0,
        temporal_relevance=0.4,
        doc_id="bg-msg-1",
    )
    trace = build_pollution_trace(
        query_id="q-atlas",
        reason="changed_decision",
        hits=[hit],
    )
    payload = trace.as_dict()
    assert payload["hits"][0]["signal_class"] == "background"
    assert payload["hits"][0]["similarity"] == 0.91
    assert payload["hits"][0]["entity_overlap"] == 0.1
    assert payload["hits"][0]["project_overlap"] == 0.0
    assert payload["hits"][0]["temporal_relevance"] == 0.4

    artefact = build_comparison_artefact(
        baseline="alex-v1-spine",
        treatment="alex-v1-background",
        baseline_metrics=_full_metrics(critical_recall=1.0),
        treatment_metrics=_full_metrics(critical_recall=1.0),
        git_commit="c0ffee",
        corpus_revision="rev",
        sanitiser_version="1",
        seed="1",
        pollution_traces=[trace],
    )
    errors = validate_comparison_schema(artefact.as_dict())
    assert errors == []
    # signal_class is present on evaluator artefact only — never claimed as
    # an Enigma-facing field.
    assert artefact.pollution_traces[0].hits[0].signal_class == "background"


def test_comparison_artefact_fails_on_recall_regression(tmp_path: Path) -> None:
    artefact = build_comparison_artefact(
        baseline="alex-v1-spine",
        treatment="alex-v1-background",
        baseline_metrics=_full_metrics(critical_recall=1.0),
        treatment_metrics=_full_metrics(critical_recall=0.97),
        git_commit="x",
        corpus_revision="y",
        sanitiser_version="1",
        seed="z",
    )
    assert not artefact.passed
    path = write_comparison_artefact(tmp_path / "ab.json", artefact)
    loaded = load_comparison_artefact(path)
    assert not evaluate_comparison_artefact(loaded).passed


def test_assert_ab_gate_and_public_aliases(tmp_path: Path) -> None:
    from personal_enigma.evaluation.ab_eval import (
        ABComparisonArtefact,
        assert_ab_gate,
        build_ab_comparison,
        write_ab_comparison,
    )

    good = build_ab_comparison(
        baseline="alex-v1-spine",
        treatment="alex-v1-background",
        baseline_metrics=_full_metrics(critical_recall=0.97),
        treatment_metrics=_full_metrics(critical_recall=0.965),
        git_commit="g",
        corpus_revision="c",
        sanitiser_version="1",
        seed="s",
        critical_ids=["obl"],
        baseline_ranks={"obl": 1},
        treatment_ranks={"obl": 2},
        surface_threshold=3,
    )
    assert isinstance(good, ABComparisonArtefact)
    write_ab_comparison(tmp_path / "ok.json", good)
    assert_ab_gate(good)

    bad = build_ab_comparison(
        baseline="alex-v1-spine",
        treatment="alex-v1-background",
        baseline_metrics=_full_metrics(critical_recall=1.0),
        treatment_metrics=_full_metrics(critical_recall=1.0),
        git_commit="g",
        corpus_revision="c",
        sanitiser_version="1",
        seed="s",
        critical_ids=["obl"],
        baseline_ranks={"obl": 1},
        treatment_ranks={"obl": 9},
        surface_threshold=3,
    )
    try:
        assert_ab_gate(bad)
        raise AssertionError("expected assert_ab_gate to fail")
    except AssertionError as exc:
        assert "displaced" in str(exc)
