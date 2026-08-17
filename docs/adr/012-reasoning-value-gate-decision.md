# ADR-012: Reasoning Value Gate architecture decision

**Status:** Accepted (live gate evidence — B2 + evaluation_transformed_v1; R-L09 Step 7 = **B**)
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

**Displacement:** No new checkpoint failed. Jan 20 3/3 still miss token-audit while brunch surfaces; Jan 19 2/3 miss, 1/3 surfaces token-audit. Policy still sees `time_sensitivity` ~0.3. Do not tune. Do not run main.

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
6. **Relations-in-prompt (R-L09.5)** — Step 6 closed the wiring gap. Step 7: **B**. Causal relations in the prompt moved token-audit *features* (`actionability_now` → 0.9) but not aggregate recall (still 0.85). `time_sensitivity` stayed ~0.3; brunch still displaced token-audit on Jan 20.

## Interim research direction (after R-L09.5 / decision B)

Inspect displacement (policy vs remaining low `time_sensitivity`) **without** threshold tuning, prompt edits, or a main rerun. Main is eligible only under outcome A.

## Multi-axis decision table

| Outcome | Criteria |
| --- | --- |
| CLEAR WIN | recall Δ≥+5pp AND suppress Δ≥-1pp AND regressions=0 AND model schema/privacy=100% |
| SMALL WIN | hybrid threshold (recall Δ≥+2pp, suppress Δ≥-1pp, ≤1 regression) |
| NO WIN | keep deterministic |

See [reasoning-value-gate-live-report.md](../reports/reasoning-value-gate-live-report.md).
