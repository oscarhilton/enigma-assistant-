# M15 — Cross-source obligation merging

| Field | Value |
| --- | --- |
| Status | `todo` |
| Branch | `ticket/M15-cross-source-merging` |
| Domain | `obligations` |

## Package boundary (hard)

- May edit: `packages/attention/**` and/or new `packages/obligations/**`
- May read fixtures, domain, ingestion outputs
- Must not special-case providers in merge core (use SourceType + evidence)

## Depends on

- M06, M08, M09; M11/M12 when available — fixtures can unblock earlier

## Unlocks

- M16, coherent attention UX

## Non-goals

- Provider-specific alert UIs
- Creating reminders

## Acceptance criteria

- [ ] Merge reminder + email follow-up + calendar meeting into one `Obligation`
- [ ] Single attention item with combined evidence narrative
- [ ] Confidence score populated
- [ ] Google/Apple calendar duplicates do not produce duplicate attention items

## Test plan

- Spec scenario “Review proposal” fixture → one obligation
- Dedupe regression tests

## Privacy constraints

- Evidence refs local; remote summaries use transformed text only
