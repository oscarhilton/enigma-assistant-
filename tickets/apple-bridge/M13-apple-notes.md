# M13 — Apple Notes experimental adapter

| Field | Value |
| --- | --- |
| Status | `todo` |
| Branch | `ticket/M13-apple-notes` |
| Domain | `apple-bridge` |

## Package boundary (hard)

- May edit: `apps/apple-bridge/Sources/EnigmaAppleBridgeCore/Notes/**`
- May edit: Transport routes **only** for `/notes/*`
- May edit: `packages/ingestion/src/personal_enigma/ingestion/sources/apple_notes.py`
- May edit: `packages/privacy/src/personal_enigma/privacy/notes_policy.py` (create) for Notes HIGH defaults / passage rules only
- Must not edit: other sources, embeddings implementation (M14), SQLite Notes DB

## Hard depends

- M07

## Soft depends (~)

- M01
- M04 (required before enabling any remote note passages)

## Unlocks / enhances

- Hard-unlocks M14 Notes corpus indexing

## Non-goals

- Attachments, OCR, handwriting, audio, drawings
- Notes SQLite scraping
- Wholesale remote transmission
- Full local embedding pipeline (M14)

## Acceptance criteria

- [ ] Explicit opt-in; automation permission separate from Calendar/Reminders/Contacts
- [ ] `NotesSource` list/read via Apple Events / AppleScript
- [ ] Map to `PrivateNote`
- [ ] Capability `quality: "best_effort"`
- [ ] Local relevance detection path stubs; no auto remote ship of full body

## Test plan

- Adapter tests with mocked Apple Events results
- Privacy tests: full body never `may_transmit_remotely` by default

## Privacy constraints

- Default remote privacy HIGH; select → extract passage → transform → leakage analysis
