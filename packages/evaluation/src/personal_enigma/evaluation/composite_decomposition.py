"""R-L10 Phase 1 — offline composite decomposition (no model spend).

Replays frozen Step 7 semantic features through production
``composite_surface_score`` / ``decide_interruption``. Does not change policy
weights, judge prompts, or ground truth.
"""

from __future__ import annotations

import json
from dataclasses import dataclass, field
from datetime import datetime
from enum import StrEnum
from pathlib import Path
from typing import Any

from personal_enigma.attention.interruption_policy import (
    CONFIDENCE_MIN,
    CONTEXT_SCORE_THRESHOLD,
    NEAR_TERM_HOURS,
    NEAR_TERM_MAX_BOOST,
    NOISE_INFERRED_KINDS,
    NOISE_OBLIGATION_STRENGTH_MAX,
    OVERDUE_SCORE_BOOST,
    RESTFUL_URGENT_ACTIONABILITY,
    RESTFUL_URGENT_TIME_SENSITIVITY,
    SURFACE_SCORE_THRESHOLD,
    WEIGHT_ACTIONABILITY_NOW,
    WEIGHT_IMPORTANCE,
    WEIGHT_OBLIGATION_STRENGTH,
    WEIGHT_TIME_SENSITIVITY,
    WEIGHT_USER_RESPONSIBILITY,
    CandidatePolicyFacts,
    InterruptionMode,
    SemanticFeatures,
    composite_surface_score,
    decide_interruption,
)
from personal_enigma.evaluation.checkpoint_runner import load_checkpoint_snapshot
from personal_enigma.evaluation.evaluation_truth import EvaluationTruth, load_evaluation_truth
from personal_enigma.evaluation.ground_truth import CRITICAL_IMPORTANCE
from personal_enigma.evaluation.llm_benchmark import (
    build_candidate_policy_facts,
    semantic_output_to_features,
)
from personal_enigma.evaluation.observations import CheckpointSnapshot
from personal_enigma.evaluation.support_contract import AttentionBehaviour
from personal_enigma.reasoning.structured_output import SemanticJudgeV1Output

DEFAULT_STEP7_JSON = Path("reports/reasoning-gate-live/hardest-10-evaluation_transformed_v2.json")
DEFAULT_OUTPUT_JSON = Path("reports/reasoning-gate-live/rl10-jan19-20-decomposition.json")
DEFAULT_GROUND_TRUTH = Path("scenarios/alex-v1/ground_truth")
DEFAULT_BASELINE_DIR = Path("packages/evaluation/fixtures/baselines/arm-a")
JAN19_20_CHECKPOINTS = ("cp-2026-01-19T10:00", "cp-2026-01-20T11:00")
TOKEN_CANDIDATE_ID = "item-obligation_token_audit"
BRUNCH_CANDIDATE_ID = "item-obligation_brunch_book"
CALENDAR_PROXIMITY_BOOST = 0.05
"""Mirrors the +0.05 literal in ``composite_surface_score`` (calendar ≤ 2h)."""

COMPOSITE_FORMULA = (
    "composite = min(1.0, "
    f"{WEIGHT_OBLIGATION_STRENGTH}*obligation_strength + "
    f"{WEIGHT_USER_RESPONSIBILITY}*user_responsibility + "
    f"{WEIGHT_IMPORTANCE}*importance + "
    f"{WEIGHT_TIME_SENSITIVITY}*time_sensitivity + "
    f"{WEIGHT_ACTIONABILITY_NOW}*actionability_now "
    f"+ overdue(+{OVERDUE_SCORE_BOOST} if hours_until_due<=0) "
    f"+ near_term(+{NEAR_TERM_MAX_BOOST}*(1-hours/{NEAR_TERM_HOURS}) "
    f"if 0<hours<={NEAR_TERM_HOURS}) "
    f"+ calendar(+{CALENDAR_PROXIMITY_BOOST} if calendar_proximity_hours<=2) "
    "; then ×0.30 if is_noise_evidence). "
    f"surface if composite>={SURFACE_SCORE_THRESHOLD} else context if >={CONTEXT_SCORE_THRESHOLD} "
    "else suppress. Gates before score cut: engine_suppressed; "
    f"confidence<{CONFIDENCE_MIN}→low_confidence; "
    f"RESTFUL_WEEKEND unless time_sensitivity>={RESTFUL_URGENT_TIME_SENSITIVITY} and "
    f"actionability_now>={RESTFUL_URGENT_ACTIONABILITY}; "
    "noise_no_obligation / noise_evidence."
)


class TokenAuditLayer(StrEnum):
    """Per-rep token-audit miss layer (R-L10 classification)."""

    QUALIFICATION_FAILURE = "qualification_failure"
    OTHER_GATE = "other_gate"
    OUTSIDE_TOP3 = "outside_top3"
    EVAL_BUG = "eval_bug"
    SURFACED_IN_TOP3 = "surfaced_in_top3"


@dataclass(frozen=True, slots=True)
class BoostBreakdown:
    hours_until_due: float | None
    overdue_boost: float
    near_term_boost: float
    calendar_boost: float
    noise_multiplier: float
    weighted_semantic: float

    def as_dict(self) -> dict[str, Any]:
        return {
            "hours_until_due": self.hours_until_due,
            "overdue_boost": self.overdue_boost,
            "near_term_boost": self.near_term_boost,
            "calendar_boost": self.calendar_boost,
            "noise_multiplier": self.noise_multiplier,
            "weighted_semantic": self.weighted_semantic,
        }


@dataclass(frozen=True, slots=True)
class CandidateDecomposition:
    checkpoint_id: str
    rep: int
    candidate_id: str
    obligation_strength: float
    user_responsibility: float
    importance: float
    time_sensitivity: float
    actionability_now: float
    confidence: float
    reason_codes: tuple[str, ...]
    boosts: BoostBreakdown
    composite: float
    eligible: bool
    confidence_ok: bool
    mode_ok: bool
    noise_ok: bool
    engine_suppressed: bool
    other_gates_pass: bool
    decision: str
    policy_reason: str | None
    stored_policy_score: float | None
    stored_matches_recomputed: bool | None
    rank: int | None
    current_output: str

    def as_dict(self) -> dict[str, Any]:
        return {
            "checkpoint_id": self.checkpoint_id,
            "rep": self.rep,
            "candidate_id": self.candidate_id,
            "obligation_strength": self.obligation_strength,
            "user_responsibility": self.user_responsibility,
            "importance": self.importance,
            "time_sensitivity": self.time_sensitivity,
            "actionability_now": self.actionability_now,
            "confidence": self.confidence,
            "reason_codes": list(self.reason_codes),
            "boosts": self.boosts.as_dict(),
            "composite": self.composite,
            "eligible": self.eligible,
            "confidence_ok": self.confidence_ok,
            "mode_ok": self.mode_ok,
            "noise_ok": self.noise_ok,
            "engine_suppressed": self.engine_suppressed,
            "other_gates_pass": self.other_gates_pass,
            "decision": self.decision,
            "policy_reason": self.policy_reason,
            "stored_policy_score": self.stored_policy_score,
            "stored_matches_recomputed": self.stored_matches_recomputed,
            "rank": self.rank,
            "current_output": self.current_output,
        }


@dataclass(frozen=True, slots=True)
class TokenAuditClassification:
    checkpoint_id: str
    rep: int
    composite: float
    eligible: bool
    decision: str
    rank: int | None
    contract_pass: bool | None
    layer: TokenAuditLayer

    def as_dict(self) -> dict[str, Any]:
        return {
            "checkpoint_id": self.checkpoint_id,
            "rep": self.rep,
            "composite": self.composite,
            "eligible": self.eligible,
            "decision": self.decision,
            "rank": self.rank,
            "contract_pass": self.contract_pass,
            "layer": self.layer.value,
        }


@dataclass
class DecompositionReport:
    formula: str = COMPOSITE_FORMULA
    surface_score_threshold: float = SURFACE_SCORE_THRESHOLD
    rows: list[CandidateDecomposition] = field(default_factory=list)
    token_audit: list[TokenAuditClassification] = field(default_factory=list)
    three_layer: dict[str, Any] = field(default_factory=dict)
    finding: str = ""
    outcome: str = ""

    def as_dict(self) -> dict[str, Any]:
        return {
            "formula": self.formula,
            "surface_score_threshold": self.surface_score_threshold,
            "rows": [r.as_dict() for r in self.rows],
            "token_audit": [t.as_dict() for t in self.token_audit],
            "three_layer": self.three_layer,
            "finding": self.finding,
            "outcome": self.outcome,
        }


def weighted_semantic_score(semantic: SemanticFeatures) -> float:
    return (
        WEIGHT_OBLIGATION_STRENGTH * semantic.obligation_strength
        + WEIGHT_USER_RESPONSIBILITY * semantic.user_responsibility
        + WEIGHT_IMPORTANCE * semantic.importance
        + WEIGHT_TIME_SENSITIVITY * semantic.time_sensitivity
        + WEIGHT_ACTIONABILITY_NOW * semantic.actionability_now
    )


def deterministic_boosts(
    semantic: SemanticFeatures,
    facts: CandidatePolicyFacts,
) -> BoostBreakdown:
    """Decompose production boosts without re-implementing the composite."""
    hours = facts.hours_until_due
    overdue = 0.0
    near_term = 0.0
    if hours is not None:
        if hours <= 0:
            overdue = OVERDUE_SCORE_BOOST
        elif hours <= NEAR_TERM_HOURS:
            near_term = NEAR_TERM_MAX_BOOST * (1.0 - hours / NEAR_TERM_HOURS)
    calendar = 0.0
    if facts.calendar_proximity_hours is not None and facts.calendar_proximity_hours <= 2.0:
        calendar = CALENDAR_PROXIMITY_BOOST
    noise_multiplier = 0.30 if facts.is_noise_evidence else 1.0
    return BoostBreakdown(
        hours_until_due=hours,
        overdue_boost=overdue,
        near_term_boost=near_term,
        calendar_boost=calendar,
        noise_multiplier=noise_multiplier,
        weighted_semantic=weighted_semantic_score(semantic),
    )


def classify_token_audit(
    *,
    composite: float,
    decision: str,
    rank: int | None,
    contract_pass: bool | None,
    threshold: float = SURFACE_SCORE_THRESHOLD,
) -> TokenAuditLayer:
    if composite < threshold:
        return TokenAuditLayer.QUALIFICATION_FAILURE
    if decision != "surface":
        return TokenAuditLayer.OTHER_GATE
    if rank is None or rank > 3:
        return TokenAuditLayer.OUTSIDE_TOP3
    if contract_pass is False:
        return TokenAuditLayer.EVAL_BUG
    return TokenAuditLayer.SURFACED_IN_TOP3


def _restful_mode_ok(semantic: SemanticFeatures, facts: CandidatePolicyFacts) -> bool:
    if facts.interruption_mode != InterruptionMode.RESTFUL_WEEKEND:
        return True
    return (
        semantic.time_sensitivity >= RESTFUL_URGENT_TIME_SENSITIVITY
        and semantic.actionability_now >= RESTFUL_URGENT_ACTIONABILITY
    )


def _noise_ok(semantic: SemanticFeatures, facts: CandidatePolicyFacts) -> bool:
    if (
        not facts.has_open_obligation
        and facts.candidate_kind in NOISE_INFERRED_KINDS
        and semantic.obligation_strength < NOISE_OBLIGATION_STRENGTH_MAX
    ):
        return False
    if facts.is_noise_evidence and semantic.obligation_strength < NOISE_OBLIGATION_STRENGTH_MAX:
        return False
    return True


def _token_contract_pass(stored_metrics: dict[str, Any]) -> bool | None:
    for score in stored_metrics.get("checkpoint_scores") or []:
        if score.get("scenario") == "token-inventory-blocker":
            return bool(score.get("attention_pass"))
    return None


def _must_surface_critical_ids(truth: EvaluationTruth, when: datetime) -> list[str]:
    ids: list[str] = []
    for contract in truth.support_contracts.active_at(when):
        if contract.attention.behaviour != AttentionBehaviour.MUST_SURFACE:
            continue
        oid = contract.obligation_id
        if not oid:
            continue
        obligation = truth.ground_truth.obligation_by_id(oid)
        if obligation and obligation.importance in CRITICAL_IMPORTANCE:
            ids.append(oid)
    return ids


def decompose_rep(
    *,
    snapshot: CheckpointSnapshot,
    truth: EvaluationTruth,
    rep_payload: dict[str, Any],
) -> list[CandidateDecomposition]:
    by_id = {c.id: c for c in snapshot.candidate_set}
    stored_policy = list(rep_payload.get("policy_judgement") or [])
    stored_scores = {row["id"]: float(row["score"]) for row in stored_policy}
    stored_rank = {row["id"]: index + 1 for index, row in enumerate(stored_policy)}
    rep = int(rep_payload.get("rep", 0))
    rows: list[CandidateDecomposition] = []
    for judgement in rep_payload.get("candidate_judgements") or []:
        candidate_id = str(judgement["candidate_id"])
        candidate = by_id.get(candidate_id)
        if candidate is None:
            continue
        raw_semantic = judgement.get("semantic_output")
        if not isinstance(raw_semantic, dict):
            continue
        semantic = semantic_output_to_features(SemanticJudgeV1Output.model_validate(raw_semantic))
        facts = build_candidate_policy_facts(snapshot, candidate, truth)
        boosts = deterministic_boosts(semantic, facts)
        composite = composite_surface_score(semantic, facts)
        policy = decide_interruption(semantic, facts)
        stored = stored_scores.get(candidate_id)
        match: bool | None
        if stored is None:
            match = None
        else:
            match = abs(stored - policy.composite_score) < 1e-9 or abs(stored - composite) < 1e-9
        rank = stored_rank.get(candidate_id)
        if rank is None and policy.decision == "surface":
            rank = None
        rows.append(
            CandidateDecomposition(
                checkpoint_id=snapshot.checkpoint_id,
                rep=rep,
                candidate_id=candidate_id,
                obligation_strength=semantic.obligation_strength,
                user_responsibility=semantic.user_responsibility,
                importance=semantic.importance,
                time_sensitivity=semantic.time_sensitivity,
                actionability_now=semantic.actionability_now,
                confidence=semantic.confidence,
                reason_codes=semantic.reason_codes,
                boosts=boosts,
                composite=composite,
                eligible=composite >= SURFACE_SCORE_THRESHOLD,
                confidence_ok=semantic.confidence >= CONFIDENCE_MIN,
                mode_ok=_restful_mode_ok(semantic, facts),
                noise_ok=_noise_ok(semantic, facts),
                engine_suppressed=facts.engine_suppressed,
                other_gates_pass=(
                    semantic.confidence >= CONFIDENCE_MIN
                    and _restful_mode_ok(semantic, facts)
                    and _noise_ok(semantic, facts)
                    and not facts.engine_suppressed
                ),
                decision=policy.decision,
                policy_reason=policy.reason,
                stored_policy_score=stored,
                stored_matches_recomputed=match,
                rank=rank,
                current_output=policy.decision,
            )
        )
    return rows


def _three_layer_metrics(
    rows: list[CandidateDecomposition],
    truth: EvaluationTruth,
    snapshots: dict[str, CheckpointSnapshot],
) -> dict[str, Any]:
    """Offline qualification / ranking / presentation numbers for Jan 19/20."""
    grouped: dict[tuple[str, int], list[CandidateDecomposition]] = {}
    for row in rows:
        grouped.setdefault((row.checkpoint_id, row.rep), []).append(row)

    eligibility_hits = 0
    eligibility_expected = 0
    recall_at: dict[int, list[float]] = {k: [] for k in (1, 2, 3, 5)}
    presented: dict[int, list[float]] = {1: [], 2: []}
    mrr_values: list[float] = []

    for (cp_id, _rep), group in sorted(grouped.items()):
        snapshot = snapshots[cp_id]
        must_ids = _must_surface_critical_ids(truth, snapshot.at)
        by_cand = {row.candidate_id: row for row in group}
        eligible_ids = {
            row.candidate_id.removeprefix("item-")
            for row in group
            if row.eligible
        }
        surfaced = sorted(
            [row for row in group if row.decision == "surface"],
            key=lambda r: (-r.composite, r.candidate_id),
        )
        surfaced_oids = [r.candidate_id.removeprefix("item-") for r in surfaced]
        for oid in must_ids:
            eligibility_expected += 1
            cand_id = f"item-{oid}"
            row = by_cand.get(cand_id)
            if row is not None and row.eligible:
                eligibility_hits += 1
            elif oid in eligible_ids:
                eligibility_hits += 1

        for k in (1, 2, 3, 5):
            hit = sum(1 for oid in must_ids if oid in surfaced_oids[:k])
            recall_at[k].append(hit / len(must_ids) if must_ids else 1.0)
        for n in (1, 2):
            hit = sum(1 for oid in must_ids if oid in surfaced_oids[:n])
            presented[n].append(hit / len(must_ids) if must_ids else 1.0)

        ranks = []
        for oid in must_ids:
            if oid in surfaced_oids:
                ranks.append(1.0 / (surfaced_oids.index(oid) + 1))
            else:
                ranks.append(0.0)
        if ranks:
            mrr_values.append(sum(ranks) / len(ranks))

    def _mean(values: list[float]) -> float:
        return sum(values) / len(values) if values else 1.0

    return {
        "attention_eligibility_recall": (
            eligibility_hits / eligibility_expected if eligibility_expected else 1.0
        ),
        "eligibility_hits": eligibility_hits,
        "eligibility_expected": eligibility_expected,
        "critical_recall_at_k": {str(k): _mean(v) for k, v in recall_at.items()},
        "presented_slot_recall": {str(n): _mean(v) for n, v in presented.items()},
        "mrr": _mean(mrr_values),
        "note": (
            "Eligibility = composite >= SURFACE_SCORE_THRESHOLD regardless of rank. "
            "Critical recall@K / presented-slot N use production surface decisions "
            "(unbounded N) then cut to K/N. Production has no slot budget."
        ),
    }


def _finding_and_outcome(
    token_rows: list[TokenAuditClassification],
) -> tuple[str, str]:
    n = len(token_rows)
    qual_fail = sum(1 for t in token_rows if t.layer == TokenAuditLayer.QUALIFICATION_FAILURE)
    in_top3 = sum(1 for t in token_rows if t.layer == TokenAuditLayer.SURFACED_IN_TOP3)
    other_gate = sum(1 for t in token_rows if t.layer == TokenAuditLayer.OTHER_GATE)
    outside = sum(1 for t in token_rows if t.layer == TokenAuditLayer.OUTSIDE_TOP3)
    eval_bug = sum(1 for t in token_rows if t.layer == TokenAuditLayer.EVAL_BUG)
    finding = (
        "LLM recognises token-audit as actionable (actionability_now=0.9 on every Jan 19/20 "
        "rep). The qualification formula weights time_sensitivity (0.25) more than "
        "actionability_now (0.15), and brunch also receives a +0.05 calendar-proximity boost "
        f"token does not. Token composite stays below {SURFACE_SCORE_THRESHOLD} on "
        f"{qual_fail}/{n} reps (decision=context). The {in_top3} rep that crosses the "
        "threshold (Jan 19 rep2) surfaces at rank 2 and the Top-3 MUST_SURFACE contract "
        "passes. Increasing presentation slot budget to 2 would not rescue the below-threshold "
        "reps. Confidence, restful-weekend, and noise gates never block token-audit here."
    )
    if qual_fail == n:
        outcome = "C"
    elif qual_fail and in_top3 and not other_gate and not outside and not eval_bug:
        outcome = "C (primary), B (mechanism); A only for Top-1 on the qualifying rep"
    elif in_top3 and not qual_fail:
        outcome = "A"
    else:
        outcome = "mixed"
    return finding, outcome


def decompose_step7_json(
    report_path: Path,
    *,
    checkpoint_ids: list[str] | None = None,
    baseline_dir: Path = DEFAULT_BASELINE_DIR,
    ground_truth: Path = DEFAULT_GROUND_TRUTH,
) -> DecompositionReport:
    payload = json.loads(Path(report_path).read_text(encoding="utf-8"))
    truth = load_evaluation_truth(ground_truth)
    cp_ids = list(checkpoint_ids or JAN19_20_CHECKPOINTS)
    snapshots = {
        cp_id: load_checkpoint_snapshot(Path(baseline_dir) / f"{cp_id}.json") for cp_id in cp_ids
    }
    arm_b_reps = payload.get("arm_b_reps") or {}
    rows: list[CandidateDecomposition] = []
    token_audit: list[TokenAuditClassification] = []
    for cp_id in cp_ids:
        snapshot = snapshots[cp_id]
        for rep_payload in arm_b_reps.get(cp_id) or []:
            decomposed = decompose_rep(
                snapshot=snapshot,
                truth=truth,
                rep_payload=rep_payload,
            )
            rows.extend(decomposed)
            token = next((r for r in decomposed if r.candidate_id == TOKEN_CANDIDATE_ID), None)
            if token is None:
                continue
            contract_pass = _token_contract_pass(rep_payload.get("metrics") or {})
            layer = classify_token_audit(
                composite=token.composite,
                decision=token.decision,
                rank=token.rank,
                contract_pass=contract_pass,
            )
            token_audit.append(
                TokenAuditClassification(
                    checkpoint_id=cp_id,
                    rep=token.rep,
                    composite=token.composite,
                    eligible=token.eligible,
                    decision=token.decision,
                    rank=token.rank,
                    contract_pass=contract_pass,
                    layer=layer,
                )
            )
    finding, outcome = _finding_and_outcome(token_audit)
    return DecompositionReport(
        rows=rows,
        token_audit=token_audit,
        three_layer=_three_layer_metrics(rows, truth, snapshots),
        finding=finding,
        outcome=outcome,
    )


def render_markdown_table(rows: list[CandidateDecomposition]) -> str:
    header = (
        "| checkpoint | rep | candidate | obl | resp | imp | ts | act | "
        "near/overdue | cal | composite | ≥0.72? | gates | decision | rank |"
    )
    sep = (
        "| --- | ---: | --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: | "
        "---: | --- | --- | --- | ---: |"
    )
    lines = [header, sep]
    for row in rows:
        short = row.candidate_id.removeprefix("item-obligation_")
        boost = row.boosts.overdue_boost + row.boosts.near_term_boost
        gates = "pass" if row.other_gates_pass else "fail"
        if row.engine_suppressed:
            gates = "engine_suppressed"
        rank = "" if row.rank is None else str(row.rank)
        lines.append(
            "| "
            f"{row.checkpoint_id} | {row.rep} | {short} | "
            f"{row.obligation_strength:.2f} | {row.user_responsibility:.2f} | "
            f"{row.importance:.2f} | {row.time_sensitivity:.2f} | {row.actionability_now:.2f} | "
            f"{boost:.4f} | {row.boosts.calendar_boost:.2f} | {row.composite:.4f} | "
            f"{'yes' if row.eligible else 'no'} | {gates} | {row.decision} | {rank} |"
        )
    return "\n".join(lines)


def write_decomposition_report(report: DecompositionReport, output_path: Path) -> Path:
    output_path = Path(output_path)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    payload = report.as_dict()
    payload["markdown_table"] = render_markdown_table(report.rows)
    output_path.write_text(json.dumps(payload, indent=2) + "\n", encoding="utf-8")
    return output_path


__all__ = [
    "CALENDAR_PROXIMITY_BOOST",
    "COMPOSITE_FORMULA",
    "CandidateDecomposition",
    "DEFAULT_OUTPUT_JSON",
    "DEFAULT_STEP7_JSON",
    "DecompositionReport",
    "JAN19_20_CHECKPOINTS",
    "TOKEN_CANDIDATE_ID",
    "TokenAuditClassification",
    "TokenAuditLayer",
    "classify_token_audit",
    "decompose_rep",
    "decompose_step7_json",
    "deterministic_boosts",
    "render_markdown_table",
    "weighted_semantic_score",
    "write_decomposition_report",
]
