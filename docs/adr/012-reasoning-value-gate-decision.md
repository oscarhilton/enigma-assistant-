# ADR-012: Reasoning Value Gate architecture decision

**Status:** Accepted (live gate evidence — B2 + evaluation_transformed_v1; R-L09 **complete** — decision **B**; R-L10 Phase 1 **complete** — Outcome **C**; freeze on tuning/spend continues)
**Date:** 2026-08-17
**Git:** freeze `50198fc` / tag `r-l09-step6-prompt-wiring`

## Production decision (narrow scope)

**no_win** — No win — keep deterministic (recall Δ=-0.075, regressions=2, model_schema_fail=0.0%). Provider transport failures=5.0% (excluded from model schema rate).

Keep deterministic interruption policy. Do **not** adopt remote reasoning from this gate alone.

### What was tested

| Scope | Result |
| --- | --- |
| B2 + `evaluation_transformed_v1` | **PROVEN** → `no_win` |
| B2 + `evaluation_transformed_v2` (Step 5 live) | **NO MOVEMENT** — wiring gap; relations never in prompt |
| B2 + `TransformedContext` in prompt (Step 7 live) | **B — partial signal** — recall still 0.85; Jan 19/20 semantics moved |

## R-L09 chronology (research record)

| Phase | Finding |
| --- | --- |
| **R-L09.1** | Offline transform lacked causal semantics → fixed (`relations[]`, BLOCKED_BY resolution, production parity as `evaluation_transformed_v2`). |
| **R-L09.2** | Offline causal-preservation gate passed (Jan 19/20 checkpoints). |
| **R-L09.3** | Live hardest-10: v2 critical recall **0.85** vs historical v1 **0.85** — **NO MOVEMENT**. Investigation: `relations[]` never entered the semantic judge prompt (`snapshot_to_context_dict()` fork). Result classified as **integration/wiring negative**, not semantic-preservation hypothesis falsification. |
| **R-L09.4** | Step 6: route privacy-gated `TransformedContext` into semantic judge prompt (frozen at `r-l09-step6-prompt-wiring`). |
| **R-L09.5** | Step 7 live hardest-10 (~$0.069): **decision B**. v2 critical recall **0.85** vs historical v1 **0.85**; MUST_SUPPRESS 1.00; v2 privacy failures 0. Jan 19/20 `actionability_now` 0.5–0.7→**0.9** and reason codes left `LOW_URGENCY`/`CONTEXT_ONLY`; `time_sensitivity` stayed ~0.3. Relations (`BLOCKED_BY`, `state=resolved`) were in the stored prompt `context_json`. Remaining misses are still Jan 19/20 (brunch displacement / policy did not surface token-audit) — not a new checkpoint regression. **Not eligible for main.** Do not tune thresholds. |
| **R-L09.5.1** | Step 7 displacement attribution (read-only, no tuning): **zero net checkpoint movement** vs historical v1 B (`main-benchmark.json`). 8 agree PASS, 2 shared_fail (Jan 19/20). Jan 19 token-inventory-blocker **0/3→1/3** rep rescue (rep2 surfaces both brunch + token); Jan 20 **0/3→0/3** (3/3 brunch-only policy surface). No checkpoint worsened vs historical v1. Arm-A-vs-B regressions (Jan 19/20) persist — bucket **1** (semantic improvement + qualification failure): token `actionability_now`↑ but composite stays below 0.72 on 5/6 reps. R-L10 Phase 1 confirmed ranking/presentation not implicated. |

### Step 5 live hardest-10 (2026-08-17)

| Column | Critical recall | Valid? |
| --- | --- | --- |
| v1 (frozen) | 1.00 | **No** — prompt-build failures silently fell back to Arm A scoring |
| v2 | **0.85** | Yes |
| full_synthetic | 1.00 | Yes, but byte-identical prompt to v2 (confound) |

Cost: ~$0.058. v2 MUST_SUPPRESS: 1.00. Privacy failures: 0.

**Architectural finding:** Privacy transformation and reasoning pipelines were conceptually connected but **not connected at the final model-input boundary**. Fireworks receives only the prompt string; `TransformedContext.relations[]` passed `assert_remote_safe()` but was never serialised into it. This is exactly the class of boundary violation the benchmark programme is designed to uncover.

### Step 7 live hardest-10 (2026-08-17, freeze `50198fc` / `r-l09-step6-prompt-wiring`)

| Column | Critical recall | Valid? |
| --- | --- | --- |
| v1 historical | **0.85** | Yes — comparator (this-run v1 mixed-invalid) |
| v1 (this run) | 1.00 | **No** — 15/30 reps `experiment_invalid` (raw possessive identity); remaining quiet checkpoints inflate recall. Hard-fail worked (no Arm A fallback). |
| **v2** | **0.85** | Yes |
| full_synthetic (this run) | 1.00 | **No** — `invalid_experiment=true` (privacy gate refused all reps). Historical oracle 1.00 still stands as prior anchor. |

Cost: **$0.069**. v2 MUST_SUPPRESS: **1.00**. v2 privacy failures: **0**.

**Predeclared A/B/C:** **B — partial signal.** Aggregate unchanged vs 0.85, but token-audit semantics moved and prompt audit proves `BLOCKED_BY` / `state=resolved` / causal text reached the model. Not A (recall not 0.95–1.00). Not C (Jan 19/20 are no longer stuck on `LOW_URGENCY`/`CONTEXT_ONLY`). Harness `no_movement` label is the older aggregate-only rule and does not override A/B/C.

**Displacement (R-L09.5.1):** Per-checkpoint v1-historical vs Step-7-v2 — 8 agree PASS, 2 shared_fail (Jan 19/20 only). **No new regressions** vs historical v1. Jan 19 token contract 0/3→**1/3** rep pass; Jan 20 0/3 unchanged (brunch-only surface all reps). Initial attribution: semantics improved (`actionability_now` 0.9) but composite below threshold on most reps. **R-L10 Phase 1 corrected attribution** to qualification failure (not ranking displacement). Do not tune. Do not run main.

## Live evidence (original main gate — B2 + evaluation_transformed_v1)

| Metric | Arm A | LLM B | Delta |
| --- | --- | --- | --- |
| Critical recall | 0.925 | 0.850 | -0.075 |
| Must-suppress accuracy | 0.975 | 1.000 | +0.025 |
| Top-3 critical recall | 0.925 | 0.850 | -0.075 |
| Next-action fit | 1.000 | 0.950 | -0.050 |
| Total live cost | ~$0 | $0.2639 | — |
| B stability | n/a | 98.3% | — |
| Rescues | — | 2 | — |
| Critical regressions | — | 2 | — |
| Provider transport failures | — | 5.0% | — |
| Model schema failures | — | 0.0% | — |
| Privacy ablation critical recall Δ (full − eval_v1) | — | — | +0.150 |

## Research findings (do not overstate as production conclusions)

1. **Direct judge (B1) failed** — anchored prompt leaked Arm A labels; de-anchored collapsed.
2. **Semantic judge + policy (B2) is viable** — smoke 9/9; main stability 98.3%.
3. **Transform gap dominates recall** — hardest-10: eval_v1 recall 0.85 vs full_synthetic 1.00 (+15pp).
4. **Failure taxonomy was polluted** — reported 5% “schema” failures were HTTP 403 transport errors.
5. **Prompt wiring gap (R-L09.3)** — v2 preserved causal semantics offline but the live judge never received them; Step 5 did not test the semantic-preservation hypothesis, only the current integration path.
6. **Relations-in-prompt (R-L09.5)** — Step 6 closed the wiring gap. Step 7: **B**. Causal relations in the prompt moved token-audit *features* (`actionability_now` → 0.9) but not aggregate recall (still 0.85). R-L10 Phase 1: qualification formula does not translate actionability into eligibility — not a ranking problem.

## R-L09 conclusion (2026-08-17 — complete, frozen)

R-L09 is **done**. Step 7 outcome **B** with displacement bucket **1** (**semantic improvement + qualification failure** — attribution corrected post R-L10). Zero checkpoint regressions vs historical v1 (8 agree, 2 shared_fail on Jan 19/20).

### Pipeline mental model (post R-L10 Phase 1)

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

Semantic judge wiring (Step 6) closed the integration gap. Remaining misses are an **attention qualification** problem, not evidence of hard model incapacity (Jan 19 rep2: token qualifies at 0.7475, rank 2, Top-3 eval passes).

**Formula insight (document only — do not change weights):** `WEIGHT_TIME_SENSITIVITY=0.25` vs `WEIGHT_ACTIONABILITY_NOW=0.15`. Model marks newly unblocked work as actionable (`actionability_now=0.9`); policy composite stays 0.65–0.70 when `time_sensitivity` ~0.3 — product philosophy compressed into one threshold.

### Product model distinction (motivates R-L10)

Three layers — do not bake conclusions into metric names:

| Layer | Name | Question | Offline metric (R-L10) |
| --- | --- | --- | --- |
| Qualification | NEEDS YOU / attention-eligible | Does this deserve attention at all? | Attention-eligibility recall |
| Ranking | Priority among eligible | Where among eligible things? | Critical recall@K, rank, MRR |
| Presentation | Interrupt / show now | What actually reaches the user? | Presented-slot recall |

Production `decide_interruption()` can emit **N surface decisions** (no slot cap in `interruption_policy.py`). The gate aggregate `critical_recall` is implemented as **Top-3 critical recall**; Top-1 is a separate metric. Jan 19 rep2 surfaced both brunch and token — a Top-1 miss is not automatically a qualification failure.

The benchmark may conflate `MUST_SURFACE` author intent with Top-1 presentation scoring. See [next-action.md](../architecture/next-action.md) · [ADR-010](010-next-action-not-attention.md). R-L10 compares **analysis model A** (0.72 as eligibility) vs **analysis model B** (policy as implemented) without changing code.

### Reasoning freeze

R-L10 Phase 1 **complete** (Outcome C). Freeze **continues** until user explicitly directs otherwise:

- **No** judge rubric changes
- **No** policy weight tuning (`WEIGHT_*`, `SURFACE_SCORE_THRESHOLD`)
- **No** model spend on reasoning gate arms
- **No** main rerun (eligible only under outcome A — not met)
- **No** `support_contracts.yaml` edits

Phase 2 = **future design research** (urgency vs opportunity, NEEDS YOU semantics) — not implementation or weight tuning without explicit approval. R-L11 candidate.

Follow-up ticket: **[R-L10 — Attention qualification vs ranking vs presentation](../../tickets/reasoning/R-L10-attention-set-vs-interruption.md)** (Phase 1 complete; Phase 2 design research deferred).

### R-L10 Phase 1 conclusion (offline, 2026-08-17) — Outcome C

**Genuine qualification failure.** Privacy-safe causal relations materially improve semantic understanding of newly unblocked work, but the current deterministic qualification formula does not reliably translate increased actionability into NEEDS YOU eligibility. Five of six Jan 19/20 token-audit reps remain below `SURFACE_SCORE_THRESHOLD` (0.72). Ranking, Top-3 evaluation, confidence gates, noise suppression, and presentation cardinality are **not** responsible.

Replay of frozen Step 7 v2 semantic features through production `composite_surface_score`. Token-audit `actionability_now=0.9` on all Jan 19/20 reps; composite **< 0.72 on 5/6** (`context`). Only Jan 19 rep2 crosses the bar (0.7475), surfaces at rank 2, and Top-3 **passes** — proves downstream works when qualification succeeds. Confidence / weekend / noise gates are not the miss. Brunch’s +0.05 calendar boost and ts-heavy weights explain the gap vs token.

**Outcome: C** (qualification failure). **B** as mechanism (single composite). **A** and presentation layers exonerated. **D** recorded as MUST_SURFACE wording ambiguity. Slot budget 2 would not rescue below-threshold reps. Do not tune.

**Future design research (Phase 2 — not implementation):** Two latent concepts compressed into `time_sensitivity` + one threshold:

| Concept | Question | Bias |
| --- | --- | --- |
| **URGENCY** | How costly is delay? | Notification-system |
| **OPPORTUNITY** | How good a moment is this to act? (blocked→unblocked) | Newly possible work |

NEEDS YOU semantics: if synonymous with *urgent*, current policy is reasonable; if “important enough, actionable enough, timely enough, or newly possible enough to hold in active attention set”, qualification model is too one-dimensional. Example product copy: *“Nothing urgent needs you. But one thing just became worth doing: the token work is unblocked now.”*

**Reporting note:** gate aggregate labelled `critical_recall` is implemented as **`top3_critical_recall`** — “MUST_SURFACE recall (critical)” in some reports is misleading; eventual label correction tracked, not a Phase 1 blocker.

Details: [R-L10 ticket Phase 1 results](../../tickets/reasoning/R-L10-attention-set-vs-interruption.md) · [live report](../reports/reasoning-value-gate-live-report.md).

## Multi-axis decision table

| Outcome | Criteria |
| --- | --- |
| CLEAR WIN | recall Δ≥+5pp AND suppress Δ≥-1pp AND regressions=0 AND model schema/privacy=100% |
| SMALL WIN | hybrid threshold (recall Δ≥+2pp, suppress Δ≥-1pp, ≤1 regression) |
| NO WIN | keep deterministic |

See [reasoning-value-gate-live-report.md](../reports/reasoning-value-gate-live-report.md).
