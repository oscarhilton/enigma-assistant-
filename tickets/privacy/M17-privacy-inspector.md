# M17 — Privacy inspector

| Field | Value |
| --- | --- |
| Status | `todo` |
| Branch | `ticket/M17-privacy-inspector` |
| Domain | `privacy` |

## Package boundary (hard)

- May edit: `packages/privacy/**`
- May edit: `apps/web/src/pages/PrivacyInspector*` and `apps/web/src/privacy/**` (create)
- May edit: `apps/api/src/personal_enigma/api/routes/privacy_inspector.py` (create)
- Must not edit: M04 invariant definitions to weaken them
- Must not edit: reasoning provider (M05) or ChatGPT UX (M19)

## Hard depends

- M04, M03

## Soft depends (~)

- M00b

## Unlocks / enhances

- Hard-unlocks trust UX for M19

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
