# POLARIS-SEARCH-05 — Executive motifs and strategy scripts

| Field | Value |
| --- | --- |
| Status | `future` |
| Branch | `ticket/POLARIS-SEARCH-05-executive-motifs` |
| Domain | `polaris` |

## Package boundary (hard)

- May edit: motif classifiers + strategy-script priors (move ordering / prune hints), tests, docs pointers
- Must not edit: C12 Life Script YAML product tests; `persona.yaml` as runtime input; person records; UI

## Hard depends

- [POLARIS-SEARCH-04](./POLARIS-SEARCH-04-receding-horizon-search.md) `done`

## Soft depends (~)

- [ALEX-EVAL-01](../demo-evaluation/ALEX-EVAL-01-life-positions.md) (~ labels)
- [ADR-024](../../docs/adr/024-shareable-recipes-procedure-never-personal-state.md) recipes as later procedure binding

## Unlocks / enhances

- Faster 04 on recurring Alex positions; ALEX-EVAL-02 quality

## Non-goals

- Personality profiling / user embeddings as priors
- Renaming or overwriting C12 Life Scripts
- ADHD or diagnostic flags in runtime
- `ALEX_BIOGRAPHY.md`

## Acceptance criteria

- [ ] Motifs are **position classes** ([ADR-047](../../docs/adr/047-executive-motifs-and-search-efficiency.md)): at least double-booked, waiting-on-someone, deadline compression, blocked-task, low-energy mismatch
- [ ] Strategy scripts are inspectable move-ordering / prune **priors** over legal moves only
- [ ] Transposition-style reuse keys `DecisionPosition`; stale evidence invalidates reuse
- [ ] Quiescence triggers for forcing motifs (conflict, deadline cliff)
- [ ] C12 YAML remains product-acceptance; this ticket does not add architecture-named utterances to scripts
- [ ] Example: `dentist-critique-overlap` classified `double_booked` → prior prefers `resolve_calendar_conflict` before deep work — still legal-only

## Exit conditions

Done when 04 with scripts enabled is at least as correct as 04 without them on the Alex motif fixtures, and no person-level trait is read from `persona.yaml`.

## Test plan

- Motif classification on the five example families (fixtures, not HF)
- Negative: `persona.yaml` `admin_avoidance` must not be an engine input
- Reuse: identical position twice → cache hit; change blocker evidence → miss

## Privacy constraints

- Motifs are not written onto the user record
- Support-challenge tags stay evaluator-only when used in tests
