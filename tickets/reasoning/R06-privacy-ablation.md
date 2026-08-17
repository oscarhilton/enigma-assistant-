# R06 — Privacy ablation

| Field | Value |
| --- | --- |
| Status | `todo` |
| Branch | `ticket/R06-privacy-ablation` |
| Domain | `demo-evaluation` + `privacy` (assertions only) |

## Package boundary (hard)

- May edit: `packages/evaluation/src/personal_enigma/evaluation/privacy_ablation.py` (create) or extend `llm_benchmark.py`
- May edit: `packages/evaluation/tests/test_privacy_ablation.py`
- May edit: `packages/evaluation/src/personal_enigma/evaluation/report.py` (ablation delta section)
- Must not edit: `packages/privacy/**` gate logic (import only), `packages/attention/**`

## Hard depends

- [R03](./R03-llm-judge.md) (LLM benchmark harness)

## Soft depends (~)

- M04 (privacy invariant tests — reference patterns)

## Unlocks / enhances

- [R07](./R07-reasoning-value-gate-report.md) privacy ablation delta row
- Quantified answer: does pseudonymisation cost 1% or 20%?

## Non-goals

- Changing privacy transform rules during ablation
- Running full-synthetic arm against real network in CI (fixture-only)
- Private Mode ablation (Demo controlled experiment only)

## Acceptance criteria

- [ ] Same LLM, same checkpoints, two context arms:
  - **Full synthetic** — raw fictional names (Alex-only controlled experiment)
  - **Transformed** — Enigma `TransformedContext` (PERSON_*, scrubbed PII)
- [ ] Report delta on attention + support fitness between arms
- [ ] Transformed arm always passes `assert_remote_safe`
- [ ] Full-synthetic arm never runs in CI against real network (replay/fixture only)
- [ ] Ablation section in gate report with numeric delta per metric family

## Test plan

- Transformed fixture → privacy gate pass
- Full vs transformed on identical checkpoint → delta computed
- CI path uses replay transport only

## Privacy constraints

- Ablation exists to measure **cost of privacy**, not to bypass it
- Transformed arm is the production-shaped path; full-synthetic is evaluator-controlled fiction only
- No Private storage roots or real correspondence in either arm

## Notes

- Architecture: [reasoning-value-gate.md](../../docs/demo/reasoning-value-gate.md)
