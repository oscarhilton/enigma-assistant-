# F — Reasoning LLM arms C–E (later)

| Field | Value |
| --- | --- |
| Status | `todo` |
| Branch | `ticket/F-llm-arms-c-e` |
| Domain | `demo-evaluation` |

## Package boundary (hard)

- May edit: `packages/evaluation/**` for Discovery / Hybrid / Oracle arm runners
- Must **not** start until Arm B Judge metrics are interpretable
- Must **not** give Oracle labels to runtime attention (eval-only)

## Hard depends

- [F-llm-judge-harness](./F-llm-judge-harness.md) done with baseline Arm B reports
- Soft preferred: [F-judgement-scenario-catalogue](../demo-scenario/F-judgement-scenario-catalogue.md)

## Soft depends (~)

- [F-llm-judge-record-replay](./F-llm-judge-record-replay.md)
- [F-llm-judge-privacy-ablation](./F-llm-judge-privacy-ablation.md)

## Unlocks / enhances

- Full A–E comparison matrix in [reasoning-llm-benchmark.md](../../docs/architecture/reasoning-llm-benchmark.md)

## Non-goals

- Replacing Arm B as the first LLM experiment
- Product wiring of Discovery without policy authority

## Acceptance criteria

- [ ] Arm C — LLM Discovery: model may propose candidates from a larger sanitised window; code still validates evidence + policy
- [ ] Arm D — Hybrid: Judge only on contested mid-band; measure cost vs Arm B
- [ ] Arm E — Synthetic Oracle: eval-time ground truth only; never transmitted as model context in product configs
- [ ] Same whole-checkpoint metrics + 5-run variance protocol as Arm B

## Test plan

- Offline fixtures per arm
- Oracle arm cannot be selected when `ENIGMA_ENVIRONMENT=private` / Shadow product paths

## Privacy constraints

- TransformedContext only for any hosted call
- Oracle labels stay evaluator-side ([ADR-011](../../docs/adr/011-llm-structured-judgement.md))

## Notes

- Do not claim this ticket until Judge-first results justify the extra variables.
