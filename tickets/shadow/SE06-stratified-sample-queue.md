# SE06 — Stratified sample queue

| Field | Value |
| --- | --- |
| Status | `todo` |
| Branch | `ticket/SE06-stratified-sample-queue` |
| Domain | `shadow` |
| Baseline | [shadow-silence-evaluation.md](../../docs/architecture/shadow-silence-evaluation.md) |

## Package boundary (hard)

- May edit: `packages/evaluation/**` for sampler + queue models
- May edit: `apps/api/**` thin `/shadow/audits/*` stub routes if needed (no Demo chrome)
- May edit: tests
- Must **not** build full polished UX (SE09 owns screen); copy contracts OK
- Must **not** edit Demo Mode UI files under `apps/web/src/demo/**`

## Hard depends

- None for offline sampler + fixtures

## Soft depends (~)

- SE04 decision log (population)
- SE08 metrics (consume labels)
- SE09 accuracy screen
- S02 storage

## Unlocks / enhances

- Human labels for Suppression Accuracy denominator
- Active learning toward borderline / ambiguous strata

## Non-goals

- Shipping 3–5/day push notifications (queue + prompt contract only)
- Claiming statistical significance

## Acceptance criteria

- [ ] Daily sample config (default 3–5) with strata: near-threshold, very-low-score, human-requests, calendar-derived, machine-mail, uncertain
- [ ] Label enum: `should_have_surfaced` | `fine_to_suppress` | `unsure`
- [ ] UX copy contract: “Enigma decided these did not need your attention. Was that right?”
- [ ] Active-learning hooks: reduce weight on strata with consistent `fine_to_suppress`; boost borderline / relationship / time-sensitive
- [ ] Tests: stratified draw from fixture decision log; empty-population safe

## Test plan

- Fixed RNG fixture yields mixed strata
- Reweight after synthetic “all fine” machine-mail labels

## Privacy constraints

- Audit queue local to Shadow root
- Present transformed refs in API stubs by default
