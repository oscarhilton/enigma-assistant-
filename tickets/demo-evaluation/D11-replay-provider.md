# D11 — Provider recording + deterministic replay

| Field | Value |
| --- | --- |
| Status | `todo` |
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

- [ ] Record sanitised provider request/response pairs from Demo runs (TransformedContext only)
- [ ] Replay provider serves recordings by request hash / scenario step
- [ ] Eval runner can run fully offline with replay
- [ ] Mismatch behaviour is explicit (fail vs passthrough policy documented)

## Test plan

- Record → replay → identical eval report for a feature scenario
- Attempting replay with Private credentials present still does not hit network when replay mode forced

## Privacy constraints

- Recordings must never contain PrivatePerson fields or wholesale Notes
- Only Demo Mode may write recordings by default
