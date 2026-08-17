# R01 — Scenario truth catalogue

> **Absorbs:** [V2-EF-01](../demo-scenario/V2-EF-01-support-contract-design.md) (support contract schema + alex-v1 truth authoring)

| Field | Value |
| --- | --- |
| Status | `todo` |
| Branch | `ticket/R01-scenario-truth-catalogue` |
| Domain | `demo-scenario` + `demo-evaluation` |

## Package boundary (hard)

- May edit: `scenarios/alex-v1/ground_truth/**` (additive only — no timeline edits)
- May edit: `scenarios/alex-v1/scenario.yaml` (version bump to `0.2.1`), `scenarios/alex-v1/README.md`
- May edit: `packages/evaluation/src/personal_enigma/evaluation/support_contract.py`, `evaluation_truth.py`
- May edit: `packages/evaluation/tests/test_support_contract*.py`, `test_evaluation_truth.py`
- May edit: `docs/architecture/alex-v1-support-challenge-catalogue.yaml` (migrate content into machine-scorable YAML)
- Must not edit: `scenarios/alex-v1/timeline/**`, `packages/attention/**`, `packages/reasoning/**`

## Hard depends

- D06 (ground-truth models)
- [ADR-011](../../docs/adr/011-observable-support-challenges-only.md) accepted

## Soft depends (~)

- D07 (report field names)

## Unlocks / enhances

- [R02](./R02-freeze-arm-a.md) Arm A baseline inputs
- [R04](./R04-support-fitness.md) support contract scoring
- Trustworthy alex-v1 benchmark (brunch, expenses, dentist regressions)

## Non-goals

- Timeline or content body edits (evaluator correction release only)
- Runtime Next Action generation
- Alex v2 arc authoring (stretch — [V2-EF-02](../demo-scenario/V2-EF-02-ef-arc-authoring.md))

## Acceptance criteria

- [ ] **alex-v1 v0.2.1** evaluator correction: bump `scenario.yaml` version; document immutability rules in README
- [ ] `ground_truth/support_contracts.yaml` — all intentional arcs with `MUST_SURFACE` / `MAY_SURFACE` / `CONTEXT_ONLY` / `MUST_SUPPRESS`, windows, resolution events, `good_next_actions` / `poor_actions`
- [ ] Expanded obligations (brunch, december-expenses, elena-dinner-wine, dentist, token, Sam, social, etc.)
- [ ] Expanded `attention_windows.yaml` / noise signals — PrizeVault junk, machine notifications, newsletters → `MUST_SUPPRESS`
- [ ] `support_contract.py` loader validates against [support_contract.v0.json](../../docs/architecture/eval-stubs/support_contract.v0.json)
- [ ] `load_evaluation_truth()` merges D06 ground truth + support contracts
- [ ] Content migrated from [alex-v1-support-challenge-catalogue.yaml](../../docs/architecture/alex-v1-support-challenge-catalogue.yaml) into machine-scorable YAML
- [ ] Dual checkpoint at **2026-01-21T13:30** — attention ≠ next_action expectations documented

### Arc coverage (minimum)

Brunch (parents), december-expenses, token inventory, Q1 roadmap, checkout, Sam reply, social scheduling, dentist, newsletters, PrizeVault junk, machine notifications, quiet periods.

## Test plan

- Schema validation: valid + invalid support contract fixtures
- All 12+ arcs load; brunch obligation present with `MUST_SURFACE` window
- Suppress arcs never expect attention surfacing
- Assert support contracts absent from simulation ingest / attention payloads

## Privacy constraints

- Support contracts and `support_challenges` are **evaluator-only** ([ADR-011](../../docs/adr/011-observable-support-challenges-only.md))
- Never ingested by Enigma runtime or LLM prompts
- Demo Mode never shares Private storage roots ([ADR-005](../../docs/adr/005-demo-private-storage-roots.md))

## Notes

- Architecture: [reasoning-value-gate.md](../../docs/demo/reasoning-value-gate.md)
- Sprint charter exit gate blocked until R01 truth is trustworthy
