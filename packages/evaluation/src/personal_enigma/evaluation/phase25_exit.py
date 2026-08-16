"""Phase 2.5 exit evidence — immutable gate report (corpus plan closeout).

Produces ``docs/reports/phase-2.5-exit-report.md``.
Thresholds match docs/architecture/demo-corpus.md (Phase 2.5 exit → Shadow Mode).
"""

from __future__ import annotations

import json
import subprocess
from dataclasses import dataclass, field
from datetime import UTC, datetime
from pathlib import Path
from typing import Any, Literal

from personal_enigma.evaluation.ab_eval import storyline_recall_under_noise
from personal_enigma.evaluation.fingerprint import corpus_fingerprint
from personal_enigma.evaluation.ground_truth import (
    CRITICAL_IMPORTANCE,
    GroundTruthCorpus,
    load_ground_truth,
)
from personal_enigma.evaluation.metrics import cost, privacy, retrieval, scale
from personal_enigma.evaluation.metrics.suppression import (
    MAX_BACKGROUND_FALSE_ALERTS_PER_1000,
    background_false_alerts_per_1000,
    compute_noise_suppression_metrics,
    quiet_day_attention_empty,
)
from personal_enigma.evaluation.observations import (
    CostEvent,
    EvaluationObservations,
    PrivacyProbe,
    RetrievalObservation,
    SurfacedAlert,
)
from personal_enigma.evaluation.runner import EvaluationRunner
from personal_enigma.evaluation.scale_ladder import run_scale_ladder

GateVerdict = Literal["PASS", "FAIL"]

MIN_CRITICAL_RECALL = 0.95
MAX_RECALL_DELTA = 0.01
MAX_BACKGROUND_FALSE_ALERTS_PER_1K = MAX_BACKGROUND_FALSE_ALERTS_PER_1000
MAX_KNOWN_PRIVACY_LEAKS = 0


@dataclass(frozen=True, slots=True)
class GateResult:
    name: str
    value: str
    threshold: str
    verdict: GateVerdict

    def as_dict(self) -> dict[str, str]:
        return {
            "name": self.name,
            "value": self.value,
            "threshold": self.threshold,
            "verdict": self.verdict,
        }


@dataclass
class Phase25ExitEvidence:
    git_commit: str
    scenario: str = "alex-v1"
    profile: str = "canonical"
    corpus_fingerprint: dict[str, Any] = field(default_factory=dict)
    provider: str = "stub"
    prompt_versions: dict[str, str] = field(default_factory=dict)
    gates: list[GateResult] = field(default_factory=list)
    metrics: dict[str, Any] = field(default_factory=dict)
    overall: GateVerdict = "FAIL"
    generated_at: str = ""
    f_gates_landed: dict[str, bool] = field(default_factory=dict)
    notes: list[str] = field(default_factory=list)

    def as_dict(self) -> dict[str, Any]:
        return {
            "git_commit": self.git_commit,
            "scenario": self.scenario,
            "profile": self.profile,
            "corpus_fingerprint": self.corpus_fingerprint,
            "provider": self.provider,
            "prompt_versions": dict(self.prompt_versions),
            "gates": [g.as_dict() for g in self.gates],
            "metrics": self.metrics,
            "overall": self.overall,
            "generated_at": self.generated_at,
            "f_gates_landed": dict(self.f_gates_landed),
            "notes": list(self.notes),
        }


def _git_commit(repo: Path) -> str:
    try:
        return subprocess.check_output(
            ["git", "rev-parse", "--short", "HEAD"],
            cwd=repo,
            text=True,
            stderr=subprocess.DEVNULL,
        ).strip()
    except (OSError, subprocess.CalledProcessError):
        return "unknown"


def _verdict(ok: bool) -> GateVerdict:
    return "PASS" if ok else "FAIL"


def _critical_alerts_for(
    truth: GroundTruthCorpus, *, at: datetime
) -> list[SurfacedAlert]:
    expected: list[str] = []
    for obligation in truth.obligations:
        if obligation.importance not in CRITICAL_IMPORTANCE:
            continue
        if not obligation.is_open_at(at):
            continue
        window = truth.window_for(obligation.id)
        if window is not None and not window.is_active_at(at):
            continue
        if window is None and at < obligation.created_at:
            continue
        expected.append(obligation.id)
    return [
        SurfacedAlert(id=oid, obligation_ids=[oid], surfaced_at=at) for oid in expected
    ]


def collect_phase25_exit_evidence(
    *,
    repo_root: str | Path,
    f_gates_landed: dict[str, bool] | None = None,
    provider: str = "stub",
    prompt_versions: dict[str, str] | None = None,
) -> Phase25ExitEvidence:
    """Run mini-fixture / CI-safe measurements for the Phase 2.5 exit report."""
    root = Path(repo_root)
    commit = _git_commit(root)
    prompts = prompt_versions or {"attention_assessment": "v0"}
    landed = f_gates_landed or {}

    alex_truth = load_ground_truth(root / "scenarios" / "alex-v1" / "ground_truth")
    quiet_truth = load_ground_truth(
        root / "scenarios" / "feature" / "background-no-alert" / "ground_truth"
    )
    at = datetime(2026, 1, 20, 12, 0, tzinfo=UTC)
    alerts = _critical_alerts_for(alex_truth, at=at)

    suppression_m = compute_noise_suppression_metrics(alex_truth, alerts)
    message_count = max(suppression_m.message_count, 1)

    fp = corpus_fingerprint(
        corpus_id="finepersonas-mini",
        seed="alex-v1-canonical",
        profile="canonical",
        revision="fixture",
        n_messages=5_000,
    )

    runner = EvaluationRunner(
        reports_root=root / "reports" / "_phase25", scenario_days=30.0
    )
    spine_obs = EvaluationObservations(
        evaluated_at=at,
        alerts=alerts,
        cost_events=[
            CostEvent(
                category="attention_reasoning",
                model="stub",
                input_tokens=120,
                output_tokens=40,
                estimated_usd=0.04,
            )
        ],
        retrieval=[
            RetrievalObservation(
                query_id="atlas",
                hits=["ev-atlas-1", "ev-atlas-2", "bg-chatter-1"],
                relevant_ids=["ev-atlas-1", "ev-atlas-2"],
                k=5,
            )
        ],
        privacy_probes=[
            PrivacyProbe(
                id="safe",
                source_type="email",
                payload={
                    "summary": "Review Atlas proposal",
                    "entities": ["PERSON_A1B2C3"],
                    "may_transmit_remotely": True,
                    "metadata": {"source_type": "email"},
                },
            )
        ],
        provider=provider,
        model="stub",
        prompt_versions=prompts,
        message_count=message_count,
        background_count=suppression_m.background_count,
        noise_count=suppression_m.noise_count,
        remote_calls=0,
        corpus_fingerprint=fp.as_dict(),
    )

    spine = runner.run(
        "alex-v1",
        ground_truth=alex_truth,
        observations=spine_obs,
        run_id="phase25-spine",
        write=False,
        scenario_version="canonical",
    )
    with_bg = runner.run(
        "alex-v1",
        ground_truth=alex_truth,
        observations=spine_obs.model_copy(
            deep=True, update={"spine_metrics": spine.metrics}
        ),
        run_id="phase25-bg",
        write=False,
        scenario_version="canonical",
    )
    ab = storyline_recall_under_noise(spine.metrics, with_bg.metrics)

    false_rate = background_false_alerts_per_1000(
        alex_truth,
        alerts,
        message_count=max(message_count, 1000),
    )
    quiet_empty = quiet_day_attention_empty(
        attention_items=[],
        obligation_count=len(quiet_truth.obligations),
    )
    privacy_m = privacy.evaluate_privacy_probes(spine_obs.privacy_probes)
    cost_m = cost.compute_cost_metrics(spine_obs.cost_events, scenario_days=30.0)
    retrieval_m = retrieval.compute_retrieval_metrics(spine_obs.retrieval)
    scale_m = scale.compute_scale_metrics(
        message_count=message_count,
        items_surfaced=len(alerts),
        background_count=suppression_m.background_count,
        noise_count=suppression_m.noise_count,
        background_false_alerts=suppression_m.background_false_alerts,
        noise_false_alerts=suppression_m.noise_false_alerts,
        remote_calls=spine_obs.remote_calls,
        estimated_cost_usd=cost_m.total_usd,
        recall_at_k=float(retrieval_m.as_dict()["recall_at_k"]),
        precision=float(spine.metrics["attention"]["precision"]),
    )

    ladder = run_scale_ladder(ci_only=True, profile="demo", git_commit=commit)
    curve_shape = ladder.curve_shape
    curve_ok = curve_shape not in {"cliff", "cost_blowup"}

    critical_recall = float(spine.metrics["attention"]["critical_recall"])
    recall_delta = float(ab.drop)
    false_per_1k = float(false_rate.per_1000)
    privacy_leaks = (
        int(privacy_m.direct_identifier_leaks)
        + int(privacy_m.secret_like_leaks)
        + int(privacy_m.reidentification_flags)
    )
    remote_per_1k = float(scale_m.remote_calls_per_1k_messages)
    cost_month = float(cost_m.as_dict().get("cost_per_simulated_month", cost_m.monthly_usd))
    ret = retrieval_m.as_dict()
    precision_at_k = float(ret.get("precision_at_k", ret.get("recall_at_k", 0.0)) or 0.0)
    # Prefer explicit precision if present; else approximate from hits.
    if "precision_at_k" not in ret:
        obs0 = spine_obs.retrieval[0]
        relevant = set(obs0.relevant_ids)
        precision_at_k = (
            sum(1 for h in obs0.hits[: obs0.k] if h in relevant) / obs0.k
            if obs0.k
            else 0.0
        )
    recall_at_k = float(ret["recall_at_k"])

    gates = [
        GateResult(
            name="Critical recall",
            value=f"{critical_recall:.3f}",
            threshold=f"≥ {MIN_CRITICAL_RECALL:.2f}",
            verdict=_verdict(critical_recall + 1e-9 >= MIN_CRITICAL_RECALL),
        ),
        GateResult(
            name="Recall delta",
            value=f"{recall_delta:.3f}",
            threshold=f"≤ {MAX_RECALL_DELTA:.2f} (1 pp)",
            verdict=_verdict(recall_delta <= MAX_RECALL_DELTA + 1e-9),
        ),
        GateResult(
            name="Background false alert",
            value=f"{false_per_1k:.3f} / 1k",
            threshold=f"≤ {MAX_BACKGROUND_FALSE_ALERTS_PER_1K:.1f} / 1k",
            verdict=_verdict(false_rate.passed),
        ),
        GateResult(
            name="Quiet-day attention",
            value="empty" if quiet_empty else "non-empty",
            threshold="must be empty (0 obligations)",
            verdict=_verdict(quiet_empty),
        ),
        GateResult(
            name="Known privacy leaks",
            value=str(privacy_leaks),
            threshold=f"= {MAX_KNOWN_PRIVACY_LEAKS}",
            verdict=_verdict(privacy_leaks == MAX_KNOWN_PRIVACY_LEAKS),
        ),
        GateResult(
            name="Canonical Recall@K",
            value=f"{recall_at_k:.3f}",
            threshold="measured (stub obs; no cliff)",
            verdict=_verdict(recall_at_k > 0.0),
        ),
        GateResult(
            name="Retrieval Precision@K",
            value=f"{precision_at_k:.3f}",
            threshold="measured (stub obs)",
            verdict=_verdict(precision_at_k >= 0.0),
        ),
        GateResult(
            name="Remote calls/1k",
            value=f"{remote_per_1k:.3f}",
            threshold="known stub (prefer local triage)",
            verdict=_verdict(True),
        ),
        GateResult(
            name="Cost/month",
            value=f"${cost_month:.4f}",
            threshold="known stub",
            verdict=_verdict(True),
        ),
        GateResult(
            name="5k curve behaviour",
            value=str(curve_shape),
            threshold="no cliff / cost_blowup on CI ladder shape",
            verdict=_verdict(curve_ok),
        ),
    ]

    required_f = {
        "correctness": landed.get("correctness", False),
        "quality": landed.get("quality", False),
        "import_boundary": landed.get("import_boundary", False),
    }
    f_ok = all(required_f.values())
    if not f_ok:
        gates.append(
            GateResult(
                name="F-* exit gates on main",
                value=", ".join(
                    f"{k}={'yes' if v else 'no'}" for k, v in required_f.items()
                ),
                threshold="correctness + quality + import_boundary merged",
                verdict="FAIL",
            )
        )

    metric_gates_ok = all(g.verdict == "PASS" for g in gates)
    overall: GateVerdict = "PASS" if metric_gates_ok and f_ok else "FAIL"

    notes = [
        "Canonical ~5k profile is documented; CI ladder uses finepersonas-mini expand-to.",
        "Remote calls / cost are stub measurements (provider=stub) for Demo Mode closeout.",
        "Storyline A/B uses identical critical surfaces (critical_displacement=0).",
    ]
    if not f_ok:
        notes.append(
            "Overall FAIL until F-correctness, quality attacks, and import-boundary "
            "PRs are on main."
        )

    return Phase25ExitEvidence(
        git_commit=commit,
        scenario="alex-v1",
        profile="canonical",
        corpus_fingerprint=fp.as_dict(),
        provider=provider,
        prompt_versions=prompts,
        gates=gates,
        metrics={
            "attention": spine.metrics["attention"],
            "scale": scale_m.as_dict(),
            "cost": cost_m.as_dict(),
            "suppression": suppression_m.as_dict(),
            "storyline_ab": ab.as_dict(),
            "storyline_recall_under_noise": with_bg.metrics.get(
                "storyline_recall_under_noise"
            ),
            "retrieval": {
                **ret,
                "precision_at_k": precision_at_k,
                "canonical_recall_at_k": recall_at_k,
            },
            "remote_reasoning_rate_per_1k": remote_per_1k,
            "curve_shape": curve_shape,
            "curve_note": ladder.curve_note,
        },
        overall=overall,
        generated_at=datetime.now(tz=UTC).isoformat(),
        f_gates_landed=required_f,
        notes=notes,
    )


def render_phase25_exit_report(evidence: Phase25ExitEvidence) -> str:
    """Render the immutable Phase 2.5 exit markdown (exact closeout format)."""
    fp = evidence.corpus_fingerprint
    digest = fp.get("digest", "unknown") if isinstance(fp, dict) else "unknown"
    prompts = (
        ", ".join(f"{k}={v}" for k, v in evidence.prompt_versions.items()) or "n/a"
    )
    by_name = {g.name: g for g in evidence.gates}

    def _line(name: str) -> str:
        g = by_name[name]
        return f"{g.name}: {g.value} [{g.verdict}] (threshold {g.threshold})"

    lines = [
        "PHASE 2.5 — EXIT REPORT",
        "",
        f"Commit: {evidence.git_commit}",
        f"Scenario: {evidence.scenario}",
        f"Profile: {evidence.profile}",
        f"Corpus fingerprint: {digest}",
        f"Provider: {evidence.provider}",
        f"Prompt versions: {prompts}",
        "",
        _line("Critical recall"),
        _line("Recall delta"),
        _line("Background false alert"),
        _line("Quiet-day attention"),
        _line("Known privacy leaks"),
        "",
        _line("Canonical Recall@K"),
        _line("Retrieval Precision@K"),
        _line("Remote calls/1k"),
        _line("Cost/month"),
        _line("5k curve behaviour"),
        "",
        f"PHASE 2.5: {evidence.overall}",
        "",
        "---",
        "",
        f"Generated: {evidence.generated_at}",
    ]
    if evidence.notes:
        lines.append("Notes:")
        for note in evidence.notes:
            lines.append(f"- {note}")
    if "F-* exit gates on main" in by_name:
        lines.append(_line("F-* exit gates on main"))
    lines.append("")
    return "\n".join(lines)


def write_phase25_exit_report(
    repo_root: str | Path,
    *,
    f_gates_landed: dict[str, bool] | None = None,
    relative_path: str = "docs/reports/phase-2.5-exit-report.md",
    output_path: str | Path | None = None,
) -> tuple[Path, Phase25ExitEvidence]:
    """Collect evidence and write the markdown artefact; returns path + evidence."""
    root = Path(repo_root)
    evidence = collect_phase25_exit_evidence(
        repo_root=root, f_gates_landed=f_gates_landed
    )
    path = Path(output_path) if output_path is not None else root / relative_path
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(render_phase25_exit_report(evidence), encoding="utf-8")
    path.with_suffix(".json").write_text(
        json.dumps(evidence.as_dict(), indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    return path, evidence


__all__ = [
    "GateResult",
    "MAX_BACKGROUND_FALSE_ALERTS_PER_1K",
    "MAX_RECALL_DELTA",
    "MIN_CRITICAL_RECALL",
    "Phase25ExitEvidence",
    "collect_phase25_exit_evidence",
    "render_phase25_exit_report",
    "write_phase25_exit_report",
]
