# D08f-05 — May ordinary events (old context returns)

| Field | Value |
| --- | --- |
| Status | `todo` |
| Branch | `ticket/D08f-05-may` |
| Domain | `demo-scenario` |
| Parent | [D08f](./D08f-alex-six-month.md) |

## Package boundary (hard)

- May edit: `scenarios/alex-v1/timeline/2026-05/**`, `scenarios/alex-v1/content/**` (new bodies only)
- Must not edit: other months’ committed events, `packages/ingestion/**`, C11, SEC-07, `intent_router.py`, Life Scripts

## Hard depends

- [D08f](./D08f-alex-six-month.md) programme

## Soft depends (~)

- [D08f-02](./D08f-02-february.md) loader. Do not block start.

## Shape (ordinary)

A **new** commitment intersects an **old** relationship or project context (Elena / Maya / Tom / Jordan — whoever already exists). Enough history that Enigma *could* help without the sources replaying the whole backstory in one email. No reunion-special; a calendar hold + a short mail is enough.

## Non-goals

- Re-authoring January as a recap thread · C11 · cinematic stakes

## Acceptance criteria

- [ ] Source events only under `timeline/2026-05/`
- [ ] New commitment evidenced; overlap with a prior contact/project is in payloads, not a bio file
- [ ] No recap-the-last-four-months email
- [ ] No world-model keys; no `ALEX_BIOGRAPHY.md`

## Test plan

- After glob: May events load; at least one payload references an existing contact id
- Ids unique across the package

## Privacy constraints

- Fictional only. Do not invent intimate-relationship plot.
