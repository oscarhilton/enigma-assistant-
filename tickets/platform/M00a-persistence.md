# M00a — Private persistence

| Field | Value |
| --- | --- |
| Status | `todo` |
| Branch | `ticket/M00a-persistence` |
| Domain | `platform` |

## Package boundary (hard)

- May edit: `apps/api/src/personal_enigma/api/db/**` (create as needed)
- May edit: `apps/worker/src/personal_enigma/worker/storage/**` (create as needed)
- May add: Alembic / SQLAlchemy / sqlite config under those trees only
- Must not edit: domain models (M01), bridge, google adapters, web UI

## Hard depends

- M01

## Soft depends (~)

- None

## Unlocks / enhances

- Sync cursor storage for all `DataSource` adapters
- M07 Keychain/token install bookkeeping (Core side)
- M15/M16 durable obligations

## Non-goals

- Cloud multi-tenant DB
- Storing raw Notes bodies for remote sync

## Acceptance criteria

- [ ] Local private database (sqlite acceptable for MVP)
- [ ] Tables/collections for sync cursors, ingested canonical records, obligations
- [ ] Migrations documented and tested
- [ ] No network exposure of DB

## Test plan

- Migration up/down smoke tests
- Round-trip insert/read for cursor + one domain type

## Privacy constraints

- DB is local-only; never dump private tables to remote APIs
