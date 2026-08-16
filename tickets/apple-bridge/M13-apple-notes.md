# M13 — Apple Notes experimental adapter

| Field | Value |
| --- | --- |
| Status | `todo` |
| Branch | `ticket/M13-apple-notes` |
| Domain | `apple-bridge` |

## Package boundary (hard)

- May edit: `apps/apple-bridge` Notes module
- May edit: ingestion + privacy hooks for note passages
- Must follow ADR-004

## Depends on

- M07; M04 strongly recommended before enabling remote paths

## Unlocks

- M14 (local embeddings over notes)

## Non-goals

- Attachments, OCR, handwriting, audio, drawings
- Notes SQLite scraping
- Wholesale remote transmission

## Acceptance criteria

- [ ] Explicit opt-in; automation permission separate from Calendar/Reminders/Contacts
- [ ] `NotesSource` list/read via Apple Events / AppleScript
- [ ] Map to `PrivateNote` (title, plain text, folder, created/updated, stable id)
- [ ] Capability `quality: "best_effort"`
- [ ] Local relevance detection path stubs; no auto remote ship of full body

## Test plan

- Adapter tests with mocked Apple Events results
- Privacy tests: full body never `may_transmit_remotely` by default

## Privacy constraints

- Default remote privacy HIGH; select → extract passage → transform → leakage analysis
