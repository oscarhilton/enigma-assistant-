# V2-EF-02 — Alex v2 EF arc authoring (~30 arcs)

| Field | Value |
| --- | --- |
| Status | `todo` |
| Branch | `ticket/V2-EF-02-ef-arc-authoring` |
| Domain | `demo-scenario` |

## Package boundary (hard)

- May edit: `scenarios/alex-v2/**` (new package — do not mutate `scenarios/alex-v1/`)
- May edit: `docs/architecture/executive-function-support-benchmark.md` (arc index appendix only)
- Must not edit: `packages/evaluation/**` scoring (EF-01), `packages/attention/**`

## Hard depends

- D03 (scenario format)
- [V2-EF-01](./V2-EF-01-support-contract-design.md) support contract schema frozen

## Soft depends (~)

- D08b–e corpus patterns (background density for v2)

## Unlocks / enhances

- Longitudinal benchmark (12-month Alex)
- EF-01 support fitness eval on authored contracts
- Phase 2.5 “second squeeze” gate

## Non-goals

- Full 115k background replay (use profiles like alex-v1)
- Private Mode ingestion changes
- UI for Next Action

## Acceptance criteria

- [ ] New immutable package `scenarios/alex-v2/` with 12-month span (calendar year)
- [ ] ~30 authored arcs covering all **8 deliberate EF patterns** (see [architecture doc](../../docs/architecture/executive-function-support-benchmark.md#alex-v2--deliberate-ef-arcs))
- [ ] Each arc includes: timeline evidence, obligation/window truth, support contract, ≥1 checkpoint where attention ≠ next_action
- [ ] Persona traits author-side only; every arc tags `support_challenges` in ground truth
- [ ] README + `scenario.yaml` version immutability rules match alex-v1 conventions

### Eight EF patterns (minimum one arc each)

1. Initiation support — knows what to do, doesn’t start
2. Ambiguous giant task — decomposition
3. Hyperfocus / wrong-task persistence
4. Interruption and resumption
5. Time blindness / transition (e.g. 14:35 → meeting 15:00)
6. Boring recurring admin over 12 months (learn drift without shaming)
7. Working-memory disappearance (obligation + noise + 8-day silence)
8. Avoided communication (phone-call avoidance → online booking link)

## Test plan

- Scenario validator passes full alex-v2 package
- Spot-check: every support contract validates against v0 schema
- Deterministic double-load byte stability

## Privacy constraints

- Fictional content only; no Private paths or real correspondence
