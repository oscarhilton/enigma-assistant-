# M03 — Enigma transformation

| Field | Value |
| --- | --- |
| Status | `todo` |
| Branch | `ticket/M03-enigma-transformation` |
| Domain | `transformation` |

## Package boundary (hard)

- May edit: `packages/transformation/**` only
- May read: `packages/domain/**`, `packages/privacy/**`, `packages/fixtures/**`, `packages/identity/**`
- Must not edit: identity implementation (M10); may call `EntityResolver` protocol with a test double

## Hard depends

- M01

## Soft depends (~)

- M02 (fixture coverage)
- M10 (richer Contacts-backed pseudonyms — **do not wait**; use stub HMAC resolver until M10)

## Unlocks / enhances

- Hard-unlocks M04, M05
- Enables M06 local attention inputs

## Non-goals

- Calling remote LLMs
- Full obligation merging (M15)
- Implementing `packages/identity` (M10)

## Acceptance criteria

- [ ] Transformer maps private records → Enigma context with entity pseudonyms
- [ ] Default `may_transmit_remotely` is conservative (false unless policy allows)
- [ ] Notes path extracts minimal passages, not wholesale bodies
- [ ] Interface remains provider-agnostic

## Test plan

- Unit tests with fixtures proving no raw emails/phones/secrets in transformed output when marked sensitive
- Golden tests for pseudonym stability given fixed HMAC key in test config

## Privacy constraints

- Select → transform → transmit; never skip selection for Notes
