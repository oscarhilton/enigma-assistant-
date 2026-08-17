# V2-EF-01 — Support contract design freeze

> **Superseded by [R01](../reasoning/R01-scenario-truth-catalogue.md)** — alex-v1
> v0.2.1 evaluator correction ships `support_contracts.yaml`, loader, and merged
> `load_evaluation_truth()`.

| Field | Value |
| --- | --- |
| Status | `superseded` |
| Branch | `ticket/R01-scenario-truth-catalogue` |
| Domain | `demo-scenario` + `demo-evaluation` (schema only) |

## Package boundary (hard)

- May edit: `docs/architecture/executive-function-support-benchmark.md`, `docs/architecture/eval-stubs/**`, `docs/architecture/alex-v1-support-challenge-catalogue.yaml`, `docs/adr/011-*.md`
- May edit: `packages/evaluation/src/personal_enigma/evaluation/support_contract.py` (loader/validator stub only — no scoring)
- May edit: `packages/evaluation/tests/test_support_contract_schema.py`
- Must not edit: `packages/attention/**`, `scenarios/alex-v1/**` (immutable), full alex-v2 timeline (V2-EF-02)

## Hard depends

- D06 (ground-truth patterns)
- [ADR-011](../../docs/adr/011-observable-support-challenges-only.md) accepted

## Soft depends (~)

- D07 (report field names)

## Unlocks / enhances

- [V2-EF-02](./V2-EF-02-ef-arc-authoring.md) arc authoring
- [EF-01](../demo-evaluation/EF-01-support-fitness-evaluator.md) scoring
- [D14](../demo-evaluation/D14-llm-judge-benchmark.md) structured output contract

## Non-goals

- Runtime Next Action generation in Enigma Core
- Modifying alex-v1 released ground truth
- ADHD / diagnostic labels in any schema field

## Acceptance criteria

- [ ] JSON Schema `support_contract.v0.json` reviewed and version-pinned
- [ ] Pydantic loader validates example fixtures; rejects diagnostic label fields
- [ ] On-disk layout documented: `ground_truth/support_contracts.yaml` for alex-v2
- [ ] Alex v1 retrospective catalogue checked in (`alex-v1-support-challenge-catalogue.yaml`)
- [ ] Architecture doc cross-links ADR-011, D06, D07, pipeline overview

## Test plan

- Valid + invalid YAML fixtures for support contracts
- Assert loader output never imported from simulation ingest paths
- Schema enum covers v1 + v2 challenge tags

## Privacy constraints

- Support contracts evaluator-only; absent from SyntheticMailSource and attention payloads
