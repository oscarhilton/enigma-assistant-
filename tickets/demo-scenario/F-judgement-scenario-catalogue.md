# F — Judgement scenario catalogue (MUST_SURFACE / MUST_SUPPRESS)

| Field | Value |
| --- | --- |
| Status | `todo` |
| Branch | `ticket/F-judgement-scenario-catalogue` (or sibling critical-obligation branch) |
| Domain | `demo-scenario` |

## Package boundary (hard)

- May edit: `scenarios/alex-v1/ground_truth/**`, feature scenario ground truth as needed
- May edit: scenario docs / attention-window checkpoints for whole-checkpoint eval (e.g. Wed 21 Jan noon)
- Must **not** edit: `packages/evaluation/llm_judge/**` (owned by Judge harness)
- Must **not** fight parallel Judge-harness PRs on shared YAML without coordinating

## Hard depends

- D06 ground-truth models
- D08a Alex spine

## Soft depends (~)

- [F-llm-judge-harness](../demo-evaluation/F-llm-judge-harness.md) — scoring consumes labels; harness can ship with frozen fixtures first

## Unlocks / enhances

- Arm A/B whole-checkpoint metrics (MUST_SURFACE recall, MUST_SUPPRESS violations)
- Parents/brunch as ideal first labelled case ([attention-surface.md](../../docs/architecture/attention-surface.md))

## Non-goals

- LLM transport or Judge schema
- Shadow Mode labels for real users

## Acceptance criteria

- [ ] Checkpoint-oriented labels: MUST_SURFACE / MUST_SUPPRESS (and critical rank expectations) for at least parents/brunch + token-audit style items
- [ ] Document clock(s) used for whole-checkpoint eval
- [ ] No ground-truth fields leaked into synthetic source payloads
- [ ] Coordinate with Judge harness: do not overwrite harness fixtures; export stable obligation / evidence IDs

## Test plan

- Ground-truth loader accepts new fields or companion YAML
- Isolation: source adapters never see MUST_* labels

## Privacy constraints

- Evaluator-only labels; Demo root only

## Notes

- Soft-dep sibling of the LLM Judge benchmark. Prefer additive catalogue commits; leave TODO pointers in harness docs until IDs stabilize.
- Design: [reasoning-llm-benchmark.md](../../docs/architecture/reasoning-llm-benchmark.md)
