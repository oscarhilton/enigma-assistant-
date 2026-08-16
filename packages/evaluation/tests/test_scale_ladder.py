"""D08e — scale metrics, ladder artefacts, and profile budgets."""

from __future__ import annotations

from pathlib import Path

from personal_enigma.evaluation import (
    CI_LADDER_POINTS,
    corpus_fingerprint,
    run_scale_ladder,
    storyline_ab_report,
    storyline_recall_under_noise,
    write_scale_curve,
)
from personal_enigma.evaluation.metrics.scale import compute_scale_metrics
from personal_enigma.simulation.corpus.background import (
    CANONICAL_BACKGROUND_MESSAGE_TARGET,
    CANONICAL_NOISE_MESSAGE_TARGET,
    STRESS_BACKGROUND_MESSAGE_TARGET,
    load_scenario_background,
)
from personal_enigma.simulation.scenario import load_scenario

REPO = Path(__file__).resolve().parents[3]
ALEX = REPO / "scenarios" / "alex-v1"
FEATURE = REPO / "scenarios" / "feature"


def test_documented_profile_targets() -> None:
    pkg = load_scenario(ALEX)
    cfg = load_scenario_background(pkg)
    assert cfg is not None
    demo = cfg.targets_for_profile("demo")
    assert demo.ci_background_messages == 8
    canonical = cfg.targets_for_profile("canonical")
    assert canonical.background_messages == CANONICAL_BACKGROUND_MESSAGE_TARGET
    assert canonical.noise_messages == CANONICAL_NOISE_MESSAGE_TARGET
    stress = cfg.targets_for_profile("stress")
    assert stress.background_messages == STRESS_BACKGROUND_MESSAGE_TARGET
    assert stress.note is not None
    feature = cfg.targets_for_profile("feature")
    assert feature.background_messages == 0
    assert cfg.profile == "demo"
    assert cfg.specs_for_profile("demo")[0].message_count == 8


def test_scale_metrics_compression_and_cost_per_1k() -> None:
    metrics = compute_scale_metrics(
        message_count=1000,
        items_surfaced=2,
        background_count=800,
        noise_count=200,
        background_false_alerts=1,
        noise_false_alerts=0,
        remote_calls=2,
        estimated_cost_usd=0.5,
    )
    assert metrics.attention_compression_ratio == 500.0
    assert abs(metrics.background_suppression_rate - 799 / 800) < 1e-9
    assert abs(metrics.background_false_alerts_per_1k - 1.0) < 1e-9
    assert abs(metrics.cost_per_1k_messages - 0.5) < 1e-9
    assert abs(metrics.remote_calls_per_1k_messages - 2.0) < 1e-9


def test_ci_scale_ladder_writes_json_csv(tmp_path: Path) -> None:
    report = run_scale_ladder(ci_only=True, profile="demo")
    assert len(report.points) == len(CI_LADDER_POINTS)
    assert [p.n_messages for p in report.points] == list(CI_LADDER_POINTS)
    assert report.curve_shape in {
        "flat",
        "linear",
        "linear_latency_flat_recall",
        "roughly_linear_latency",
        "mixed",
        "cliff",
        "cost_blowup",
        "unknown",
    }
    fp = (
        report.fingerprint.as_dict()
        if hasattr(report.fingerprint, "as_dict")
        else report.fingerprint
    )
    assert fp and fp.get("digest")
    out = write_scale_curve(report, tmp_path / "curves")
    assert (out / "scale_ladder.json").is_file() or (out / "scale_curve.json").is_file()
    csv_files = list(out.glob("*.csv"))
    assert csv_files
    text = csv_files[0].read_text(encoding="utf-8")
    assert "attention_compression_ratio" in text
    assert "cost_per_1k_messages" in text
    assert all(p.n_messages <= 1_000 for p in report.points)


def test_ci_ladder_rejects_stress_points() -> None:
    import pytest

    with pytest.raises(ValueError, match="CI ladder forbids"):
        run_scale_ladder(points=[100, 25_000], ci_only=True)


def test_corpus_fingerprint_stable() -> None:
    a = corpus_fingerprint(
        corpus_ids=["finepersonas-mini"],
        corpus_revision="fixture",
        sanitiser_version="v1",
        seed="s1",
        profile="canonical",
    )
    b = corpus_fingerprint(
        corpus_ids=["finepersonas-mini"],
        corpus_revision="fixture",
        sanitiser_version="v1",
        seed="s1",
        profile="canonical",
    )
    assert a.digest == b.digest
    assert a.as_dict()["digest"] == b.as_dict()["digest"]


def test_storyline_ab_rejects_critical_displacement() -> None:
    spine = {"attention": {"critical_recall": 1.0}}
    with_bg = {"attention": {"critical_recall": 1.0}}
    ok = storyline_recall_under_noise(spine, with_bg, critical_displacement=0)
    assert ok.passed
    bad = storyline_recall_under_noise(spine, with_bg, critical_displacement=1)
    assert not bad.passed


def test_storyline_ab_report_includes_fingerprint() -> None:
    spine = {"attention": {"critical_recall": 1.0}}
    treatment = {"attention": {"critical_recall": 0.995}}
    report = storyline_ab_report(
        spine,
        treatment,
        treatment_label="background+noise",
        profile="canonical",
        n_messages=5000,
    )
    assert report["ab"]["passed"]
    assert "noise" in report["treatment_label"] or report["treatment_label"] == "background+noise"
    fp = report["corpus_fingerprint"]
    digest = fp["digest"] if isinstance(fp, dict) else fp.digest
    assert digest
    assert report["delta_pp"] <= 1.0 + 1e-9


def test_feature_scenarios_load() -> None:
    from personal_enigma.simulation.corpus.noise import build_noise_stream

    for name in (
        "background-basic",
        "background-volume-vs-importance",
        "background-no-alert",
        "background-canonical-isolation",
    ):
        pkg = load_scenario(FEATURE / name)
        assert pkg.manifest.id == name
        mail = [e for e in pkg.events if e.type in {"email.receive", "email.send"}]
        if name == "background-no-alert" and not mail:
            # D08d: noise lives in noise.yaml, not scenario events.
            built = build_noise_stream(pkg)
            mail = list(built.events)
        assert mail
        for event in mail:
            assert "signal_class" not in event.payload
            assert "source_class" not in event.payload


def test_background_basic_has_critical_surrounded_by_background() -> None:
    pkg = load_scenario(FEATURE / "background-basic")
    subjects = [
        e.payload.get("subject", "")
        for e in pkg.events
        if e.type == "email.receive"
    ]
    assert any("Lease renewal" in str(s) for s in subjects)
    assert sum(1 for s in subjects if "Thread chatter" in str(s)) >= 50


def test_background_no_alert_has_no_obligations() -> None:
    from personal_enigma.evaluation import load_ground_truth
    from personal_enigma.simulation.corpus.noise import build_noise_stream

    truth = load_ground_truth(FEATURE / "background-no-alert" / "ground_truth")
    assert truth.obligations == []
    pkg = load_scenario(FEATURE / "background-no-alert")
    built = build_noise_stream(pkg)
    assert len(built.events) == 183
    assert all(s.expected_attention is False for s in built.signals)
