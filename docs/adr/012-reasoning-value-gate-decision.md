# ADR-012: Reasoning Value Gate architecture decision

**Status:** Accepted (live gate evidence — B2 + evaluation_transformed_v1; R-L09 integration finding)
**Date:** 2026-08-17
**Git:** `1c80841`

## Production decision (narrow scope)

**no_win** — No win — keep deterministic (recall Δ=-0.075, regressions=2, model_schema_fail=0.0%). Provider transport failures=5.0% (excluded from model schema rate).

Keep deterministic interruption policy. Do **not** adopt remote reasoning from this gate alone.

### What was tested

| Scope | Result |
| --- | --- |
| B2 + `evaluation_transformed_v1` | **PROVEN** → `no_win` |
| B2 + `evaluation_transformed_v2` (Step 5 live) | **NO MOVEMENT** — see R-L09 chronology below |
| B2 + `DefaultEnigmaTransformer` in prompt | **NOT YET PROVEN** — R-L09 Step 6 follow-up |

## R-L09 chronology (research record)

| Phase | Finding |
| --- | --- |
| **R-L09.1** | Offline transform lacked causal semantics → fixed (`relations[]`, BLOCKED_BY resolution, production parity as `evaluation_transformed_v2`). |
| **R-L09.2** | Offline causal-preservation gate passed (Jan 19/20 checkpoints). |
| **R-L09.3** | Live hardest-10: v2 critical recall **0.85** vs historical v1 **0.85** — **NO MOVEMENT**. Investigation: `relations[]` never entered the semantic judge prompt (`snapshot_to_context_dict()` fork). Result classified as **integration/wiring negative**, not semantic-preservation hypothesis falsification. |
| **R-L09.4** | Next experiment: route privacy-gated `TransformedContext` directly into semantic judge prompt (Step 6); re-run hardest-10 only. |

### Step 5 live hardest-10 (2026-08-17)

| Column | Critical recall | Valid? |
| --- | --- | --- |
| v1 (frozen) | 1.00 | **No** — prompt-build failures silently fell back to Arm A scoring |
| v2 | **0.85** | Yes |
| full_synthetic | 1.00 | Yes, but byte-identical prompt to v2 (confound) |

Cost: ~$0.058. v2 MUST_SUPPRESS: 1.00. Privacy failures: 0.

**Architectural finding:** Privacy transformation and reasoning pipelines were conceptually connected but **not connected at the final model-input boundary**. Fireworks receives only the prompt string; `TransformedContext.relations[]` passed `assert_remote_safe()` but was never serialised into it. This is exactly the class of boundary violation the benchmark programme is designed to uncover.

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

## Interim research direction (R-L09 Step 6)

**Prompt wiring:** `TransformedContext` → serialise → `build_semantic_judge_prompt()` → Fireworks. Eliminate the parallel `snapshot_to_context_dict()` path for live judge calls. Hard-fail invalid ablation arms (no Arm A fallback). Re-gate hardest-10 only (~$0.05).

**Frozen:** `evaluation_transformed_v2` transform logic until Step 7 live result is recorded.

## Multi-axis decision table

| Outcome | Criteria |
| --- | --- |
| CLEAR WIN | recall Δ≥+5pp AND suppress Δ≥-1pp AND regressions=0 AND model schema/privacy=100% |
| SMALL WIN | hybrid threshold (recall Δ≥+2pp, suppress Δ≥-1pp, ≤1 regression) |
| NO WIN | keep deterministic |

See [reasoning-value-gate-live-report.md](../reports/reasoning-value-gate-live-report.md).
