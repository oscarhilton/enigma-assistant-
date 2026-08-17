# V2-EF-02 — Alex v2 longitudinal arcs (stretch — 3 arcs)

> **Stretch scope after [R07](../reasoning/R07-reasoning-value-gate-report.md) passes.**
> Original ~30-arc / 12-month plan deferred until the Reasoning Value Gate answers
> whether LLM reasoning beats heuristics on alex-v1.

| Field | Value |
| --- | --- |
| Status | `todo` (stretch — blocked on R07) |
| Branch | `ticket/V2-EF-02-ef-arc-authoring` |
| Domain | `demo-scenario` |

## Package boundary (hard)

- May edit: `scenarios/alex-v2/**` (new package — do not mutate `scenarios/alex-v1/`)
- May edit: `docs/architecture/executive-function-support-benchmark.md` (arc index appendix only)
- Must not edit: `packages/evaluation/**` scoring (R04), `packages/attention/**`

## Hard depends

- D03 (scenario format)
- [R01](../reasoning/R01-scenario-truth-catalogue.md) support contract schema + loader (supersedes V2-EF-01)
- [R07](../reasoning/R07-reasoning-value-gate-report.md) gate pass (architecture decision landed)

## Soft depends (~)

- D08b–e corpus patterns (background density for v2)

## Unlocks / enhances

- Longitudinal benchmark (3–6 month arcs, not full year)
- R04 support fitness eval on authored contracts
- Next question: *Does accumulated memory improve reasoning over 6–12 months?*

## Non-goals

- ~30 arcs / 12-month span (original Phase 2.5 scope — deferred)
- Full 115k background replay or 40k email generation
- Private Mode ingestion changes
- UI for Next Action

## Acceptance criteria

- [ ] New immutable package `scenarios/alex-v2/` with **3 longitudinal arcs only** (3–6 months each):
  1. **Boring recurring admin** — expenses / timesheet drift; learn pattern without shaming
  2. **Long-running work project** — Atlas-style ambiguity and decomposition over months
  3. **Relationship/social commitment** — parents multi-visit coordination across visits
- [ ] Each arc includes: timeline evidence, obligation/window truth, support contract, ≥1 checkpoint where attention ≠ next_action
- [ ] Persona traits author-side only; every arc tags `support_challenges` in ground truth
- [ ] README + `scenario.yaml` version immutability rules match alex-v1 conventions
- [ ] No 40k generation — use profiles like alex-v1 (demo / canonical scale documented, not enabled in PR CI)

## Test plan

- Scenario validator passes full alex-v2 package (3 arcs)
- Spot-check: every support contract validates against v0 schema
- Deterministic double-load byte stability

## Privacy constraints

- Fictional content only; no Private paths or real correspondence

## Notes

- Sprint charter: [reasoning-value-gate.md](../../docs/demo/reasoning-value-gate.md)
- Original eight EF patterns remain design reference for future arc expansion — not this ticket's scope
