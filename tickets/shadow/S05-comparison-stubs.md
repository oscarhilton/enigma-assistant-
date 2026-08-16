# S05 — Comparison stubs (seven evaluation goals)

| Field | Value |
| --- | --- |
| Status | `todo` |
| Branch | `ticket/S05-comparison-stubs` |
| Domain | `shadow` |
| Baseline | `v0.2.0-demo` |

## Package boundary (hard)

- May edit: `packages/evaluation/**` for Shadow comparison stub types / placeholders
- May edit: `docs/architecture/shadow-mode.md`, `docs/architecture/shadow-mode-questions.md`
- May edit: tests under `packages/evaluation/tests/**`
- Must not edit: Demo scenario packages, F-* gate thresholds (frozen), Shadow storage roots, Gmail OAuth

## Hard depends

- S01 `done`
- S04 `done` (~ soft if stubs are types-only)

## Soft depends (~)

- S04 shadow attention log
- Phase 2.5 exit report shape

## Unlocks / enhances

- Structured place to measure the seven questions without claiming answers yet

## Non-goals

- Implementing full longitudinal user studies
- Importing Demo DBs into Shadow
- Changing Demo F-* science gates
- Product claims that Shadow “matches Alex”

## Acceptance criteria

- [ ] Stub metric / journal interfaces exist for each of the seven evaluation goals in [shadow-mode-questions.md](../../docs/architecture/shadow-mode-questions.md)
- [ ] Stubs consume Shadow attention-log shapes and optional *exported* Demo report numbers — never Demo storage roots
- [ ] Documented that stubs are goals, not shipped answers
- [ ] CI runs a smoke test that stubs construct without I/O into Demo paths

## Test plan

- Construct stub bundle for all seven goals
- Refuse any helper that accepts a Demo storage root as Shadow input

## Privacy constraints

- Comparison artefacts must not embed raw private mail bodies destined for remote logs
