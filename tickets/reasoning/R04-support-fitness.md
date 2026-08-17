# R04 — Support fitness scoring

> **Absorbs:** [EF-01](../demo-evaluation/EF-01-support-fitness-evaluator.md) (D07 support fitness extension)

| Field | Value |
| --- | --- |
| Status | `todo` |
| Branch | `ticket/R04-support-fitness` |
| Domain | `demo-evaluation` |

## Package boundary (hard)

- May edit: `packages/evaluation/src/personal_enigma/evaluation/metrics/support_fitness.py` (create)
- May edit: `packages/evaluation/src/personal_enigma/evaluation/runner.py`, `report.py` (support fitness sections)
- May edit: `packages/evaluation/tests/test_support_fitness.py`
- Must not edit: `packages/attention/**`, `scenarios/alex-v1/timeline/**`

## Hard depends

- [R01](./R01-scenario-truth-catalogue.md) (support contracts loaded)

## Soft depends (~)

- [R02](./R02-freeze-arm-a.md) (checkpoint snapshots for integration tests)
- [R03](./R03-llm-judge.md) (LLM structured output arm)

## Unlocks / enhances

- [R05](./R05-failure-attribution.md) per-checkpoint pass/fail matrix
- [R07](./R07-reasoning-value-gate-report.md) exit gate metrics
- Second benchmark dimension alongside attention recall

## Non-goals

- Generating next actions inside Enigma runtime ([N01](../next-action/N01-scorer-stub.md) waits)
- LLM-as-judge semantic similarity (deterministic token match first)
- Persona-trait-based scoring

## Acceptance criteria

- [ ] **Attention accuracy** metrics: critical recall, suppression accuracy, top-3 critical recall, timing accuracy (window hit)
- [ ] **Support fitness** metrics: actionability, task-size fit, friction reduction, context fit, repetition penalty, non-nagging (`poor_actions` match)
- [ ] Dual checkpoint scoring: Attention and NextAction scored **independently** at each instant
- [ ] Pass/fail matrix when attention correct but next_action wrong (and vice versa)
- [ ] `enigma-eval` report JSON/Markdown includes support fitness section when contracts present
- [ ] december-expenses: `gather_receipts` passes; `restate_deadline_only` fails
- [ ] Backward compatible when no support contracts present

## Test plan

- Feature scenario with minimal support contract → report fields populated
- Known good vs poor action tokens → pass/fail with reason codes
- Brunch arc — attention pass independent of next-action score
- Attention-only run (no contracts) → backward compatible report

## Privacy constraints

- Support contracts never logged to external surfaces; Demo root only
- Scorer reads evaluator-only truth — never emits challenge tags to remote models

## Notes

- Architecture: [executive-function-support-benchmark.md](../../docs/architecture/executive-function-support-benchmark.md)
- Supersedes [EF-01](../demo-evaluation/EF-01-support-fitness-evaluator.md)
