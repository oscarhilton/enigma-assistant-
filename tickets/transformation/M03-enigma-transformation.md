# M03 — Enigma transformation

| Field | Value |
| --- | --- |
| Status | `todo` |
| Branch | `ticket/M03-enigma-transformation` |
| Domain | `transformation` |

## Package boundary (hard)

- May edit: `packages/transformation/**`
- May read: `packages/domain/**`, `packages/privacy/**`, `packages/fixtures/**`

## Depends on

- M01, M02 (recommended)

## Unlocks

- M04, M05, M06

## Non-goals

- Calling remote LLMs
- Full obligation merging (M15)

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
