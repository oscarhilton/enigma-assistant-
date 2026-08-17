# Reasoning Value Gate — Live Report

- Generated: 2026-08-17 (R-L10 Phase 1 **closed** — Outcome C)
- Git freeze: `50198fc` / tag `r-l09-step6-prompt-wiring`
- Scenario: `alex-v1` v0.2.1
- Arm B path: semantic judge + deterministic interruption policy (B2)

## Scientific conclusion (narrow production scope)

**PROVEN:** B2 + `evaluation_transformed_v1` → **`no_win`** vs frozen Arm A (main gate, ~$0.26).

**R-L09.5 (Step 7):** **B — partial signal.** Production `TransformedContext` (including `relations[]`) **was** seen by the model. v2 critical recall stayed **0.85** vs historical v1 **0.85**; Jan 19/20 token-audit *features* moved (`actionability_now` → 0.9) but policy still missed the item on most reps. **Not eligible for main.**

Keep deterministic interruption policy in production. Do not tune thresholds from this run.

---

## R-L09 live chronology

### R-L09.1 — Offline transform fix

Causal semantics missing from evaluation stub → `relations[]` graph, BLOCKED_BY resolution, production parity (`evaluation_transformed_v2`).

### R-L09.2 — Offline gate passed

Jan 19/20 checkpoints: dependency, resolution, causality checklist green. Privacy gate clean.

### R-L09.3 — Live hardest-10 (2026-08-17, ~$0.058)

**Decision: NO MOVEMENT** under current wiring.

| Column | Critical recall | MUST_SUPPRESS | Notes |
| --- | --- | --- | --- |
| v1 historical (prior ablation) | **0.85** | ≥0.95 | Valid anchor |
| v1 (this run) | 1.00 | 0.95 | **Invalid** — Arm A fallback on prompt-build failure |
| **v2** | **0.85** | **1.00** | Valid — no movement vs historical v1 |
| full_synthetic | 1.00 | 0.95 | Valid recall but **byte-identical prompt to v2** |

**Jan 19/20 v2 semantics (token audit):** `time_sensitivity` ~0.3, `actionability_now` ~0.5–0.7, `LOW_URGENCY` / `CONTEXT_ONLY` — no shift toward blocker-resolved / high-urgency.

**Root cause:** `TransformedContext.relations[]` passed `assert_remote_safe()` but was **not serialised into the semantic judge prompt**. Fireworks receives only the prompt; `build_semantic_judge_prompt()` used `snapshot_to_context_dict()` — a parallel path with no relations. v2 and full_synthetic prompts were byte-identical.

**Classification:** Integration/wiring negative — falsifies the assumption that the live judge path consumes `TransformedContext`. **Does not** falsify the semantic-preservation hypothesis until Step 6 wires context into the prompt and Step 7 re-runs hardest-10.

Artifacts: `reports/reasoning-gate-live/hardest-10-triple-column.json`, per-column JSONs.

### R-L09.4 — Step 6 prompt wiring (frozen)

`TransformedContext` → `serialise_transformed_context_for_judge()` → `build_semantic_judge_prompt()` → Fireworks. Invalid ablation arms hard-fail (`experiment_invalid`, no Arm A fallback). Tag: `r-l09-step6-prompt-wiring`.

### R-L09.5 — Step 7 live hardest-10 (2026-08-17, ~$0.069)

**Decision: B — partial signal.** Relations were in the prompt; aggregate recall did not move.

| Column | Critical recall | MUST_SUPPRESS | Notes |
| --- | --- | --- | --- |
| v1 historical | **0.85** | ≥0.95 | Valid comparator |
| v1 (this run) | 1.00 | 1.00 | Mixed-invalid — 15/30 reps `experiment_invalid`; do not use |
| **v2** | **0.85** | **1.00** | Valid — privacy failures 0 |
| full_synthetic (this run) | 1.00 | 1.00 | **`invalid_experiment`** — privacy gate refused all reps |
| full_synthetic historical | 1.00 | ≥0.95 | Prior oracle anchor |

**Jan 19/20 v2 token-audit semantics:** `actionability_now` **0.9** (was ~0.5–0.7); reason codes mostly `USER_OWNS_ACTION` / `NEAR_TERM_COMMITMENT` / `EXPLICIT_REQUEST` (left `LOW_URGENCY` / `CONTEXT_ONLY`); `time_sensitivity` still **~0.3**.

#### Displacement table (R-L09.5.1)

Historical v1 comparator: `main-benchmark.json` arm B (`evaluation_transformed_v1`, 0.85 aggregate). Step 7 v2: `hardest-10-evaluation_transformed_v2.json` arm B.

| checkpoint | v1/historical | v2 Step 7 | token-inventory-blocker | change |
| --- | --- | --- | --- | --- |
| cp-2026-01-20T11:00 | FAIL | FAIL | 0/3 → 0/3 | shared_fail |
| cp-2026-01-19T10:00 | FAIL | FAIL | 0/3 → **1/3** | shared_fail (token partial) |
| cp-2026-01-11T11:00 | PASS | PASS | n/a | agree |
| cp-2026-01-10T14:00 | PASS | PASS | n/a | agree |
| cp-2026-01-15T13:00 | PASS | PASS | n/a | agree |
| cp-2026-01-25T17:00 | PASS | PASS | n/a | agree |
| cp-2026-01-25T10:00 | PASS | PASS | n/a | agree |
| cp-2026-01-24T15:00 | PASS | PASS | n/a | agree |
| cp-2026-01-24T09:00 | PASS | PASS | n/a | agree |
| cp-2026-01-23T12:00 | PASS | PASS | n/a | agree |

**Outcome summary vs historical v1:** 8 agree, 0 rescues, 0 regressions, 2 shared_fail.

**Arm A vs B (Step 7 `outcome_counts`):** 6 agree, 2 rescues (`cp-2026-01-10T14:00`, `cp-2026-01-11T11:00`), 2 regressions (`cp-2026-01-19T10:00`, `cp-2026-01-20T11:00`).

#### Jan 19/20 rescue status (precise)

| checkpoint | historical v1 token pass | Step 7 v2 token pass | policy surface |
| --- | --- | --- | --- |
| cp-2026-01-19T10:00 | 0/3 | **1/3** (rep2) | rep0: none; rep1: brunch only; rep2: brunch + token |
| cp-2026-01-20T11:00 | 0/3 | 0/3 | 3/3 brunch only (`elena-parents-brunch` contract passes; token `must_surface_missed`) |

**Jan 19:** partial rep-level rescue — not checkpoint majority PASS. **Jan 20:** no rescue.

#### Regression attribution (Jan 19/20 persistent failures) — corrected post R-L10

No checkpoint worsened vs historical v1. Initial R-L09.5.1 label “ranking displacement” was **too broad**. R-L10 Phase 1 reclassified as **semantic improvement + qualification failure**:

- Token-audit semantics improved (`actionability_now` 0.5–0.7 → 0.9; reason codes upgraded) once `BLOCKED_BY`/`state=resolved` reached the prompt.
- Composite stays below 0.72 on **5/6** reps despite high actionability — qualification formula weights `time_sensitivity` (0.25) over `actionability_now` (0.15).
- Jan 19 rep2 proves downstream works: token qualifies (0.7475, rank 2) → Top-3 eval **passes**. Ranking and presentation are **not** implicated.

Do not tune.

---

## Pipeline mental model (post R-L10 Phase 1 closure)

```
WORLD MODEL
    ↓
LLM semantic interpretation       ✅ working better (R-L09)
    ↓
ATTENTION QUALIFICATION           ⚠️ current bottleneck (R-L10 Outcome C)
    ↓
RANKING                            ✅ not implicated
    ↓
PRESENTATION                       ✅ not implicated
```

| Stage | Jan 19/20 evidence |
| --- | --- |
| Transform + relations in prompt | `BLOCKED_BY`, `state=resolved`, causal text in stored `context_json` |
| Semantic features | `actionability_now` 0.5–0.7 → **0.9**; reason codes upgraded |
| Qualification | Composite **< 0.72 on 5/6** token reps despite actionability 0.9 |
| Ranking | Jan 19 rep2 rank 2 still Top-3 **pass** — exonerated |
| Not hard model failure | Jan 19 rep2: token qualifies → downstream works |
| vs historical v1 | 8 agree, 0 regressions, 2 shared_fail |

**Product model (three layers):** qualification (NEEDS YOU — attention-eligible?) → ranking (critical recall@K) → presentation (presented-slot recall / interrupt channel). Production policy emits N surface decisions (no slot cap in `interruption_policy.py`).

**Reasoning freeze:** R-L10 Phase 1 **complete** (Outcome C). Still no judge rubric changes, no policy weight tuning, no model spend, no `support_contracts.yaml` edits until user explicitly unfrozen. Phase 2 = design research (urgency vs opportunity) — no weight tuning yet.

**Follow-up:** [R-L10 ticket](../../tickets/reasoning/R-L10-attention-set-vs-interruption.md) — Phase 2 architectural/design research deferred.

## R-L10 Phase 1 closure — Outcome C (2026-08-17)

**Genuine qualification failure.** Privacy-safe causal relations materially improve semantic understanding of newly unblocked work, but the current deterministic qualification formula does not reliably translate increased actionability into NEEDS YOU eligibility. Five of six Jan 19/20 token-audit reps remain below the 0.72 surface threshold. Ranking, Top-3 evaluation, confidence gates, noise suppression, and presentation cardinality are **not** responsible for the misses.

**Jan 19 rep2 proof:** composite 0.7475, rank 2, Top-3 eval passes — downstream pipeline works when qualification succeeds.

**Formula insight (document only):** Model says “very doable now” (`actionability_now=0.9`); policy composite 0.65–0.70 when `time_sensitivity` ~0.3 — “not urgent enough” despite newly unblocked work.

**Metric reporting note:** The gate aggregate labelled **`critical_recall`** (sometimes written “MUST_SURFACE recall (critical)”) is implemented as **`top3_critical_recall`** in `llm_benchmark.py` / `support_fitness.py` — not top-1. This label conflation should be corrected in a future eval-harness pass; it did not affect Phase 1 conclusions.

Frozen Step 7 v2 features replayed through production `composite_surface_score` / `decide_interruption`. **No model spend. No weight/prompt/truth changes.** Stored policy scores match recomputed composites on every surfaced row.

**Formula:** `0.25*obligation_strength + 0.20*user_responsibility + 0.15*importance + 0.25*time_sensitivity + 0.15*actionability_now` + overdue(+0.12) + near-term(+0.10×(1−h/36) if h≤36) + calendar(+0.05 if cal≤2h); ×0.30 if noise evidence. Surface if ≥0.72. Confidence / restful-weekend / noise gates did not block token-audit (weekdays, confidence ≥0.9).

**Finding:** LLM marks token-audit actionable (`actionability_now=0.9` all 6 reps). Qualification still fails on **5/6** reps because `time_sensitivity` (weight 0.25) stays 0.3–0.4 and brunch gets a +0.05 calendar boost token does not. Token is **not** already ≥0.72 except Jan 19 rep2 (0.7475, rank 2, Top-3 **pass**). Slot budget 2 would not rescue the other five reps.

| checkpoint | rep | brunch composite | token composite | token layer |
| --- | ---: | ---: | ---: | --- |
| Jan 19 | 0 | 0.685 context | 0.673 context | qualification failure |
| Jan 19 | 1 | 0.888 surface #1 | 0.665 context | qualification failure |
| Jan 19 | 2 | 0.817 surface #1 | 0.748 surface #2 | surfaced in Top-3 (contract pass) |
| Jan 20 | 0 | 0.785 surface #1 | 0.657 context | qualification failure |
| Jan 20 | 1 | 0.923 surface #1 | 0.669 context | qualification failure |
| Jan 20 | 2 | 0.953 surface #1 | 0.697 context | qualification failure |

**Outcome: C** (genuine qualification failure). Ranking and presentation **exonerated**. **B** is the mechanism (single composite; ts-heavy weights + brunch calendar boost). **D** (MUST_SURFACE vs interrupt-now) remains documented ambiguity — no truth rewrite.

Jan 19/20 three-layer: attention-eligibility recall **0.44** (4/9); critical recall@1/@2/@3 = 0.25 / 0.42 / 0.42; presented-slot N=1/N=2 = 0.25 / 0.42. Full table: ticket R-L10 / `reports/reasoning-gate-live/rl10-jan19-20-decomposition.json`.

**Audit proof** (`reports/reasoning-gate-live/prompt-audit.jsonl`, v2 `item-obligation_token_audit`):

```json
{
  "type": "BLOCKED_BY",
  "subject": "TASK_TOKEN_AUDIT",
  "object": "RESOURCE_TOKENS",
  "state": "resolved",
  "resolved_by": "PERSON_A",
  "causal": "RESOURCE_TOKENS arrival made TASK_TOKEN_AUDIT actionable"
}
```

Present on both `cp-2026-01-19T10:00` and `cp-2026-01-20T11:00` stored `context_json`.

**R-L09 A/B/C (not R-L10):** **Not A** (recall not 0.95–1.00). **Not C** (semantics moved; relations demonstrably in prompt). Main not eligible.

---

## Original main gate (B2 + evaluation_transformed_v1)

- Live Fireworks: `True`
- Context arm: **`evaluation_transformed_v1`** (evaluation stub — not production transformer at prompt boundary)
- Total cost: $0.2639

### Exit gate metrics

> **Label note:** “Critical recall” in this table is the gate aggregate implemented as **`top3_critical_recall`** (obligation in top-3 alerts), not top-1 or a separate “MUST_SURFACE recall (critical)” metric.

| Metric | Arm A | LLM B | Delta |
| --- | --- | --- | --- |
| Critical recall (Top-3 aggregate) | 0.925 | 0.850 | -0.075 |
| MUST_SUPPRESS accuracy | 0.975 | 1.000 | +0.025 |
| Top-3 critical recall | 0.925 | 0.850 | -0.075 |
| Next-action fit | 1.000 | 0.950 | -0.050 |
| Stable decisions (B) | n/a | 98.3% | — |
| Provider transport failures | — | 5.0% | — |
| Model schema failures | — | 0.0% | — |
| Privacy failures | — | 0.0% | — |
| Critical regressions | — | 2 | — |
| Rescues | — | 2 | — |

### Rescues and regressions

- **Rescues (2):** quiet-period restraint (`cp-2026-01-10T14:00`, `cp-2026-01-11T11:00`).
- **Regressions (2):** token-inventory blocker context lost under v1 (`cp-2026-01-19T10:00`, `cp-2026-01-20T11:00`).

### Privacy ablation (10 hardest)

- Critical recall delta (full − eval_v1): **+0.15**
- Suggests lost task-relevant semantics, not model incapacity — motivated R-L09.

## Architecture decision

**Decision:** `no_win` (production). R-L09.5 = **B**; research may inspect displacement without threshold tuning or a main rerun.

## Failure attributions (main gate)

- `cp-2026-01-19T10:00` [ATTENTION_POLICY]: Attention disagreement
- `cp-2026-01-20T11:00` [ATTENTION_POLICY]: Attention disagreement
