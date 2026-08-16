# SE08 — Suppression Accuracy + Silent Miss Rate

| Field | Value |
| --- | --- |
| Status | `todo` |
| Branch | `ticket/SE08-silence-metrics` |
| Domain | `shadow` |
| Baseline | [shadow-silence-evaluation.md](../../docs/architecture/shadow-silence-evaluation.md) |

## Package boundary (hard)

- May edit: `packages/evaluation/**` for metric collectors
- May amend: SE03 weekly review schema docs to include silence metrics
- May edit: tests
- Must **not** change Demo F-* gate thresholds
- Must **not** edit `EnvironmentMode`

## Hard depends

- None for formula stubs + empty inputs

## Soft depends (~)

- SE04 decision log
- SE06 stratified labels
- SE07 miss reports
- SE05 adjudicated reviews (when present)
- SE03 weekly artefact
- S05 comparison stubs
- S06 exit criteria

## Unlocks / enhances

- Headline human-facing silence metrics
- Counterfactual harness baselines (SE10)

## Non-goals

- Surfacing metrics in Demo chrome
- Treating unaudited suppressions as correct

## Acceptance criteria

- [ ] **Suppression Accuracy** = `correctly_suppressed / suppressed_items_audited` (document human name “silence precision”)
- [ ] **Silent Miss Rate** = `important_missed / important_discovered_during_evaluation` (target: extremely low)
- [ ] Denominator rules documented: audited ⊆ stratified labels ∪ adjudicated mismatches ∪ mapped miss reports
- [ ] Config snapshot (windows, strata) stored with each metric emit
- [ ] Tests: fixture yields known ratios; refuse Demo ground_truth as default input

## Test plan

- Unit: 4 audited suppressions, 3 fine + 1 should-have → accuracy 0.75
- Unit: 2 important discovered, 1 miss → silent miss rate 0.5

## Privacy constraints

- Aggregates may export; item-level dumps stay on Shadow root
