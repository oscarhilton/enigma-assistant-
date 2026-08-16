# F — LLM Judge privacy ablation (raw vs PERSON_*)

| Field | Value |
| --- | --- |
| Status | `todo` |
| Branch | `ticket/F-llm-judge-privacy-ablation` |
| Domain | `demo-evaluation` |

## Package boundary (hard)

- May edit: `packages/evaluation/src/personal_enigma/evaluation/llm_judge/**` (ablation arm only)
- May add Demo-only fixtures under `packages/evaluation/fixtures/llm_judge/ablation/**`
- Must **not** run against Private Mode storage or real user exports
- Must **not** enable raw arm in product/runtime paths

## Hard depends

- [F-llm-judge-harness](./F-llm-judge-harness.md)
- M03 / M04 transform + privacy invariants

## Soft depends (~)

- [F-llm-judge-record-replay](./F-llm-judge-record-replay.md) for offline comparison reports

## Unlocks / enhances

- Evidence whether PERSON_* transform costs Judge quality on fictional Alex
- Reinforces ADR-011 production invariant (transformed only)

## Non-goals

- Shipping raw private payloads to hosted models in product
- Ablation on real Shadow/Private users

## Acceptance criteria

- [ ] Two arms on identical synthetic candidates: transformed PERSON_* vs raw synthetic private-shaped text (Demo fixtures only)
- [ ] Report quality delta + assert production harness refuses raw by default
- [ ] Privacy violations on transformed arm remain 0
- [ ] Docs state fictional Alex only

## Test plan

- Transformed path passes privacy gate; raw path is opt-in eval-only and never default
- Fixture comparison smoke (replay, not live CI)

## Privacy constraints

- Ablation raw payloads stay out of default remote transmission
- No Private Mode data

## Notes

- [reasoning-llm-benchmark.md](../../docs/architecture/reasoning-llm-benchmark.md) · [ADR-011](../../docs/adr/011-llm-structured-judgement.md)
