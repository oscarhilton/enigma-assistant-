# Feature scenario stub — background-canonical-isolation

| Field | Value |
| --- | --- |
| Status | `todo` |
| Domain | `demo-evaluation` |
| Related | D06, D04, D08c |

## Intent

External ground-truth metadata (`signal_class`, `expected_attention`) is demonstrably unavailable to Enigma / `SyntheticMailSource`.

## Acceptance

- [ ] Automated assertion: dumped mail items lack evaluator-only keys
- [ ] GroundTruthStore path remains separate from ingest
