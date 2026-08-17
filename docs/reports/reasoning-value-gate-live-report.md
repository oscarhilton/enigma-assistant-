# Reasoning Value Gate — Live Report

- Generated: 2026-08-17 (updated R-L09 Step 7)
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

#### Regression attribution (Jan 19/20 persistent failures)

No checkpoint worsened vs historical v1. Both persistent failures classified **bucket 1 — semantic improvement, ranking displacement (Top-N budget)**:

- Token-audit semantics improved (`actionability_now` 0.5–0.7 → 0.9; reason codes upgraded) once `BLOCKED_BY`/`state=resolved` reached the prompt.
- `time_sensitivity` stayed ~0.3 (Jan 20 brunch 0.6–0.88), so `composite_surface_score` (weight 0.25 on time sensitivity) still ranks brunch Top-1.
- Jan 19 rep2 proves both can surface when brunch score is closer — variance across reps contributes but pattern is coherent (not bucket 3).

Do not tune.

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

**Not A** (recall not 0.95–1.00). **Not C** (semantics moved; relations demonstrably in prompt). Main not eligible.

---

## Original main gate (B2 + evaluation_transformed_v1)

- Live Fireworks: `True`
- Context arm: **`evaluation_transformed_v1`** (evaluation stub — not production transformer at prompt boundary)
- Total cost: $0.2639

### Exit gate metrics

| Metric | Arm A | LLM B | Delta |
| --- | --- | --- | --- |
| MUST_SURFACE recall (critical) | 0.925 | 0.850 | -0.075 |
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
