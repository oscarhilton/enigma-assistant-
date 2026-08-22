# ALEX-EVAL-02 — Planner tournament

| Field | Value |
| --- | --- |
| Status | `future` |
| Branch | `ticket/ALEX-EVAL-02-planner-tournament` |
| Domain | `demo-evaluation` |

## Package boundary (hard)

- May edit: `packages/evaluation/**` tournament runner, reports under `docs/reports/` if an exemplar is the package convention, tests
- Must not edit: live user output path; `packages/attention` policy; scenarios timeline

## Hard depends

- [ALEX-EVAL-01](./ALEX-EVAL-01-life-positions.md) `done`
- [POLARIS-SEARCH-04](../polaris/POLARIS-SEARCH-04-receding-horizon-search.md) `done`

## Soft depends (~)

- POLARIS-SEARCH-05 (ordering may change scores; tournament must pin planner versions)
- N01 stub as the baseline “current” planner
- BRAIN-01 traces as artefacts (~)

## Unlocks / enhances

- POLARIS-SEARCH-06 / 07 evidence bar

## Non-goals

- LLM-as-judge of a life (R03 is a different gate)
- Declaring production promotion
- One exact move as the only pass criterion

## Acceptance criteria

- [ ] Same Alex positions, multiple planners (at least: current Next Action stub / heuristic, Polaris search)
- [ ] Score **invariants** (must_consider hit, must_not_recommend avoided, legal ceiling honoured, REST legal, `ranking_changed_by` when present, `coverage_adequate: false` never treated as free time)
- [ ] Measurable regression/improvement: published table per planner version (pass rate by motif **and** by lens ablation)
- [ ] Shadow-safe: tournament reads compiled positions + planner functions; **no** Private storage; **no** Demo→Shadow DB copy
- [ ] Deterministic given pin (clock + planner git/version + position id)
- [ ] Failure artefact includes trace id / ply-0 / violated invariant / which lenses were attributed — not CoT
- [ ] Do not score a universal life quality of Alex

## Exit conditions

Done when 06/07 can cite a tournament report format and CI runs a mini-suite (even 2 positions) on every polaris change.

## Test plan

- Mini tournament on dentist-critique + december-expenses + token-fuel fixtures
- Cheating planner that recommends `manufacture_urgency` fails
- Root isolation: helpers reject Private DB URLs

## Privacy constraints

- Evaluator-only labels never injected into planner prompts ([ADR-012](../../docs/adr/012-reasoning-value-gate-decision.md))
- Alex dummy only
