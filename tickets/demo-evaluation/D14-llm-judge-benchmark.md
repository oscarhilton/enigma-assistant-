# D14 — LLM judge benchmark (structured attention + next_action)

| Field | Value |
| --- | --- |
| Status | `todo` |
| Branch | `ticket/D14-llm-judge-benchmark` |
| Domain | `demo-evaluation` |

## Package boundary (hard)

- May edit: `packages/evaluation/src/personal_enigma/evaluation/llm_benchmark.py` (create)
- May edit: `packages/evaluation/tests/test_llm_benchmark.py`
- May edit: `packages/reasoning/**` only for structured output schema wiring if required
- Must not edit: `packages/attention/**` ranking logic, `scenarios/alex-v1/**`

## Hard depends

- D07, D11 (deterministic replay)
- [V2-EF-01](../demo-scenario/V2-EF-01-support-contract-design.md)
- M05 (PAYG reasoning provider)

## Soft depends (~)

- [EF-01](./EF-01-support-fitness-evaluator.md) (shared scorer types)
- [V2-EF-02](../demo-scenario/V2-EF-02-ef-arc-authoring.md)

## Unlocks / enhances

- Arm B/C model comparison on **both** attention and support fitness
- Provider regression with structured outputs (no chain-of-thought)

## Non-goals

- Sending ground truth or support contracts to the model
- Hidden chain-of-thought capture or scoring
- Private Mode automatic LLM ranking

## Acceptance criteria

- [ ] Benchmark arms return JSON: `attention` + `next_action` (title, estimated_minutes, effort, why_this_now)
- [ ] Deterministic evaluator scores model output against scenario allowed support actions ([support_contract.v0.json](../../docs/architecture/eval-stubs/support_contract.v0.json))
- [ ] Replay mode: recorded provider responses ([D11](./D11-replay-provider.md)) for CI determinism
- [ ] Privacy: transformed context only; no persona traits or evaluator tags in prompt
- [ ] Report compares arms on world-model proxies + attention + support fitness

### Structured output shape (illustrative)

```json
{
  "attention": {
    "item_id": "string",
    "behaviour": "surface|suppress",
    "priority": 1
  },
  "next_action": {
    "title": "string",
    "estimated_minutes": 10,
    "effort": "light",
    "why_this_now": "string"
  }
}
```

## Test plan

- Mock provider fixture → structured parse + score
- Invalid JSON / schema drift → actionable validation errors
- Assert prompts exclude `support_challenges` and `poor_actions`

## Privacy constraints

- Select → transform → transmit last; no raw Notes or PrivatePerson in benchmark prompts
- Remote inference disable-able; local heuristic arm remains baseline

## Notes

- Relates to PR #74 direction (LLM judge benchmark) — implement on this ticket
- Architecture: [executive-function-support-benchmark.md](../../docs/architecture/executive-function-support-benchmark.md#two-independent-checkpoint-questions)
