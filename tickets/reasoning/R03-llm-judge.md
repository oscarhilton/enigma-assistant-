# R03 — Arm B: LLM judge

> **Absorbs:** [D14](../demo-evaluation/D14-llm-judge-benchmark.md) (structured attention + next_action benchmark)

| Field | Value |
| --- | --- |
| Status | `todo` |
| Branch | `ticket/R03-llm-judge` |
| Domain | `demo-evaluation` + `reasoning` (transport wiring only) |

## Package boundary (hard)

- May edit: `packages/evaluation/src/personal_enigma/evaluation/llm_benchmark.py` (create)
- May edit: `packages/evaluation/tests/test_llm_benchmark.py`
- May edit: `packages/reasoning/**` only for structured output schema wiring if required
- Must not edit: `packages/attention/**` ranking logic, `scenarios/alex-v1/timeline/**`

## Hard depends

- [R02](./R02-freeze-arm-a.md) (frozen Arm A snapshots)
- D07, D11 (deterministic replay)
- M05 (PAYG reasoning provider)

## Soft depends (~)

- [R04](./R04-support-fitness.md) (shared scorer types)

## Unlocks / enhances

- [R05](./R05-failure-attribution.md) A/B disagreement inputs
- [R06](./R06-privacy-ablation.md) LLM benchmark harness
- Arm B/C model comparison on attention + support fitness

## Non-goals

- Sending ground truth or support contracts to the model
- Hidden chain-of-thought capture or scoring
- Private Mode automatic LLM ranking
- Changing heuristic Arm A behaviour

## Acceptance criteria

- [ ] Benchmark arms: **Arm A** = heuristic on frozen `CheckpointSnapshot`; **Arm B** = `PaygReasoningService` + structured JSON
- [ ] Structured output schema:

```json
{
  "attention": { "item_id": "...", "behaviour": "surface|suppress", "priority": 1 },
  "next_action": { "title": "...", "estimated_minutes": 10, "effort": "light", "why_this_now": "..." }
}
```

- [ ] **Same snapshot inputs** for both arms — no extra evidence for Arm B
- [ ] Pipeline: select → `DefaultEnigmaTransformer` → `assert_remote_safe` → transport (`ReplayPaygTransport` in CI)
- [ ] Replay mode: recorded provider responses (D11) for CI determinism
- [ ] Prompts exclude contracts, persona traits, and `support_challenges`

## Test plan

- Mock/replay fixture → structured parse + score
- Invalid JSON / schema drift → actionable validation errors
- Assert prompts exclude `support_challenges`, `poor_actions`, persona fields
- Remote inference disable-able; local heuristic arm remains baseline

## Privacy constraints

- Select → transform → transmit last; no raw Notes or PrivatePerson in benchmark prompts
- Only `TransformedContext` (or equivalent sanitised payload) crosses the wire
- Demo Mode never shares Private storage roots ([ADR-005](../../docs/adr/005-demo-private-storage-roots.md))

## Notes

- Architecture: [reasoning-value-gate.md](../../docs/demo/reasoning-value-gate.md)
- Supersedes [D14](../demo-evaluation/D14-llm-judge-benchmark.md)
