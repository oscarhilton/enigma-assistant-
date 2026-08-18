# D08f-02 — February ordinary events + 0.3.0 load path

| Field | Value |
| --- | --- |
| Status | `todo` |
| Branch | `ticket/D08f-02-february` |
| Domain | `demo-scenario` |
| Parent | [D08f](./D08f-alex-six-month.md) |

## Package boundary (hard)

- May edit: `scenarios/alex-v1/timeline/2026-02/**`, `scenarios/alex-v1/content/**` (new bodies only), `scenarios/alex-v1/scenario.yaml` (version bump to 0.3.0 + span copy), `scenarios/alex-v1/README.md`
- May edit: `packages/simulation/src/personal_enigma/simulation/scenario.py` (recursive `timeline/YYYY-MM/**/*.yaml` glob), `packages/simulation/tests/test_alex_corpus.py`, `packages/simulation/tests/test_scenario_format.py`
- Must not edit: `timeline/week-*.yaml` semantics (keep as January 0.2.1 files; 0.3.0 may *also* load nested months), `packages/ingestion/**`, C11, SEC-07 attacker, `intent_router.py`, Life Script YAML ([D08f-scripts](./D08f-scripts.md))

## Hard depends

- [D08f](./D08f-alex-six-month.md) programme (layout + rule)

## Soft depends (~)

- [D08f-scripts](./D08f-scripts.md) `alex_feb12_running_late` (script after events exist)

## Unlocks / enhances

- D08f-03 … D08f-06 can load their month dirs
- February Life Script

## Non-goals

- March–June content
- Tone store (C11)
- WhatsApp ingestion
- Biography / cinematic plot
- Ground-truth obligation YAML unless a Jan thread actually resolves (evaluator-only; keep minimal)

## Shape (ordinary)

Some January threads resolve (Sam empty-state? climbing with Tom?). One new work dependency. Mundane messages. **One forget** (user or Enigma-scoped — source event + optional forget API hook, not a new engine). A recurring preference starts to be visible (author as repeated source evidence, not a tone-store write).

## Acceptance criteria

- [ ] Loader recurses `timeline/**/*.yaml` (or `timeline/YYYY-MM/**/*.yaml`); 0.2.1 week files still load
- [ ] `scenario.yaml` version `0.3.0`; description span 2026-01-05 → at least 2026-02-28
- [ ] February source events only (calendar / mail / notes / reminders / contacts). No world-model keys
- [ ] One forget-shaped event or explicit “forget this” source (ordinary, not a crisis)
- [ ] Stub `2026-02-12.yaml` 1:1 kept or replaced by the real Feb 12 morning events
- [ ] Tests: nested February events appear in `load_scenario`; fingerprint still deterministic
- [ ] No `ALEX_BIOGRAPHY.md`

## Test plan

- `load_scenario("scenarios/alex-v1")` includes ≥1 event with `at` in 2026-02
- Double-load byte stability / engine fingerprint match
- Validator rejects obligation keys in new payloads

## Privacy constraints

- Fictional only. Chat-shaped evidence = `email.receive` or `note.upsert` until D04 grows a message source.
