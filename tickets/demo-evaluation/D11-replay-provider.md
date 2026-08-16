# D11 — Replay provider

| Field | Value |
| --- | --- |
| Status | `todo` |
| Branch | `ticket/D11-replay-provider` |
| Domain | `demo-evaluation` |

## Package boundary (hard)

- May edit: `packages/reasoning/**` replay/record transports (coordinate if conflicting with live PAYG), `provider-replays/**`, evaluation wiring
- Must not edit: scenario YAML corpus (D8), web chrome beyond provider-mode selectors (D10)

## Hard depends

- D1
- M05 reasoning provider abstraction

## Soft depends (~)

- D7

## Unlocks / enhances

- Offline public demos
- Cost-free UI tests

## Non-goals

- Replacing MockReasoningProvider for unit tests

## Acceptance criteria

- [ ] Record live provider response (transformed prompt, response, tokens, latency, cost)
- [ ] Replay response deterministically from fixtures
- [ ] Complete public demo runs without internet access

## Test plan

- Record → replay golden fixture
- Assert identical assistant output bytes under REPLAY mode

## Privacy constraints

- Recorded prompts must already be privacy-gated; never record raw PrivatePerson
