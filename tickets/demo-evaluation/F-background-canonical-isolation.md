# Feature scenario — background-canonical-isolation

| Field | Value |
| --- | --- |
| Status | `done` |
| Domain | `demo-evaluation` |
| Related | D06, D04, D08c |
| Branch | `ticket/F-correctness-wave` |
| Path | `scenarios/feature/background-canonical-isolation/` |

## Intent

External ground-truth metadata (`signal_class`, `expected_attention`) is demonstrably unavailable to Enigma / `SyntheticMailSource`.

## Package boundary

- `scenarios/feature/background-canonical-isolation/**`
- May edit: `packages/evaluation/tests/`, `packages/simulation/tests/`

## Acceptance

- [x] Automated assertion: dumped mail items lack evaluator-only keys
- [x] GroundTruthStore path remains separate from ingest
