"""Evaluation runner security overlay wiring."""

from __future__ import annotations

from personal_enigma.evaluation.runner import EvaluationRunner


def test_evaluation_runner_default_excludes_security_overlay() -> None:
    runner = EvaluationRunner()
    report = runner.run("alex-v1", write=False, scenario_version="0.2.1")
    assert report.summary["security_overlay"] is None
    assert report.summary["security_overlay_canary_count"] == 0


def test_evaluation_runner_security_overlay_opt_in() -> None:
    runner = EvaluationRunner()
    report = runner.run(
        "alex-v1",
        write=False,
        scenario_version="0.2.1",
        load_security_overlay=True,
    )
    assert report.summary["security_overlay"] == "alex-security-overlay-v1"
    assert report.summary["security_overlay_canary_count"] == 7
