# D06 — Ground truth

| Field | Value |
| --- | --- |
| Status | `done` (merged #31) |
| Branch | `ticket/D06-ground-truth` |
| Domain | `demo-evaluation` |

## Package boundary (hard)

- May edit: `packages/evaluation/src/personal_enigma/evaluation/ground_truth.py`, related tests
- May edit: `scenarios/*/ground_truth/**` schema examples (not full Alex corpus — D8)
- Must not edit: metric aggregation CLI (D7), simulation engine (D5)

## Hard depends

- D1

## Soft depends (~)

- D3

## Unlocks / enhances

- Hard-unlocks D7 automatic missed-obligation detection

## Non-goals

- Full eval report CLI (D7)
- Adversarial attack packs (D9)

## Acceptance criteria

- [x] Obligation / commitment / attention-window / memory-checkpoint ground-truth models
- [x] Loader for `ground_truth/*.yaml`
- [x] Evaluation can identify a missed obligation automatically against truth

### Amendment — signal classes (plan §85)

- [x] `ScenarioSignalClass`: `canonical` | `background` | `noise` | `adversarial`
- [ ] Per-event evaluator metadata (`signal_class`, `expected_attention`) for background/noise
- [ ] First canonical benchmark: background → `expected_attention: false`
- [x] Signal class never imported into Enigma reasoning / `SyntheticMailSource` payloads

## Test plan

- Fixture where attention missed a known critical obligation → detector flags it
- Invalid truth documents fail validation
- Assert `signal_class` absent from mail source dumps

## Privacy constraints

- Ground-truth APIs are developer-only; never on external sanitised surface
