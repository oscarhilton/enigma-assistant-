# D06 — Ground truth

| Field | Value |
| --- | --- |
| Status | `todo` |
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

- [ ] Obligation / commitment / attention-window / memory-checkpoint ground-truth models
- [ ] Loader for `ground_truth/*.yaml`
- [ ] Evaluation can identify a missed obligation automatically against truth

## Test plan

- Fixture where attention missed a known critical obligation → detector flags it
- Invalid truth documents fail validation

## Privacy constraints

- Ground-truth APIs are developer-only; never on external sanitised surface
