# EF-01 — Support fitness evaluator (D07 extension)

| Field | Value |
| --- | --- |
| Status | `todo` |
| Branch | `ticket/EF-01-support-fitness-evaluator` |
| Domain | `demo-evaluation` |

## Package boundary (hard)

- May edit: `packages/evaluation/src/personal_enigma/evaluation/**` (metrics, support scoring, report fields)
- May edit: `packages/evaluation/tests/**`
- May edit: `scenarios/*/ground_truth/support_contracts.yaml` in **feature** or **alex-v2** fixtures only
- Must not edit: `packages/attention/**`, `scenarios/alex-v1/**`

## Hard depends

- D07 (evaluation runner)
- [V2-EF-01](../demo-scenario/V2-EF-01-support-contract-design.md) support contract loader

## Soft depends (~)

- [V2-EF-02](../demo-scenario/V2-EF-02-ef-arc-authoring.md) (full arc corpus)
- [D14](./D14-llm-judge-benchmark.md) (LLM structured output arm)

## Unlocks / enhances

- Second benchmark dimension in CI reports
- Regression gates for support fitness alongside attention recall

## Non-goals

- Generating next actions inside Enigma runtime
- LLM-as-judge semantic similarity (deterministic token match first)
- Persona-trait-based scoring

## Acceptance criteria

- [ ] Metrics module: support fitness rubric (actionability, task size fit, friction reduction, timing fit, context fit, repetition penalty, non-nagging)
- [ ] Checkpoint scorer: independent **Attention** vs **NextAction** answers at contract instants
- [ ] `enigma-eval` report JSON/Markdown includes support fitness section when contracts present
- [ ] Repetition penalty detects re-surface of completed/dismissed loops in replay
- [ ] `poor_actions` match → explicit fail with reason codes

### Amendment — dual checkpoint questions

- [ ] At each `next_action_checkpoint.at`, score attention expectation and next_action expectation separately
- [ ] Document pass when attention correct but next_action wrong (and vice versa) for debugging

## Test plan

- Feature scenario with minimal support contract → report fields populated
- Known good vs poor action tokens → pass/fail
- Attention-only run (no contracts) → backward compatible report

## Privacy constraints

- Support contracts never logged to external surfaces; Demo root only

## Notes

- Architecture: [executive-function-support-benchmark.md](../../docs/architecture/executive-function-support-benchmark.md)
- Parent ticket lineage: extends [D07](./D07-evaluation-runner.md)
