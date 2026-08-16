# F — LLM Judge record / replay for CI

| Field | Value |
| --- | --- |
| Status | `todo` |
| Branch | `ticket/F-llm-judge-record-replay` |
| Domain | `demo-evaluation` |

## Package boundary (hard)

- May edit: `packages/evaluation/src/personal_enigma/evaluation/llm_judge/**`
- May edit: `packages/evaluation/fixtures/llm_judge/**`
- May reuse D11 recording helpers in `packages/reasoning/replay_transport.py` without weakening privacy gates
- Must **not** call live OpenAI in default CI
- Must **not** record Private Mode sessions into the repo

## Hard depends

- [F-llm-judge-harness](./F-llm-judge-harness.md)
- D11 replay provider patterns

## Soft depends (~)

- [F-judgement-scenario-catalogue](../demo-scenario/F-judgement-scenario-catalogue.md)

## Unlocks / enhances

- Deterministic Arm B metrics in PR CI (5-run variance = 0 under replay)
- Developer live capture → checked-in fixtures

## Non-goals

- Arms C–E recording formats
- Replacing privacy gates

## Acceptance criteria

- [ ] Record sanitised Judge request/response pairs (TransformedContext / structured JSON only)
- [ ] Replay by content hash of frozen candidate+evidence payload
- [ ] CI job uses replay only; live capture is developer-documented
- [ ] Mismatch policy explicit (fail vs refuse)

## Test plan

- Record → replay → identical judgements
- `force_offline` never opens network even if live transport configured

## Privacy constraints

- Recordings must never contain `PrivatePerson` fields or wholesale Notes
- Demo fixtures only

## Notes

- Extends D11 ideas to Judge schema; see [reasoning-llm-benchmark.md](../../docs/architecture/reasoning-llm-benchmark.md)
