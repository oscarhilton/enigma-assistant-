# R02 — Freeze Arm A (immutable control)

| Field | Value |
| --- | --- |
| Status | `todo` |
| Branch | `ticket/R02-freeze-arm-a` |
| Domain | `demo-evaluation` |

## Package boundary (hard)

- May edit: `packages/evaluation/src/personal_enigma/evaluation/observations.py` (CheckpointSnapshot, AttentionCandidateObservation, NextActionObservation)
- May edit: `packages/evaluation/src/personal_enigma/evaluation/checkpoint_runner.py` (create)
- May edit: `packages/evaluation/fixtures/checkpoints/alex-v1-checkpoints.yaml`, `packages/evaluation/fixtures/baselines/arm-a/**`
- May edit: `packages/evaluation/tests/test_checkpoint_runner.py`
- Must not edit: `packages/attention/**` ranking logic, `scenarios/alex-v1/timeline/**`, `packages/reasoning/**`

## Hard depends

- [R01](./R01-scenario-truth-catalogue.md) (trustworthy evaluation truth)

## Soft depends (~)

- D05 (simulation engine — if full pipeline snapshots needed later)

## Unlocks / enhances

- [R03](./R03-llm-judge.md) — identical inputs for Arm B
- [R06](./R06-privacy-ablation.md) — frozen checkpoint context
- Deterministic heuristic baseline with CI checksums

## Non-goals

- Changing HeuristicAttentionEngine ranking during the gate (observe, don't fix)
- Arm B LLM wiring (R03)
- Full demo pipeline replay (start with obligation-derived heuristic snapshots; extend if needed)

## Acceptance criteria

- [ ] **15–25 checkpoint instants** defined in `fixtures/checkpoints/alex-v1-checkpoints.yaml` (critical due, quiet periods, noise-heavy, dual conflicts e.g. 2026-01-21T13:30)
- [ ] `CheckpointSnapshot` captures: surfaced alerts, suppressed candidates, full candidate set, optional next_action, memory state, retrieval hits
- [ ] `checkpoint_runner.py` builds snapshots from `EvaluationTruth` + `HeuristicAttentionEngine`
- [ ] Frozen JSON under `fixtures/baselines/arm-a/<checkpoint_id>.json` + `manifest.json` with sha256 checksums
- [ ] Manifest records git commit + alex-v1 version
- [ ] `verify_arm_a_integrity()` detects tampered baselines

## Test plan

- Deterministic re-run at one checkpoint → identical snapshot hash
- Manifest checksum stable across CI runs
- Default checkpoint schedule covers brunch + expenses + token dual-conflict instants

## Privacy constraints

- Snapshots are Demo Mode artefacts only; no Private storage roots or HMAC material
- Baselines never embed support contract YAML — only derived observation state

## Notes

- Arm A is **frozen** after merge — R03/R06 must consume identical candidate/evidence/clock/memory inputs
- Architecture: [reasoning-value-gate.md](../../docs/demo/reasoning-value-gate.md)
