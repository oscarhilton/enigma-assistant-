# M17 — Privacy inspector

| Field | Value |
| --- | --- |
| Status | `todo` |
| Branch | `ticket/M17-privacy-inspector` |
| Domain | `privacy` |

## Package boundary (hard)

- May edit: `packages/privacy/**`, `apps/web` inspector UI, `apps/api` read-only inspection endpoints
- Must not weaken M04 invariants to “make the UI easier”

## Depends on

- M04, M03

## Unlocks

- User trust / transparency for M18–M19

## Non-goals

- Editing remote provider policies beyond viewing/explaining

## Acceptance criteria

- [ ] UI/API shows what would be sent remotely for a given attention action
- [ ] Shows privacy level per source and redactions applied
- [ ] Allows user to cancel remote send
- [ ] Documents Apple permission revocation effects

## Test plan

- API tests for inspection payloads
- Web component tests for redaction display
- Invariant: inspector itself does not upload

## Privacy constraints

- Inspector is local-first; no analytics of private payloads
