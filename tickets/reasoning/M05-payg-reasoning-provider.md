# M05 — PAYG reasoning provider

| Field | Value |
| --- | --- |
| Status | `todo` |
| Branch | `ticket/M05-payg-reasoning-provider` |
| Domain | `reasoning` |

## Package boundary (hard)

- May create/edit: `packages/reasoning/**` (new package if needed) and wire into `apps/api` / `apps/worker` **only for provider client**
- Must not edit: apple-bridge, google adapters

## Depends on

- M03, M04

## Unlocks

- M06 (optional remote ranking), M18, M19

## Non-goals

- Running giant local LLMs
- Sending private corpora for embedding (use M14 local embeddings)

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
