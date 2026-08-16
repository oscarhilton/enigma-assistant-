# D03 — Scenario format + validation

| Field | Value |
| --- | --- |
| Status | `done` (PR pending) |
| Branch | `ticket/D03-scenario-format` |
| Domain | `demo-scenario` |
| Baseline | `v0.1.0-mvp` |

## Package boundary (hard)

- May edit: `scenarios/**` schema docs + tiny `scenarios/feature/*` packs only
- May edit: `packages/simulation/src/personal_enigma/simulation/scenario*.py` (loader/validator; create as needed)
- May edit: `packages/simulation/tests/test_scenario_format.py`
- Must not fill `scenarios/alex-v1/` with a large life (D08)
- Must not implement synthetic `DataSource` adapters (D04) or eval metrics (D07)

## Hard depends

- D01

## Soft depends (~)

- D02 (timestamps in scenarios should be clock-relative / explicit instants)

## Unlocks / enhances

- D04 adapters consume validated scenario events
- D05 engine loads scenarios
- D06/D07 attach ground truth + metrics
- D08 fills Alex against a frozen format

## Non-goals

- Months of Alex narrative
- Producing obligations/commitments inside scenario files (world model is Enigma’s job)
- UI

## Acceptance criteria

- [x] Documented on-disk scenario package layout (manifest, timeline/events, entities, optional attacks, ground_truth hooks)
- [x] Validator rejects malformed packages with actionable errors
- [x] Tiny feature scenarios land under `scenarios/feature/` (≈5–10 events each), e.g.:
  - `commitment-basic`
  - `commitment-resolved`
  - `calendar-conflict`
  - `cross-source-merge`
  - `quiet-day`
- [x] `scenarios/alex-v1/` may keep placeholder dirs only until D08
- [x] Events describe **source-layer** evidence (mail/calendar/reminder/note/contact) — not pre-baked `Obligation` objects
- [x] Seeded RNG primitives (`scenario_rng` / `package.rng()`); alex-v1 loads deterministically

## Test plan

- Load + validate each feature scenario
- Invalid fixtures fail validation tests
- alex-v1 double-load is byte-stable; seeded RNG repeats

## Privacy constraints

- Scenario content is fictional; still treat like sensitive fixtures in CI logs (no accidental Private paths)
