# M11 — Gmail

| Field | Value |
| --- | --- |
| Status | `done` |
| Branch | `ticket/M11-gmail` |
| Domain | `google` |

## Package boundary (hard)

- May edit: `packages/ingestion/src/personal_enigma/ingestion/sources/gmail.py`
- May edit: `apps/api/src/personal_enigma/api/google/gmail/**` and `apps/worker/src/personal_enigma/worker/google/gmail/**` (create) for OAuth + sync only
- Must not edit: `apps/apple-bridge/**`, other `sources/*.py`, `packages/domain/**`

## Hard depends

- M01, M03, M04

## Soft depends (~)

- M10 (Contacts-backed identity)
- M00a (persist sync state)

## Unlocks / enhances

- Soft-enhances M15/M16 with email evidence (**Apple-only merge can proceed without Gmail**)

## Non-goals

- Apple Mail / IMAP / Mail.app scraping
- Send/modify mail

## Acceptance criteria

- [x] Read-only Gmail API ingestion → `PrivateMessage`
- [x] `DataSource.get_changes` implementation in `gmail.py`
- [x] Entity resolution against Contacts when available
- [x] Works with remote LLM disabled (ingest + local transform only)

## Test plan

- Recorded HTTP fixture tests
- Privacy invariants on transformed email bodies

## Privacy constraints

- Medium default; strip secrets before remote
