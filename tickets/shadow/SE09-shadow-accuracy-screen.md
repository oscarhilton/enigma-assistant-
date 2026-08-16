# SE09 — Shadow accuracy screen (private)

| Field | Value |
| --- | --- |
| Status | `todo` |
| Branch | `ticket/SE09-shadow-accuracy-screen` |
| Domain | `shadow` |
| Baseline | [shadow-silence-evaluation.md](../../docs/architecture/shadow-silence-evaluation.md) |

## Package boundary (hard)

- May edit: `apps/web/src/**` **excluding** `apps/web/src/demo/**` (Demo chrome frozen for this track)
- May edit: `apps/api/**` Shadow accuracy stub routes
- May edit: matching tests
- Must **not** reuse Demo attention card components as the accuracy product
- Must **not** enable OS notifications
- Must **not** start Gmail OAuth

## Hard depends

- None for static wireframe / route stubs with fixture JSON

## Soft depends (~)

- SE04–SE08 data contracts
- S01 banner (already done)
- S02 storage

## Unlocks / enhances

- Human adjudication loop for silence proof
- Makes empty-screen claims inspectable

## Non-goals

- Full Shadow product shell / onboarding
- Desktop tray polish (separate desktop tickets if any)
- Demo Mode visual parity

## Acceptance criteria

- [ ] Private Shadow accuracy sketch/page showing: today counts, audits queue, misses reported, behavioural mismatches
- [ ] Click-through adjudication for a mismatch → label without auto-fail default
- [ ] Stratified audit prompt wiring (or fixture-backed stub)
- [ ] Miss-report entry point (pointer or describe)
- [ ] Metrics strip: Suppression Accuracy + Silent Miss Rate (fixture OK)
- [ ] Unmistakable Shadow / observation labelling (no Demo scenario chrome)
- [ ] Tests: render/smoke with fixture JSON; assert demo attention modules not imported

## Test plan

- Component/route smoke with stub payloads
- Guard: no import from `apps/web/src/demo/attention*`

## Privacy constraints

- Screen is local-only; no remote scoring of queues
- Prefer transformed refs in list rows
