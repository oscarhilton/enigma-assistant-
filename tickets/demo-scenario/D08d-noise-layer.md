# D08d — Noise layer

| Field | Value |
| --- | --- |
| Status | `todo` |
| Branch | `ticket/D08d-noise-layer` |
| Domain | `demo-scenario` / `demo-simulation` |
| Parent | [D08](./D08-canonical-alex.md) |

## Package boundary (hard)

- May edit: `GeneratedNoiseStream` templates (newsletters, notifications, marketing, junk)
- May edit: ground-truth `signal_class: noise` fixtures
- Must not: mix adversarial/hostile packs into default noise (D09 stays separate)

## Hard depends

- D08c background integration

## Soft depends (~)

- D09 for optional SpamAssassin developer profiles

## Unlocks / enhances

- D08e scale profile
- UI “signals suppressed” stats (D10 amendment)

## Non-goals

- Pushing spam corpora through real Gmail
- Trademarked provider names in templates

## Acceptance criteria

- [ ] Deterministic local noise templates (BuildCloud, ParcelPost, etc.)
- [ ] Noise enters the same mailbox stream as canonical/background
- [ ] Background false-alert rate measured and under agreed threshold
- [ ] Quiet/noise-heavy days can yield zero attention items

## Test plan

- Feature scenario `background-no-alert`
- Noise classification never visible on `PrivateMessage` payloads

## Privacy constraints

- Synthetic-only for public Demo; SpamAssassin/TREC developer-only
