# Feature scenario — unrelated-machine-mail-not-merged

| Field | Value |
| --- | --- |
| Status | `in_progress` |
| Branch | `ticket/F-unrelated-machine-mail-not-merged` |
| Domain | `demo-evaluation` |
| Related | D08c, D08d, D07, M15 |
| Path | `scenarios/feature/unrelated-machine-mail-not-merged/` |

## Intent

PrizeVault-style retrieval / commitment-merge pollution: unrelated machine mails
(PrizeVault, BuildCloud, ProductPulse, GrowthKit, DesignLedger, …) that share
generic sludge wording must **not** collapse into one `INFERRED_COMMITMENT` or
one attention-candidate fingerprint. D08c A/B artefacts record pollution traces
when a decision would otherwise hide the collapse.

## Package boundary

- May edit: `packages/evaluation/**`
- May edit: `scenarios/feature/unrelated-machine-mail-not-merged/**`
- May edit: `tickets/demo-evaluation/F-unrelated-machine-mail-not-merged.md`
- May edit (minimal): `packages/obligations/**` — email↔email merge must ignore
  shared machine-generic tokens so the regression can pass
- Must not edit: `packages/attention/**`, heavy `apps/web` demo chrome

## Hard depends

- D07 evaluation runner
- D08c A/B artefacts / pollution-trace expectation
- D08d noise brand vocabulary (fictional brands only)

## Soft depends (~)

- `F-retrieval-keyword-pollution`
- `F-background-no-alert`

## Unlocks / enhances

- Explainable D08c pollution traces on A/B reports
- Regression gate against cross-brand commitment merge

## Non-goals

- Changing HeuristicAttentionEngine ranking (`packages/attention`)
- Demo UI chrome
- Shipping trademarked provider brands

## Acceptance criteria

- [x] `PollutionTrace` schema in `ab_eval` (+ optional `pollution_traces` on
      `storyline_ab_report`)
- [x] Tiny feature scenario with ≥4 distinct fictional machine brands
- [x] Eval asserts unrelated mails do not share one commitment fingerprint
- [x] Ground-truth marks each mail `signal_class: noise` / `expected_attention: false`
- [x] Source payloads omit evaluator-only keys

## Test plan

- [x] Unit: pollution detector flags collapsed evidence; clean singletons pass
- [x] Package load + GT for `unrelated-machine-mail-not-merged`
- [x] Live `merge_sources_to_attention` keeps one fingerprint per brand mail
- [x] Existing obligations merge tests still pass (Review proposal, etc.)

## Privacy constraints

- Fictional `.example` brands only; no Enigma-visible evaluator fields
