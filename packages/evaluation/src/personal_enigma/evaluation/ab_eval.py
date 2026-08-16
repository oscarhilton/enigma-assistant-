"""A/B storyline recall under background / noise (D08c / D08e)."""

from __future__ import annotations

from collections.abc import Mapping, Sequence
from dataclasses import dataclass
from hashlib import sha256
from typing import Any

from personal_enigma.evaluation.fingerprint import corpus_fingerprint
from personal_enigma.evaluation.regression import DEFAULT_THRESHOLDS, RegressionResult


@dataclass(frozen=True, slots=True)
class PollutionTrace:
    """D08c retrieval / commitment-merge pollution artefact.

    Emit one trace per decision (canonical miss, changed ranking, or suspected
    cross-brand merge). ``polluted`` is True when unrelated evidence collapsed
    into a single attention-candidate fingerprint.
    """

    decision_id: str
    kind: str
    polluted: bool
    fingerprint: str
    evidence_ids: tuple[str, ...]
    labels: tuple[str, ...] = ()
    note: str = ""

    def as_dict(self) -> dict[str, Any]:
        return {
            "decision_id": self.decision_id,
            "kind": self.kind,
            "polluted": self.polluted,
            "fingerprint": self.fingerprint,
            "evidence_ids": list(self.evidence_ids),
            "labels": list(self.labels),
            "note": self.note,
        }


def attention_candidate_fingerprint(
    *,
    kind: str,
    evidence_ids: Sequence[str],
) -> str:
    """Stable fingerprint for one attention / commitment candidate."""
    payload = f"{kind}|{'|'.join(sorted(evidence_ids))}"
    return sha256(payload.encode("utf-8")).hexdigest()[:16]


def commitment_merge_pollution_traces(
    candidates: Sequence[Mapping[str, Any]],
    *,
    expected_singleton_evidence_ids: Sequence[str],
    labels_by_evidence_id: Mapping[str, str] | None = None,
    decision_id: str = "unrelated-machine-mail-merge",
) -> list[PollutionTrace]:
    """Trace whether unrelated evidence ids collapsed into one fingerprint.

    ``candidates`` entries need ``kind`` and ``evidence_ids``. A candidate that
    contains two or more of ``expected_singleton_evidence_ids`` is polluted.
    """
    labels = labels_by_evidence_id or {}
    expected = list(expected_singleton_evidence_ids)
    expected_set = set(expected)
    traces: list[PollutionTrace] = []

    for index, candidate in enumerate(candidates):
        kind = str(candidate.get("kind") or "inferred_commitment")
        evidence_ids = tuple(str(eid) for eid in candidate.get("evidence_ids") or ())
        fp = attention_candidate_fingerprint(kind=kind, evidence_ids=evidence_ids)
        hit = [eid for eid in evidence_ids if eid in expected_set]
        hit_labels = tuple(labels.get(eid, eid) for eid in hit)
        polluted = len(hit) >= 2
        note = (
            f"collapsed {len(hit)} unrelated machine mails into one candidate"
            if polluted
            else "candidate keeps disjoint machine-mail evidence"
        )
        traces.append(
            PollutionTrace(
                decision_id=f"{decision_id}:{index}",
                kind="commitment_merge",
                polluted=polluted,
                fingerprint=fp,
                evidence_ids=evidence_ids,
                labels=hit_labels,
                note=note,
            )
        )

    covered = {
        eid
        for candidate in candidates
        for eid in (candidate.get("evidence_ids") or ())
        if eid in expected_set
    }
    missing = [eid for eid in expected if eid not in covered]
    if missing:
        traces.append(
            PollutionTrace(
                decision_id=f"{decision_id}:missing",
                kind="commitment_merge",
                polluted=True,
                fingerprint="",
                evidence_ids=tuple(missing),
                labels=tuple(labels.get(eid, eid) for eid in missing),
                note="expected machine-mail evidence absent from all candidates",
            )
        )

    singleton_fps = [
        attention_candidate_fingerprint(
            kind=str(candidate.get("kind") or "inferred_commitment"),
            evidence_ids=list(candidate.get("evidence_ids") or ()),
        )
        for candidate in candidates
        if len(list(candidate.get("evidence_ids") or ())) == 1
        and next(iter(candidate.get("evidence_ids") or ())) in expected_set
    ]
    if (
        expected
        and not any(t.polluted for t in traces)
        and len(set(singleton_fps)) < len(expected)
    ):
        traces.append(
            PollutionTrace(
                decision_id=f"{decision_id}:fingerprint-collapse",
                kind="attention_fingerprint",
                polluted=True,
                fingerprint="",
                evidence_ids=tuple(expected),
                labels=tuple(labels.get(eid, eid) for eid in expected),
                note=(
                    f"expected {len(expected)} distinct fingerprints, "
                    f"observed {len(set(singleton_fps))}"
                ),
            )
        )

    return traces


def compare_machine_mail_merge_pollution(
    traces: Sequence[PollutionTrace],
) -> RegressionResult:
    """Regression gate: no commitment-merge / fingerprint pollution allowed."""
    violations = [
        f"{t.decision_id}: {t.note} (evidence={list(t.evidence_ids)})"
        for t in traces
        if t.polluted
    ]
    return RegressionResult(passed=not violations, violations=violations)


@dataclass(frozen=True, slots=True)
class StorylineRecallAB:
    """Critical-recall comparison: spine-only (A) vs spine+background/noise (B)."""

    spine_critical_recall: float
    with_background_critical_recall: float
    drop: float
    max_drop: float
    passed: bool
    critical_displacement: int = 0
    treatment: str = "background"
    treatment_label: str = "background"
    with_noise_critical_recall: float | None = None
    noise_drop: float | None = None

    def as_dict(self) -> dict[str, Any]:
        return {
            "spine_critical_recall": self.spine_critical_recall,
            "with_background_critical_recall": self.with_background_critical_recall,
            "with_noise_critical_recall": self.with_noise_critical_recall,
            "drop": self.drop,
            "noise_drop": self.noise_drop,
            "max_drop": self.max_drop,
            "passed": self.passed,
            "critical_displacement": self.critical_displacement,
            "treatment": self.treatment,
            "treatment_label": self.treatment_label,
        }


def storyline_recall_under_noise(
    spine_metrics: dict[str, Any],
    with_background_metrics: dict[str, Any],
    *,
    with_noise_metrics: dict[str, Any] | None = None,
    max_critical_recall_drop: float | None = None,
    critical_displacement: int = 0,
    treatment_label: str | None = None,
) -> StorylineRecallAB:
    """Compare critical recall with vs without background/noise (≤1 pp default).

    Optional ``with_noise_metrics`` adds a third arm (soft-dep D08d). Drop vs
    spine must stay ≤1 pp for both treatment arms; ``critical_displacement``
    must be 0.
    """
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

    noise_recall: float | None = None
    noise_drop: float | None = None
    if with_noise_metrics is not None:
        noise_att = with_noise_metrics.get("attention", with_noise_metrics)
        noise_recall = float(noise_att.get("critical_recall", 1.0))
        noise_drop = max(0.0, spine_recall - noise_recall)

    if treatment_label is not None:
        treatment = treatment_label
    elif with_noise_metrics is not None:
        treatment = "background+noise"
    else:
        treatment = "background"

    recall_ok = drop <= limit + 1e-9
    if noise_drop is not None:
        recall_ok = recall_ok and noise_drop <= limit + 1e-9
    displacement_ok = critical_displacement == 0
    return StorylineRecallAB(
        spine_critical_recall=spine_recall,
        with_background_critical_recall=bg_recall,
        drop=drop,
        max_drop=limit,
        passed=recall_ok and displacement_ok,
        critical_displacement=critical_displacement,
        treatment=treatment,
        treatment_label=treatment,
        with_noise_critical_recall=noise_recall,
        noise_drop=noise_drop,
    )


def compare_storyline_ab(
    spine_metrics: dict[str, Any],
    with_background_metrics: dict[str, Any],
    *,
    with_noise_metrics: dict[str, Any] | None = None,
    max_critical_recall_drop: float | None = None,
    critical_displacement: int = 0,
    treatment_label: str | None = None,
) -> RegressionResult:
    """Regression-shaped wrapper around :func:`storyline_recall_under_noise`."""
    result = storyline_recall_under_noise(
        spine_metrics,
        with_background_metrics,
        with_noise_metrics=with_noise_metrics,
        max_critical_recall_drop=max_critical_recall_drop,
        critical_displacement=critical_displacement,
        treatment_label=treatment_label,
    )
    violations: list[str] = []
    if result.drop > result.max_drop + 1e-9:
        violations.append(
            f"storyline critical_recall dropped "
            f"{result.spine_critical_recall:.3f} → "
            f"{result.with_background_critical_recall:.3f} "
            f"(drop {result.drop:.3f} > {result.max_drop:.3f})"
        )
    if result.noise_drop is not None and result.noise_drop > result.max_drop + 1e-9:
        violations.append(
            f"storyline critical_recall under noise dropped "
            f"{result.spine_critical_recall:.3f} → "
            f"{result.with_noise_critical_recall:.3f} "
            f"(drop {result.noise_drop:.3f} > {result.max_drop:.3f})"
        )
    if result.critical_displacement != 0:
        violations.append(
            f"critical_displacement={result.critical_displacement} "
            f"(must be 0 under {result.treatment})"
        )
    return RegressionResult(passed=result.passed, violations=violations)


def storyline_ab_report(
    spine_metrics: dict[str, Any],
    treatment_metrics: dict[str, Any],
    *,
    with_noise_metrics: dict[str, Any] | None = None,
    treatment_label: str | None = None,
    critical_displacement: int = 0,
    max_critical_recall_drop: float | None = None,
    corpus_id: str = "finepersonas-mini",
    corpus_revision: str = "unknown",
    sanitiser_version: str | None = None,
    seed: str = "unknown",
    profile: str = "demo",
    n_messages: int = 0,
    git_commit: str | None = None,
    pollution_traces: Sequence[PollutionTrace] | None = None,
) -> dict[str, Any]:
    """Immutable-ish A/B comparison artefact with corpus fingerprint (D08e)."""
    ab = storyline_recall_under_noise(
        spine_metrics,
        treatment_metrics,
        with_noise_metrics=with_noise_metrics,
        max_critical_recall_drop=max_critical_recall_drop,
        critical_displacement=critical_displacement,
        treatment_label=treatment_label,
    )
    fp = corpus_fingerprint(
        corpus_id=corpus_id,
        seed=seed,
        profile=profile,
        revision=corpus_revision,
        sanitiser_version=sanitiser_version,
        n_messages=n_messages,
    )
    traces = [t.as_dict() for t in (pollution_traces or ())]
    return {
        "baseline": spine_metrics,
        "treatment": treatment_metrics,
        "treatment_label": ab.treatment,
        "delta_pp": ab.drop * 100.0,
        "ab": ab.as_dict(),
        "git_commit": git_commit,
        "corpus_fingerprint": fp.as_dict(),
        "pollution_traces": traces,
    }


__all__ = [
    "PollutionTrace",
    "StorylineRecallAB",
    "attention_candidate_fingerprint",
    "commitment_merge_pollution_traces",
    "compare_machine_mail_merge_pollution",
    "compare_storyline_ab",
    "storyline_ab_report",
    "storyline_recall_under_noise",
]
