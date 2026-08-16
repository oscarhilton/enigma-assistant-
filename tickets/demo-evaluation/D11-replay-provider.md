# D11 — Provider recording + deterministic replay

| Field | Value |
| --- | --- |
| Status | `done` (merged #38) |
| Branch | `ticket/D11-replay-provider` |
| Domain | `demo-evaluation` |
| Baseline | `v0.1.0-mvp` |

## Package boundary (hard)

- May edit: `packages/evaluation/src/personal_enigma/evaluation/replay/**` (create as needed)
- May edit: `packages/reasoning/**` only for a replay/fake provider implementing the PAYG interface
- May edit: recorded fixtures under `scenarios/**/recordings/` or `packages/evaluation/fixtures/replay/`
- Must not call live OpenAI in default CI

## Hard depends

- D05
- D07

## Soft depends (~)

- M05 PAYG interface (already on MVP)

## Unlocks / enhances

- Deterministic reasoning paths for eval
- Offline demos without spending tokens

## Non-goals

- Recording real Private user sessions into the repo
- Replacing privacy gates

## Acceptance criteria

- [x] Record sanitised provider request/response pairs from Demo runs (TransformedContext only)
- [x] Replay provider serves recordings by request hash (primary) or scenario step (`complete_step` / optional `scenario_step`)
- [x] Eval runner can run fully offline with replay
- [x] Mismatch behaviour is explicit (fail vs passthrough policy documented)

### Amendment — scale replay (plan §85)

- [ ] Content-addressed replay fixtures suitable for canonical-scale corpus runs
- [ ] Corpus fingerprint (dataset, revision, sanitiser, selection seed) recorded with replay sets
- [ ] Avoid storing duplicate prompt payloads for large background runs

## Test plan

- Record → replay → identical eval report for a feature scenario
- Attempting replay with Private credentials present still does not hit network when replay mode forced
- (amendment) Offline canonical profile smoke using replay (nightly; not PR CI bulk download)

## Privacy constraints

- Recordings must never contain PrivatePerson fields or wholesale Notes
- Only Demo Mode may write recordings by default
