"""Scale ladder runner — graphable curve artefacts (D08e).

PR CI exercises small N only (via ``CI_LADDER_POINTS`` / ``CI_SCALE_LADDER_POINTS``).
Canonical (~5k) and stress (10k / 25k) are documented for nightly/manual runs —
never download FinePersonas 115k in PR CI.
"""

from __future__ import annotations

import csv
import json
import time
from collections.abc import Callable, Sequence
from dataclasses import dataclass, field
from hashlib import sha256
from pathlib import Path
from typing import Any, Literal

from personal_enigma.evaluation.ab_eval import StorylineRecallAB, storyline_recall_under_noise
from personal_enigma.evaluation.fingerprint import CorpusFingerprint, corpus_fingerprint
from personal_enigma.evaluation.metrics.scale import ScaleMetrics, compute_scale_metrics

try:
    from personal_enigma.simulation.corpus.background import (
        CI_SCALE_LADDER_POINTS as _BG_CI,
    )
    from personal_enigma.simulation.corpus.background import (
        FULL_SCALE_LADDER_POINTS as _BG_FULL,
    )
except ImportError:  # pragma: no cover
    _BG_CI = (100, 500)
    _BG_FULL = (100, 500, 1_000, 2_500, 5_000, 10_000, 25_000)

# Full ladder from the D08e ticket (manual / nightly).
SCALE_LADDER: tuple[int, ...] = tuple(_BG_FULL)
# PR-safe points — expand mini fixtures; never require HF download.
CI_LADDER_POINTS: tuple[int, ...] = tuple(_BG_CI)

_ROLE_BY_N: dict[int, str] = {
    100: "smoke",
    500: "early_shape",
    1_000: "ci_mid",
    2_500: "pre_canonical",
    5_000: "canonical",
    10_000: "stretch",
    25_000: "stress",
}

CurveShape = Literal[
    "flat",
    "linear",
    "linear_latency_flat_recall",
    "roughly_linear_latency",
    "cliff",
    "cost_blowup",
    "mixed",
    "unknown",
]


@dataclass(frozen=True, slots=True)
class ScalePoint:
    """One N on the scale ladder with timing + quality stubs."""

    n_messages: int
    role: str
    index_size: int
    ingest_time_ms: float
    retrieval_latency_ms: float
    recall_at_k: float
    precision: float
    remote_calls: int
    estimated_cost_usd: float
    scale: ScaleMetrics
    storyline_ab: StorylineRecallAB | None = None
    critical_displacement: int = 0
    profile: str = "demo"
    notes: str = ""
    fingerprint_digest: str = ""

    def as_dict(self) -> dict[str, Any]:
        return {
            "n_messages": self.n_messages,
            "role": self.role,
            "index_size": self.index_size,
            "ingest_time_ms": self.ingest_time_ms,
            "retrieval_latency_ms": self.retrieval_latency_ms,
            "recall_at_k": self.recall_at_k,
            "precision": self.precision,
            "remote_calls": self.remote_calls,
            "estimated_cost_usd": self.estimated_cost_usd,
            "scale": self.scale.as_dict(),
            "storyline_ab": (
                self.storyline_ab.as_dict() if self.storyline_ab is not None else None
            ),
            "critical_displacement": self.critical_displacement,
            "profile": self.profile,
            "notes": self.notes,
            "fingerprint_digest": self.fingerprint_digest,
        }


@dataclass
class ScaleCurveReport:
    """Graphable ladder artefacts + curve-shape note."""

    points: list[ScalePoint] = field(default_factory=list)
    fingerprint: CorpusFingerprint | dict[str, Any] | None = None
    curve_shape: CurveShape = "unknown"
    curve_note: str = ""
    notes: str = ""
    git_commit: str | None = None
    profile: str = "demo"
    ci_only: bool = True

    def as_dict(self) -> dict[str, Any]:
        fp: dict[str, Any]
        if isinstance(self.fingerprint, CorpusFingerprint):
            fp = self.fingerprint.as_dict()
        elif isinstance(self.fingerprint, dict):
            fp = dict(self.fingerprint)
        else:
            fp = {}
        return {
            "points": [p.as_dict() for p in self.points],
            "fingerprint": fp,
            "curve_shape": self.curve_shape,
            "curve_note": self.curve_note,
            "notes": self.notes,
            "git_commit": self.git_commit,
            "profile": self.profile,
            "ci_only": self.ci_only,
            "ladder": list(SCALE_LADDER),
            "ci_points": list(CI_LADDER_POINTS),
        }


def classify_curve_shape(points: Sequence[ScalePoint]) -> tuple[CurveShape, str]:
    """Heuristic shape label from ladder points (understood, not 'must be fast')."""
    if len(points) < 2:
        return "unknown", "Insufficient points to classify curve shape."

    latencies = [p.retrieval_latency_ms for p in points]
    recalls = [p.recall_at_k for p in points]
    costs = [p.scale.cost_per_1k_messages for p in points]
    ns = [p.n_messages for p in points]

    recall_drop = max(recalls) - min(recalls)
    cost_ratio = (max(costs) / min(costs)) if min(costs) > 1e-12 else 1.0
    rates = [(latencies[i] / ns[i]) if ns[i] else 0.0 for i in range(len(points))]
    rate_spread = (max(rates) - min(rates)) / max(rates) if max(rates) > 1e-12 else 0.0

    if recall_drop >= 0.05:
        return (
            "cliff",
            f"Recall@K drop of {recall_drop:.3f} across ladder — file a finding; "
            "do not hide a cliff behind a green checkbox.",
        )
    if cost_ratio >= 3.0:
        return (
            "cost_blowup",
            f"Cost/1k rose {cost_ratio:.1f}× — premium routing or context bloat "
            "likely; next optimisation belongs at the inflection N.",
        )
    if rate_spread <= 0.35 and recall_drop <= 0.01:
        return (
            "linear_latency_flat_recall",
            "Roughly linear latency with flat Recall@K — predictable under volume; "
            "Phase 2.5 can still pass even if 5k is slower than ideal. "
            "CI smoke uses expand-to on finepersonas-mini (never FinePersonas 115k).",
        )
    if recall_drop <= 0.01 and cost_ratio < 1.5:
        return (
            "flat",
            "Quality and cost/1k stay flat; latency shape is secondary.",
        )
    return (
        "roughly_linear_latency",
        "Mixed latency/cost behaviour without a clear recall cliff — "
        "treat as understood, not as an SLO failure.",
    )


def stub_measure_point(
    n_messages: int,
    *,
    profile: str = "demo",
    spine_critical_recall: float = 1.0,
    with_noise_critical_recall: float | None = None,
    items_surfaced: int = 2,
    background_false_alerts: int = 0,
    noise_false_alerts: int = 0,
    remote_calls: int | None = None,
    cost_usd_per_message: float = 0.00002,
    critical_displacement: int = 0,
    fingerprint_digest: str = "",
) -> ScalePoint:
    """Deterministic stub measurement for CI (no embedding index required)."""
    t0 = time.perf_counter()
    digest = sha256(f"scale-stub:{profile}:{n_messages}".encode()).hexdigest()
    _ = digest * max(1, n_messages // 50)
    elapsed_ms = (time.perf_counter() - t0) * 1000.0
    ingest_ms = 0.05 * n_messages + elapsed_ms
    retrieval_ms = 0.02 * n_messages + 0.5
    calls = remote_calls if remote_calls is not None else max(1, items_surfaced)
    cost = cost_usd_per_message * n_messages
    noise_recall = (
        spine_critical_recall
        if with_noise_critical_recall is None
        else with_noise_critical_recall
    )
    scale = compute_scale_metrics(
        message_count=n_messages,
        items_surfaced=items_surfaced,
        background_count=n_messages,
        background_false_alerts=background_false_alerts,
        noise_count=0,
        noise_false_alerts=noise_false_alerts,
        remote_calls=calls,
        estimated_cost_usd=cost,
        index_size_bytes=n_messages * 64,
        ingest_time_ms=ingest_ms,
        retrieval_latency_ms=retrieval_ms,
        recall_at_k=noise_recall,
        precision=1.0,
    )
    ab = storyline_recall_under_noise(
        {"attention": {"critical_recall": spine_critical_recall}},
        {"attention": {"critical_recall": noise_recall}},
        critical_displacement=critical_displacement,
    )
    return ScalePoint(
        n_messages=n_messages,
        role=_ROLE_BY_N.get(n_messages, f"n_{n_messages}"),
        index_size=n_messages,
        ingest_time_ms=ingest_ms,
        retrieval_latency_ms=retrieval_ms,
        recall_at_k=noise_recall,
        precision=1.0,
        remote_calls=calls,
        estimated_cost_usd=cost,
        scale=scale,
        storyline_ab=ab,
        critical_displacement=critical_displacement,
        profile=profile,
        notes="stub_measure_point — CI offline; expand mini corpus, no HF download",
        fingerprint_digest=fingerprint_digest,
    )


def run_scale_ladder(
    points: Sequence[int] | None = None,
    *,
    profile: str = "demo",
    ci_only: bool = True,
    measure: Callable[[int], ScalePoint] | None = None,
    corpus_id: str = "finepersonas-mini",
    corpus_revision: str = "mini-fixture",
    sanitiser_version: str | None = None,
    seed: str = "alex-v1-email-background-v1",
    git_commit: str | None = None,
) -> ScaleCurveReport:
    """Run ladder points and classify curve shape."""
    ns = list(
        points if points is not None else (CI_LADDER_POINTS if ci_only else SCALE_LADDER)
    )
    if ci_only:
        forbidden = {n for n in ns if n > 1_000}
        if forbidden:
            raise ValueError(
                f"CI ladder forbids N>{1000}: {sorted(forbidden)}. "
                "Use ci_only=False for nightly/manual canonical/stress runs."
            )

    fp = corpus_fingerprint(
        corpus_id=corpus_id,
        seed=seed,
        profile=profile,
        revision=corpus_revision,
        sanitiser_version=sanitiser_version,
        n_messages=ns[-1] if ns else 0,
    )
    measure_fn = measure or (
        lambda n: stub_measure_point(
            n, profile=profile, fingerprint_digest=fp.digest
        )
    )
    measured = [measure_fn(n) for n in ns]
    shape, note = classify_curve_shape(measured)
    notes = (
        f"{note} PR CI never downloads FinePersonas 115k; "
        "uses finepersonas-mini + expand-to only."
    )
    return ScaleCurveReport(
        points=measured,
        fingerprint=fp,
        curve_shape=shape,
        curve_note=note,
        notes=notes,
        git_commit=git_commit,
        profile=profile,
        ci_only=ci_only,
    )


def write_scale_curve(
    report: ScaleCurveReport,
    output_dir: Path | str,
    *,
    run_id: str = "scale-ladder",
) -> Path:
    """Persist JSON + CSV under ``output_dir/<run_id>/`` for graphing."""
    paths = write_scale_ladder_artefacts(report, Path(output_dir) / run_id)
    return paths["json"].parent


def write_scale_ladder_artefacts(
    report: ScaleCurveReport,
    output_dir: Path | str,
) -> dict[str, Path]:
    """Write ``scale_ladder.json`` + ``scale_ladder.csv``; return path map."""
    root = Path(output_dir)
    root.mkdir(parents=True, exist_ok=True)
    json_path = root / "scale_ladder.json"
    csv_path = root / "scale_ladder.csv"
    note_path = root / "curve_note.md"

    payload = report.as_dict()
    json_path.write_text(
        json.dumps(payload, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )

    fieldnames = [
        "n_messages",
        "role",
        "index_size",
        "ingest_time_ms",
        "retrieval_latency_ms",
        "recall_at_k",
        "precision",
        "remote_calls",
        "estimated_cost_usd",
        "attention_compression_ratio",
        "background_suppression_rate",
        "background_false_alerts_per_1k",
        "cost_per_1k_messages",
        "remote_calls_per_1k",
        "critical_displacement",
        "storyline_recall_drop",
        "fingerprint_digest",
        "profile",
    ]
    with csv_path.open("w", encoding="utf-8", newline="") as fh:
        writer = csv.DictWriter(fh, fieldnames=fieldnames)
        writer.writeheader()
        for point in report.points:
            ab = point.storyline_ab
            writer.writerow(
                {
                    "n_messages": point.n_messages,
                    "role": point.role,
                    "index_size": point.index_size,
                    "ingest_time_ms": f"{point.ingest_time_ms:.4f}",
                    "retrieval_latency_ms": f"{point.retrieval_latency_ms:.4f}",
                    "recall_at_k": f"{point.recall_at_k:.6f}",
                    "precision": f"{point.precision:.6f}",
                    "remote_calls": point.remote_calls,
                    "estimated_cost_usd": f"{point.estimated_cost_usd:.8f}",
                    "attention_compression_ratio": (
                        f"{point.scale.attention_compression_ratio:.6f}"
                    ),
                    "background_suppression_rate": (
                        f"{point.scale.background_suppression_rate:.6f}"
                    ),
                    "background_false_alerts_per_1k": (
                        f"{point.scale.background_false_alerts_per_1k:.6f}"
                    ),
                    "cost_per_1k_messages": (
                        f"{point.scale.cost_per_1k_messages:.8f}"
                    ),
                    "remote_calls_per_1k": (
                        f"{point.scale.remote_calls_per_1k_messages:.6f}"
                    ),
                    "critical_displacement": point.critical_displacement,
                    "storyline_recall_drop": (
                        f"{ab.drop:.6f}" if ab is not None else ""
                    ),
                    "fingerprint_digest": point.fingerprint_digest
                    or (
                        report.fingerprint.digest
                        if isinstance(report.fingerprint, CorpusFingerprint)
                        else ""
                    ),
                    "profile": point.profile,
                }
            )

    fp_digest = ""
    if isinstance(report.fingerprint, CorpusFingerprint):
        fp_digest = report.fingerprint.digest
    elif isinstance(report.fingerprint, dict):
        fp_digest = str(report.fingerprint.get("digest", ""))
    note_path.write_text(
        f"# Scale curve — `{report.profile}`\n\n"
        f"- Shape: **{report.curve_shape}**\n"
        f"- CI-only: `{report.ci_only}`\n"
        f"- Fingerprint: `{fp_digest}`\n\n"
        f"{report.notes or report.curve_note}\n",
        encoding="utf-8",
    )
    return {"json": json_path, "csv": csv_path, "note": note_path}


__all__ = [
    "CI_LADDER_POINTS",
    "SCALE_LADDER",
    "CurveShape",
    "ScaleCurveReport",
    "ScalePoint",
    "classify_curve_shape",
    "run_scale_ladder",
    "stub_measure_point",
    "write_scale_curve",
    "write_scale_ladder_artefacts",
]
