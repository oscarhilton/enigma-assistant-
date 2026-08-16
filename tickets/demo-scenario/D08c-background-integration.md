# D08c — Background integration

| Field | Value |
| --- | --- |
| Status | `todo` |
| Branch | `ticket/D08c-background-integration` |
| Domain | `demo-scenario` / `demo-simulation` |
| Parent | [D08](./D08-canonical-alex.md) |

## Package boundary (hard)

- May edit: scenario `background.yaml` / profile wiring for alex-v1
- May edit: corpus → `CorpusBackgroundStream` → `SyntheticMailSource` merge
- May edit: evaluation A/B hooks for storyline recall under noise
- Must not: ship Enron/SpamAssassin into public Demo profiles

## Hard depends

- D08b corpus pipeline
- D05 timeline merge
- D06 signal classes
- D07 baseline metrics

## Soft depends (~)

- Feature scenarios `background-basic`, `background-canonical-isolation`

## Unlocks / enhances

- D08d noise layer
- Product compression narrative (D12)

## Non-goals

- Full canonical 5k profile (D08e)
- Generated newsletter templates (D08d)

## Acceptance criteria

- [ ] Canonical + background merge into one chronological mailbox
- [ ] Enigma cannot observe `signal_class` / background labels
- [ ] Critical canonical recall does not materially degrade vs spine-only (measure; target ≤1 pp)
- [ ] Seeded reset reproduces identical background traffic
- [ ] Background contacts remain disjoint from canonical person namespaces

## Test plan

- A/B eval: alex spine only vs spine + mini/demo background
- Isolation test: ground-truth metadata absent from source payloads

## Privacy constraints

- Evaluator-only classification; `.example` domains only in public Demo
