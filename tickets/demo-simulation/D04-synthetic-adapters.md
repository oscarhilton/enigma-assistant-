# D04 — Synthetic source adapters

| Field | Value |
| --- | --- |
| Status | `todo` |
| Branch | `ticket/D04-synthetic-adapters` |
| Domain | `demo-simulation` |
| Baseline | `v0.1.0-mvp` |

## Package boundary (hard)

- May edit **only** pinned files:
  - `packages/simulation/src/personal_enigma/simulation/sources/mail.py`
  - `.../sources/calendar.py`
  - `.../sources/reminders.py`
  - `.../sources/notes.py`
  - `.../sources/contacts.py`
  - `.../sources/__init__.py`
- May edit: matching tests under `packages/simulation/tests/sources/**`
- Must not edit: `packages/ingestion/src/personal_enigma/ingestion/sources/**`
- Must not emit obligations/commitments/attention items from adapters

## Hard depends

- D01

## Soft depends (~)

- D03 (validated scenario events to read)
- D02 (event timestamps via clock)

## Unlocks / enhances

- D05 can drive real ingest path with synthetic sources
- Preserves source-layer vs world-model boundary under Demo pressure

## Non-goals

- Simulation engine scheduling (D05)
- Ground-truth comparison (D06/D07)
- Cheating via `SyntheticObligation(...)` because the scenario “says so”

## Acceptance criteria

- [ ] Each adapter implements the same `DataSource` (or equivalent) contract as production sources
- [ ] Outputs are canonical private records only: messages, calendar events, reminders, notes, persons
- [ ] Adapters stop at the **source layer** — Enigma discovers obligations downstream
- [ ] Wired only through `DemoEnvironment` source registry (never registered on Private)
- [ ] Module paths are not under `personal_enigma.ingestion.sources`

## Test plan

- Round-trip: scenario snippet → synthetic source `get_changes` → domain record shapes
- Demo environment rejects if a synthetic adapter is swapped for a real class
- No adapter test constructs `Obligation` / `AttentionItem` directly

## Privacy constraints

- Synthetic sources must not read Private storage or real credentials
