# D05 — Event simulation engine

| Field | Value |
| --- | --- |
| Status | `todo` |
| Branch | `ticket/D05-event-engine` |
| Domain | `demo-simulation` |

## Package boundary (hard)

- May edit: `packages/simulation/src/personal_enigma/simulation/engine.py`, `events.py`, `checkpoints.py`, related tests
- Must not edit: scenario corpus YAML (D8), eval metrics (D7), web UI (D10)

## Hard depends

- D1, D2, D3

## Soft depends (~)

- D4

## Unlocks / enhances

- Enables D7 batch eval and D10 timeline controls

## Non-goals

- Provider replay recording (D11)
- Full demo UI (D10)

## Acceptance criteria

- [ ] Timeline load + event emission for `at <= simulated now`
- [ ] Advance one event, advance day, batch run, reset
- [ ] One month of Alex (or fixture subset) replays identically twice

## Test plan

- Determinism: same seed + scenario → identical emitted event ids/timestamps
- Reset clears demo storage under the demo root only

## Privacy constraints

- Engine must bind to Demo storage root only ([ADR-005](../../docs/adr/005-demo-private-storage-roots.md))
