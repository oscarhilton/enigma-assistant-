# M05 — PAYG reasoning provider

| Field | Value |
| --- | --- |
| Status | `todo` |
| Branch | `ticket/M05-payg-reasoning-provider` |
| Domain | `reasoning` |

## Package boundary (hard)

- May create/edit: `packages/reasoning/**`
- May edit: `apps/api/src/personal_enigma/api/reasoning/**` and `apps/worker/src/personal_enigma/worker/reasoning/**` (create as needed) for client wiring only
- Must not edit: apple-bridge, google/ingestion sources, `apps/api` external sanitised routes (M18)

## Hard depends

- M03, M04

## Soft depends (~)

- None

## Unlocks / enhances

- Hard-unlocks M18/M19 remote paths
- Soft-enhances M06 if remote ranking is used later

## Non-goals

- Running giant local LLMs
- Sending private corpora for embedding (M14)
- ChatGPT product UX (M19)

## Acceptance criteria

- [ ] Pluggable PAYG client interface with dry-run / disabled mode
- [ ] Only accepts `TransformedContext` (or equivalent sanitised payload)
- [ ] Remote calls refused when privacy gate fails
- [ ] Cost / token logging hooks (local)

## Test plan

- Mock provider tests
- Invariant: disabled mode never opens network
- Rejection tests for unsanitised payloads

## Privacy constraints

- No `PrivatePerson`, wholesale Notes, or raw calendar attendee emails in requests
