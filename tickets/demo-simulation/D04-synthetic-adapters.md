# D04 — Synthetic source adapters

| Field | Value |
| --- | --- |
| Status | `done` (merged #28) |
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

- [x] Each adapter implements the same `DataSource` (or equivalent) contract as production sources
- [x] Outputs are canonical private records only: messages, calendar events, reminders, notes, persons
- [x] Adapters stop at the **source layer** — Enigma discovers obligations downstream
- [x] Wired only through `DemoEnvironment` source registry (never registered on Private)
- [x] Module paths are not under `personal_enigma.ingestion.sources`

### Amendment — multi-stream mail (plan §85)

- [x] `SyntheticMailSource` accepts streams: `CanonicalScenarioStream` | `CorpusBackgroundStream` | `GeneratedNoiseStream` (scaffold)
- [ ] Full `CorpusBackgroundStream` population from sanitised corpus (D08c)
- [x] Merged mailbox exposes ordinary mail fields only — never `signal_class` / importance labels from ground truth

## Test plan

- Round-trip: scenario snippet → synthetic source `get_changes` → domain record shapes
- Demo environment rejects if a synthetic adapter is swapped for a real class
- No adapter test constructs `Obligation` / `AttentionItem` directly
- Multi-stream merge hides evaluator metadata on emitted messages

## Privacy constraints

- Synthetic sources must not read Private storage or real credentials
- Corpus adapters must not emit Enigma obligation/attention types
