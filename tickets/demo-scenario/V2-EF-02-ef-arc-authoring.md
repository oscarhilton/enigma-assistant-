# V2-EF-02 — Support-contract overlay on six-month Alex (stretch)

> **Stretch after [R07](../reasoning/R07-reasoning-value-gate-report.md) passes.**
> Corpus home moved: six months of **ordinary events** live in `scenarios/alex-v1/`
> ([D08f](./D08f-alex-six-month.md)), not a new `alex-v2` package.
> This ticket authors **evaluator support contracts** on those threads — not a second mailbox.

| Field | Value |
| --- | --- |
| Status | `todo` (stretch — blocked on R07; **do not fork alex-v2**) |
| Branch | `ticket/V2-EF-02-ef-arc-authoring` |
| Domain | `demo-scenario` |

## Package boundary (hard)

- May edit: `scenarios/alex-v1/ground_truth/support_contracts.yaml` (additive contracts for Feb–Jun threads), `docs/architecture/executive-function-support-benchmark.md` (arc index appendix only)
- Must not edit: `packages/evaluation/**` scoring (R04), `packages/attention/**`
- Must not create: `scenarios/alex-v2/`
- Must not rewrite: D08f source-event months (those are D08f-02…06)

## Hard depends

- D03 (scenario format)
- [D08f](./D08f-alex-six-month.md) six-month ordinary life (events, not contracts)
- [R01](../reasoning/R01-scenario-truth-catalogue.md) support contract schema + loader (supersedes V2-EF-01)
- [R07](../reasoning/R07-reasoning-value-gate-report.md) gate pass (architecture decision landed)

## Soft depends (~)

- D08b–e corpus patterns (background density)
- Monthly D08f-02…06 events actually present for the three threads

## Unlocks / enhances

- Support fitness on longitudinal *ordinary* threads (not a 12-month novel)
- Next question: *Does accumulated memory improve reasoning over 6–12 months?*

## Non-goals

- A second Alex package (`scenarios/alex-v2/`)
- ~30 arcs / 12-month span (original Phase 2.5 scope — still deferred)
- Writing six months of biography
- Full 115k background replay or 40k email generation
- Private Mode ingestion changes
- UI for Next Action
- C11 tone runtime

## Acceptance criteria

- [ ] **No** `scenarios/alex-v2/` directory
- [ ] Three EF **threads** tagged on the existing alex-v1 Jan–Jun events (not separate packages):
  1. **Boring recurring admin** — expenses / timesheet drift; learn pattern without shaming
  2. **Long-running work project** — Atlas/token/checkout-style ambiguity over months
  3. **Relationship/social commitment** — parents / partner coordination across visits
- [ ] Each thread includes: pointers to D08f source evidence, obligation/window truth, support contract, ≥1 checkpoint where attention ≠ next_action
- [ ] Persona traits author-side only; every contract tags `support_challenges` in ground truth
- [ ] Version bump of alex-v1 ground truth only (additive); do not mutate 0.2.1 January timeline semantics
- [ ] No 40k generation — use profiles like alex-v1 (demo / canonical scale documented, not enabled in PR CI)

## Test plan

- Scenario validator still passes alex-v1
- Spot-check: every new support contract validates against v0 schema
- Deterministic double-load byte stability

## Privacy constraints

- Fictional content only; no Private paths or real correspondence

## Notes

- Ordinary-events corpus: [demo-corpus.md](../../docs/architecture/demo-corpus.md#six-month-ordinary-life-d08f)
- Sprint charter: [reasoning-value-gate.md](../../docs/demo/reasoning-value-gate.md)
- Original eight EF patterns remain design reference for future expansion — not this ticket's scope
