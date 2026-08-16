"""Phase 2.5 exit artefact + noise metric closeout tests."""

from __future__ import annotations

from pathlib import Path

from personal_enigma.evaluation.phase25_exit import (
    collect_phase25_exit_evidence,
    render_phase25_exit_report,
    write_phase25_exit_report,
)

REPO = Path(__file__).resolve().parents[3]


def test_phase25_exit_report_format_when_f_gates_pending(tmp_path: Path) -> None:
    path, evidence = write_phase25_exit_report(
        REPO,
        f_gates_landed={
            "correctness": False,
            "quality": False,
            "import_boundary": False,
        },
        output_path=tmp_path / "phase-2.5-exit-report.md",
    )
    text = path.read_text(encoding="utf-8")
    assert text.startswith("PHASE 2.5 — EXIT REPORT\n")
    for needle in (
        "Commit:",
        "Scenario: alex-v1",
        "Profile: canonical",
        "Corpus fingerprint:",
        "Critical recall:",
        "Recall delta:",
        "Background false alert:",
        "Quiet-day attention:",
        "Known privacy leaks:",
        "Canonical Recall@K:",
        "Retrieval Precision@K:",
        "Remote calls/1k:",
        "Cost/month:",
        "5k curve behaviour:",
        "PHASE 2.5: FAIL",
    ):
        assert needle in text, needle
    assert evidence.overall == "FAIL"


def test_phase25_exit_pass_when_f_gates_landed() -> None:
    evidence = collect_phase25_exit_evidence(
        repo_root=REPO,
        f_gates_landed={
            "correctness": True,
            "quality": True,
            "import_boundary": True,
        },
    )
    assert all(
        g.verdict == "PASS"
        for g in evidence.gates
        if g.name != "F-* exit gates on main"
    )
    assert evidence.overall == "PASS"
    text = render_phase25_exit_report(evidence)
    assert text.startswith("PHASE 2.5 — EXIT REPORT\n")
    assert "PHASE 2.5: PASS" in text
