# M15 — Cross-source obligation merging

| Field | Value |
| --- | --- |
| Status | `done` |
| Branch | `ticket/M15-cross-source-merging` |
| Domain | `obligations` |

## Package boundary (hard)

- May create/edit: `packages/obligations/**` (preferred) **or** `packages/attention/src/personal_enigma/attention/merge/**` if keeping merge inside attention
- May read: fixtures, domain, ingestion outputs, dedupe
- Must not edit: ingestion `sources/*.py`, apple-bridge Swift, google OAuth

## Hard depends

- M06

## Soft depends (~)

- M08, M09 (live Apple evidence — fixtures can substitute)
- M11, M12 (email / Google calendar evidence)
- M02 (scenario packs)
- M14 (retrieval context)

## Unlocks / enhances

- Hard-unlocks M16

## Non-goals

- Provider-specific alert UIs
- Creating reminders
- Implementing calendar dedupe (M12)

## Acceptance criteria

- [x] Merge reminder + email follow-up + calendar meeting into one `Obligation` with typed evidence
- [x] Single attention item with combined evidence narrative
- [x] Confidence score populated
- [x] Google/Apple calendar duplicates do not produce duplicate attention items (via M12 dedupe + merge)

## Test plan

- Spec scenario “Review proposal” fixture → one obligation
- Dedupe regression tests

## Privacy constraints

- Evidence refs local; remote summaries use transformed text only
