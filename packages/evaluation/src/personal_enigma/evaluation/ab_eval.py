"""A/B storyline recall under background noise (D08c scientific gate).

Emits an immutable comparison artefact (baseline / treatment / deltas),
attention-displacement diagnostics, and evaluator-only pollution traces.
"""

from __future__ import annotations

import json
import os
import tempfile
from collections.abc import Mapping, Sequence
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Literal, get_args

from personal_enigma.evaluation.regression import DEFAULT_THRESHOLDS, RegressionResult

SignalClassLabel = Literal["canonical", "background"]

# Full A/B metric table required in the comparison artefact.
AB_METRIC_KEYS: tuple[str, ...] = (
    "critical_recall",
    "precision",
    "duplicate_rate",
    "stale_alert_rate",
    "canonical_recall_at_k",
    "retrieval_precision_at_k",
    "attention_count",
    "remote_calls",
    "input_tokens",
    "estimated_cost",
    "processing_time",
)

# Rate metrics report ``delta_pp`` (percentage points); others use ``delta``.
_RATE_METRICS = frozenset(
    {
        "critical_recall",
        "precision",
        "duplicate_rate",
        "stale_alert_rate",
        "canonical_recall_at_k",
        "retrieval_precision_at_k",
    }
)

_METRIC_PATHS: dict[str, tuple[str, ...]] = {
    "critical_recall": ("attention", "critical_recall"),
    "precision": ("attention", "precision"),
    "duplicate_rate": ("attention", "duplicate_rate"),
    "stale_alert_rate": ("attention", "stale_alert_rate"),
    "canonical_recall_at_k": ("retrieval", "recall_at_k"),
    "retrieval_precision_at_k": ("retrieval", "precision_at_k"),
    "attention_count": ("attention", "total_alerts"),
    "remote_calls": ("cost", "remote_calls"),
    "input_tokens": ("cost", "input_tokens"),
    "estimated_cost": ("cost", "total_usd"),
    "processing_time": ("runtime", "processing_time"),
}


@dataclass(frozen=True, slots=True)
class StorylineRecallAB:
    """Critical-recall comparison: spine-only (A) vs spine+background (B)."""

    spine_critical_recall: float
    with_background_critical_recall: float
    drop: float
    max_drop: float
    passed: bool

    def as_dict(self) -> dict[str, Any]:
        return {
            "spine_critical_recall": self.spine_critical_recall,
            "with_background_critical_recall": self.with_background_critical_recall,
            "drop": self.drop,
            "max_drop": self.max_drop,
            "passed": self.passed,
        }


@dataclass(frozen=True, slots=True)
class MetricComparison:
    """Single metric with baseline / treatment / delta (or delta_pp)."""

    baseline: float
    treatment: float
    delta: float | None = None
    delta_pp: float | None = None

    def as_dict(self) -> dict[str, float]:
        out: dict[str, float] = {
            "baseline": self.baseline,
            "treatment": self.treatment,
        }
        if self.delta_pp is not None:
            out["delta_pp"] = self.delta_pp
        if self.delta is not None:
            out["delta"] = self.delta
        return out


@dataclass(frozen=True, slots=True)
class CanonicalRankEntry:
    """Per-critical-item attention rank in spine vs background."""

    obligation_id: str
    baseline_rank: int | None
    treatment_rank: int | None
    rank_delta: int | None
    displaced_below_surface: bool

    def as_dict(self) -> dict[str, Any]:
        return {
            "obligation_id": self.obligation_id,
            "baseline_rank": self.baseline_rank,
            "treatment_rank": self.treatment_rank,
            "rank_delta": self.rank_delta,
            "displaced_below_surface": self.displaced_below_surface,
        }


@dataclass(frozen=True, slots=True)
class AttentionDisplacement:
    """Catches 'recall still green' failures when critical items fall off-surface."""

    ranks: tuple[CanonicalRankEntry, ...]
    mean_rank_delta: float
    critical_displaced_below_surface: int
    surface_threshold: int
    passed: bool

    def as_dict(self) -> dict[str, Any]:
        return {
            "ranks": [r.as_dict() for r in self.ranks],
            "mean_rank_delta": self.mean_rank_delta,
            "critical_displaced_below_surface": self.critical_displaced_below_surface,
            "surface_threshold": self.surface_threshold,
            "passed": self.passed,
        }


@dataclass(frozen=True, slots=True)
class PollutionHit:
    """One retrieved document with match diagnostics (evaluator-side)."""

    rank: int
    source: str
    similarity: float | None = None
    entity_overlap: float | None = None
    project_overlap: float | None = None
    temporal_relevance: float | None = None
    signal_class: SignalClassLabel = "background"
    doc_id: str = ""

    def as_dict(self) -> dict[str, Any]:
        return {
            "rank": self.rank,
            "source": self.source,
            "similarity": self.similarity,
            "entity_overlap": self.entity_overlap,
            "project_overlap": self.project_overlap,
            "temporal_relevance": self.temporal_relevance,
            # Evaluator-only — never place on Enigma-facing payloads.
            "signal_class": self.signal_class,
            "doc_id": self.doc_id,
        }


@dataclass(frozen=True, slots=True)
class PollutionTrace:
    """Retrieval pollution for a canonical miss or changed decision."""

    query_id: str
    reason: Literal["canonical_miss", "changed_decision"]
    hits: tuple[PollutionHit, ...]

    def as_dict(self) -> dict[str, Any]:
        return {
            "query_id": self.query_id,
            "reason": self.reason,
            "hits": [h.as_dict() for h in self.hits],
        }


@dataclass(frozen=True, slots=True)
class ComparisonArtefact:
    """Immutable A/B comparison JSON for the D08c scientific gate."""

    baseline: str
    treatment: str
    git_commit: str
    corpus_revision: str
    sanitiser_version: str
    seed: str
    metrics: dict[str, MetricComparison]
    displacement: AttentionDisplacement
    pollution_traces: tuple[PollutionTrace, ...] = ()
    passed: bool = True
    violations: tuple[str, ...] = ()
    schema_version: str = "d08c-gate-v1"

    def as_dict(self) -> dict[str, Any]:
        return {
            "schema_version": self.schema_version,
            "baseline": self.baseline,
            "treatment": self.treatment,
            "git_commit": self.git_commit,
            "corpus_revision": self.corpus_revision,
            "sanitiser_version": self.sanitiser_version,
            "seed": self.seed,
            "metrics": {k: v.as_dict() for k, v in self.metrics.items()},
            "displacement": self.displacement.as_dict(),
            "pollution_traces": [t.as_dict() for t in self.pollution_traces],
            "passed": self.passed,
            "violations": list(self.violations),
        }


def storyline_recall_under_noise(
    spine_metrics: dict[str, Any],
    with_background_metrics: dict[str, Any],
    *,
    max_critical_recall_drop: float | None = None,
) -> StorylineRecallAB:
    """Compare critical recall with vs without background (≤1 pp default)."""
    limit = (
        DEFAULT_THRESHOLDS["critical_recall_drop"]
        if max_critical_recall_drop is None
        else max_critical_recall_drop
    )
    spine_att = spine_metrics.get("attention", spine_metrics)
    bg_att = with_background_metrics.get("attention", with_background_metrics)
    spine_recall = float(spine_att.get("critical_recall", 1.0))
    bg_recall = float(bg_att.get("critical_recall", 1.0))
    drop = max(0.0, spine_recall - bg_recall)
    return StorylineRecallAB(
        spine_critical_recall=spine_recall,
        with_background_critical_recall=bg_recall,
        drop=drop,
        max_drop=limit,
        passed=drop <= limit + 1e-9,
    )


def compare_storyline_ab(
    spine_metrics: dict[str, Any],
    with_background_metrics: dict[str, Any],
    *,
    max_critical_recall_drop: float | None = None,
) -> RegressionResult:
    """Regression-shaped wrapper around :func:`storyline_recall_under_noise`."""
    result = storyline_recall_under_noise(
        spine_metrics,
        with_background_metrics,
        max_critical_recall_drop=max_critical_recall_drop,
    )
    violations: list[str] = []
    if not result.passed:
        violations.append(
            "storyline critical_recall dropped "
            f"{result.spine_critical_recall:.3f} → "
            f"{result.with_background_critical_recall:.3f} "
            f"(drop {result.drop:.3f} > {result.max_drop:.3f})"
        )
    return RegressionResult(passed=result.passed, violations=violations)


def _dig(metrics: Mapping[str, Any], path: tuple[str, ...], default: float = 0.0) -> float:
    cur: Any = metrics
    for key in path:
        if not isinstance(cur, Mapping) or key not in cur:
            # Flat fallback: last path segment at top level.
            if len(path) > 1 and path[-1] in metrics:
                return float(metrics[path[-1]])  # type: ignore[arg-type]
            return default
        cur = cur[key]
    return float(cur)


def extract_ab_metric_values(metrics: Mapping[str, Any]) -> dict[str, float]:
    """Pull the A/B table values from a runner metrics dict (with flat fallbacks)."""
    values: dict[str, float] = {}
    for key in AB_METRIC_KEYS:
        path = _METRIC_PATHS[key]
        default = 1.0 if key in _RATE_METRICS else 0.0
        if key in metrics and not isinstance(metrics.get(key), Mapping):
            values[key] = float(metrics[key])  # type: ignore[arg-type]
        else:
            values[key] = _dig(metrics, path, default=default)
    return values


def compare_metric(
    baseline: float,
    treatment: float,
    *,
    as_pp: bool,
) -> MetricComparison:
    """Build baseline/treatment/delta(_pp) for one metric."""
    if as_pp:
        return MetricComparison(
            baseline=baseline,
            treatment=treatment,
            delta_pp=(treatment - baseline) * 100.0,
        )
    return MetricComparison(
        baseline=baseline,
        treatment=treatment,
        delta=treatment - baseline,
    )


def attention_ranks_from_surface(ordered_ids: Sequence[str]) -> dict[str, int]:
    """1-indexed ranks from a surfaced attention list (first occurrence wins)."""
    ranks: dict[str, int] = {}
    for index, oid in enumerate(ordered_ids, start=1):
        if oid not in ranks:
            ranks[oid] = index
    return ranks


def compute_attention_displacement(
    critical_ids: Sequence[str],
    baseline_ranks: Mapping[str, int],
    treatment_ranks: Mapping[str, int],
    *,
    surface_threshold: int = 3,
) -> AttentionDisplacement:
    """Compare critical-item ranks; flag functional misses below the UI surface."""
    if surface_threshold < 1:
        raise ValueError("surface_threshold must be >= 1")

    entries: list[CanonicalRankEntry] = []
    paired_deltas: list[int] = []
    displaced = 0

    for oid in critical_ids:
        base = baseline_ranks.get(oid)
        treat = treatment_ranks.get(oid)
        rank_delta: int | None
        if base is not None and treat is not None:
            rank_delta = treat - base
            paired_deltas.append(rank_delta)
        else:
            rank_delta = None

        below = base is not None and base <= surface_threshold and (
            treat is None or treat > surface_threshold
        )
        if below:
            displaced += 1

        entries.append(
            CanonicalRankEntry(
                obligation_id=oid,
                baseline_rank=base,
                treatment_rank=treat,
                rank_delta=rank_delta,
                displaced_below_surface=below,
            )
        )

    mean_delta = (
        sum(paired_deltas) / len(paired_deltas) if paired_deltas else 0.0
    )
    return AttentionDisplacement(
        ranks=tuple(entries),
        mean_rank_delta=float(mean_delta),
        critical_displaced_below_surface=displaced,
        surface_threshold=surface_threshold,
        passed=displaced == 0,
    )


def build_pollution_hit(
    *,
    rank: int,
    source: str,
    signal_class: SignalClassLabel,
    similarity: float | None = None,
    entity_overlap: float | None = None,
    project_overlap: float | None = None,
    temporal_relevance: float | None = None,
    doc_id: str = "",
) -> PollutionHit:
    """Construct a pollution hit; ``signal_class`` is evaluator-only."""
    if signal_class not in get_args(SignalClassLabel):
        raise ValueError(f"invalid signal_class: {signal_class!r}")
    return PollutionHit(
        rank=rank,
        source=source,
        similarity=similarity,
        entity_overlap=entity_overlap,
        project_overlap=project_overlap,
        temporal_relevance=temporal_relevance,
        signal_class=signal_class,
        doc_id=doc_id,
    )


def build_pollution_trace(
    *,
    query_id: str,
    reason: Literal["canonical_miss", "changed_decision"],
    hits: Sequence[PollutionHit],
) -> PollutionTrace:
    return PollutionTrace(query_id=query_id, reason=reason, hits=tuple(hits))


def _gate_violations(
    metrics: Mapping[str, MetricComparison],
    displacement: AttentionDisplacement,
    *,
    max_critical_recall_drop_pp: float,
) -> list[str]:
    violations: list[str] = []
    recall = metrics.get("critical_recall")
    if recall is not None and recall.delta_pp is not None:
        # delta_pp is treatment - baseline; regression is a negative delta.
        if recall.delta_pp < -max_critical_recall_drop_pp - 1e-9:
            violations.append(
                "critical_recall delta_pp "
                f"{recall.delta_pp:.3f} exceeds "
                f"-{max_critical_recall_drop_pp:.3f} pp budget"
            )
    if not displacement.passed:
        violations.append(
            "critical_displaced_below_surface "
            f"{displacement.critical_displaced_below_surface} != 0 "
            f"(surface_threshold={displacement.surface_threshold})"
        )
    return violations


def build_comparison_artefact(
    *,
    baseline: str,
    treatment: str,
    baseline_metrics: Mapping[str, Any],
    treatment_metrics: Mapping[str, Any],
    git_commit: str,
    corpus_revision: str,
    sanitiser_version: str,
    seed: str,
    critical_ids: Sequence[str] = (),
    baseline_ranks: Mapping[str, int] | None = None,
    treatment_ranks: Mapping[str, int] | None = None,
    surface_threshold: int = 3,
    pollution_traces: Sequence[PollutionTrace] = (),
    max_critical_recall_drop: float | None = None,
) -> ComparisonArtefact:
    """Assemble the immutable A/B gate artefact and compute pass/fail."""
    drop_frac = (
        DEFAULT_THRESHOLDS["critical_recall_drop"]
        if max_critical_recall_drop is None
        else max_critical_recall_drop
    )
    max_drop_pp = drop_frac * 100.0

    base_vals = extract_ab_metric_values(baseline_metrics)
    treat_vals = extract_ab_metric_values(treatment_metrics)
    metric_comparisons: dict[str, MetricComparison] = {}
    for key in AB_METRIC_KEYS:
        metric_comparisons[key] = compare_metric(
            base_vals[key],
            treat_vals[key],
            as_pp=key in _RATE_METRICS,
        )

    displacement = compute_attention_displacement(
        critical_ids,
        baseline_ranks or {},
        treatment_ranks or {},
        surface_threshold=surface_threshold,
    )
    violations = _gate_violations(
        metric_comparisons,
        displacement,
        max_critical_recall_drop_pp=max_drop_pp,
    )
    return ComparisonArtefact(
        baseline=baseline,
        treatment=treatment,
        git_commit=git_commit,
        corpus_revision=corpus_revision,
        sanitiser_version=sanitiser_version,
        seed=str(seed),
        metrics=metric_comparisons,
        displacement=displacement,
        pollution_traces=tuple(pollution_traces),
        passed=not violations,
        violations=tuple(violations),
    )


def write_comparison_artefact(
    path: str | Path,
    artefact: ComparisonArtefact | Mapping[str, Any],
) -> Path:
    """Atomically write the comparison JSON (immutable artefact for CI gates)."""
    target = Path(path)
    target.parent.mkdir(parents=True, exist_ok=True)
    payload = artefact.as_dict() if isinstance(artefact, ComparisonArtefact) else dict(artefact)
    text = json.dumps(payload, indent=2, sort_keys=True) + "\n"
    fd, tmp_name = tempfile.mkstemp(
        dir=str(target.parent),
        prefix=f".{target.name}.",
        suffix=".tmp",
    )
    try:
        with os.fdopen(fd, "w", encoding="utf-8") as handle:
            handle.write(text)
            handle.flush()
            os.fsync(handle.fileno())
        os.replace(tmp_name, target)
    except Exception:
        try:
            os.unlink(tmp_name)
        except OSError:
            pass
        raise
    return target


def load_comparison_artefact(path: str | Path) -> dict[str, Any]:
    """Load a previously written comparison artefact."""
    return json.loads(Path(path).read_text(encoding="utf-8"))


def evaluate_comparison_artefact(
    artefact: ComparisonArtefact | Mapping[str, Any],
    *,
    max_critical_recall_drop: float | None = None,
) -> RegressionResult:
    """Re-check gate pass/fail from an artefact (dict or dataclass)."""
    if isinstance(artefact, ComparisonArtefact):
        data = artefact.as_dict()
    else:
        data = dict(artefact)

    drop_frac = (
        DEFAULT_THRESHOLDS["critical_recall_drop"]
        if max_critical_recall_drop is None
        else max_critical_recall_drop
    )
    max_drop_pp = drop_frac * 100.0
    violations: list[str] = []

    metrics_raw = data.get("metrics", {})
    recall = metrics_raw.get("critical_recall", {})
    if "delta_pp" in recall:
        delta_pp = float(recall["delta_pp"])
        if delta_pp < -max_drop_pp - 1e-9:
            violations.append(
                "critical_recall delta_pp "
                f"{delta_pp:.3f} exceeds -{max_drop_pp:.3f} pp budget"
            )

    displacement = data.get("displacement", {})
    displaced = int(displacement.get("critical_displaced_below_surface", 0))
    if displaced != 0:
        threshold = displacement.get("surface_threshold", "?")
        violations.append(
            "critical_displaced_below_surface "
            f"{displaced} != 0 (surface_threshold={threshold})"
        )

    # Honour explicit violations recorded when the artefact was built.
    for item in data.get("violations", []):
        if item not in violations:
            violations.append(str(item))

    return RegressionResult(passed=not violations, violations=violations)


def validate_comparison_schema(data: Mapping[str, Any]) -> list[str]:
    """Return schema errors for a comparison artefact dict (empty = ok)."""
    errors: list[str] = []
    for key in (
        "baseline",
        "treatment",
        "git_commit",
        "corpus_revision",
        "sanitiser_version",
        "seed",
        "metrics",
        "displacement",
    ):
        if key not in data:
            errors.append(f"missing required field: {key}")

    metrics = data.get("metrics")
    if isinstance(metrics, Mapping):
        for key in AB_METRIC_KEYS:
            if key not in metrics:
                errors.append(f"metrics missing: {key}")
                continue
            entry = metrics[key]
            if not isinstance(entry, Mapping):
                errors.append(f"metrics.{key} must be an object")
                continue
            for side in ("baseline", "treatment"):
                if side not in entry:
                    errors.append(f"metrics.{key} missing {side}")
            if key in _RATE_METRICS and "delta_pp" not in entry:
                errors.append(f"metrics.{key} missing delta_pp")
            if key not in _RATE_METRICS and "delta" not in entry:
                errors.append(f"metrics.{key} missing delta")
    else:
        errors.append("metrics must be an object")

    displacement = data.get("displacement")
    if isinstance(displacement, Mapping):
        for key in (
            "mean_rank_delta",
            "critical_displaced_below_surface",
            "surface_threshold",
            "ranks",
        ):
            if key not in displacement:
                errors.append(f"displacement missing: {key}")
    elif "displacement" in data:
        errors.append("displacement must be an object")

    for index, trace in enumerate(data.get("pollution_traces", [])):
        if not isinstance(trace, Mapping):
            errors.append(f"pollution_traces[{index}] must be an object")
            continue
        for hit_i, hit in enumerate(trace.get("hits", [])):
            if not isinstance(hit, Mapping):
                errors.append(f"pollution_traces[{index}].hits[{hit_i}] must be an object")
                continue
            for field_name in (
                "rank",
                "source",
                "similarity",
                "entity_overlap",
                "project_overlap",
                "temporal_relevance",
                "signal_class",
            ):
                if field_name not in hit:
                    errors.append(
                        f"pollution_traces[{index}].hits[{hit_i}] missing {field_name}"
                    )
            sc = hit.get("signal_class")
            if sc is not None and sc not in get_args(SignalClassLabel):
                errors.append(
                    f"pollution_traces[{index}].hits[{hit_i}] "
                    f"invalid signal_class: {sc!r}"
                )

    return errors


def assert_ab_gate(
    artefact: ComparisonArtefact | Mapping[str, Any],
    *,
    max_critical_recall_drop: float | None = None,
) -> RegressionResult:
    """CI helper: raise ``AssertionError`` when the scientific gate fails."""
    result = evaluate_comparison_artefact(
        artefact,
        max_critical_recall_drop=max_critical_recall_drop,
    )
    if not result.passed:
        raise AssertionError("; ".join(result.violations) or "A/B gate failed")
    return result


# Public aliases matching ticket / demo-corpus wording.
ABComparisonArtefact = ComparisonArtefact
build_ab_comparison = build_comparison_artefact
write_ab_comparison = write_comparison_artefact


__all__ = [
    "AB_METRIC_KEYS",
    "ABComparisonArtefact",
    "AttentionDisplacement",
    "CanonicalRankEntry",
    "ComparisonArtefact",
    "MetricComparison",
    "PollutionHit",
    "PollutionTrace",
    "SignalClassLabel",
    "StorylineRecallAB",
    "assert_ab_gate",
    "attention_ranks_from_surface",
    "build_ab_comparison",
    "build_comparison_artefact",
    "build_pollution_hit",
    "build_pollution_trace",
    "compare_metric",
    "compare_storyline_ab",
    "compute_attention_displacement",
    "evaluate_comparison_artefact",
    "extract_ab_metric_values",
    "load_comparison_artefact",
    "storyline_recall_under_noise",
    "validate_comparison_schema",
    "write_ab_comparison",
    "write_comparison_artefact",
]
