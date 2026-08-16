# M11 — Gmail

| Field | Value |
| --- | --- |
| Status | `todo` |
| Branch | `ticket/M11-gmail` |
| Domain | `google` |

## Package boundary (hard)

- May create: `packages/google` or `packages/ingestion/src/.../gmail*`
- May edit: `apps/api` / `apps/worker` OAuth + sync jobs
- Must not edit: `apps/apple-bridge`

## Depends on

- M01, M03, M04; M10 recommended for identity

## Unlocks

- M15 (email evidence), M16

## Non-goals

- Apple Mail / IMAP / Mail.app scraping
- Send/modify mail

## Acceptance criteria

- [ ] Read-only Gmail API ingestion
- [ ] Canonical private message model shared with future mail providers
- [ ] `DataSource.get_changes` implementation
- [ ] Entity resolution against Contacts when available
- [ ] Works with remote LLM disabled (ingest + local transform only)

## Test plan

- Recorded HTTP fixture tests
- Privacy invariants on transformed email bodies

## Privacy constraints

- Medium default; strip secrets before remote
