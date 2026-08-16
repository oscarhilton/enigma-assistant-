# M07 — macOS Apple Bridge shell

| Field | Value |
| --- | --- |
| Status | `todo` |
| Branch | `ticket/M07-bridge-shell` |
| Domain | `apple-bridge` |

## Package boundary (hard)

- May edit: `apps/apple-bridge/**`
- May add thin client in `packages/ingestion` / `apps/api` for bridge HTTP/socket **client only**
- Must not implement EventKit/Contacts/Notes adapters beyond stubs (M08+)

## Depends on

- Scaffold; ADR-002

## Unlocks

- M08–M10, M13

## Non-goals

- Real calendar/reminder/contact/note reads
- Internet-facing bind

## Acceptance criteria

- [ ] Local server on Unix socket or `127.0.0.1` only
- [ ] Bearer token auth (Keychain-backed secret generation documented; Core generates token)
- [ ] `GET /capabilities` returns scaffold capability JSON
- [ ] Permission request hooks stubbed per source
- [ ] Continues if individual sources unauthorised
- [ ] No LLM provider calls from bridge

## Test plan

- XCTest for capabilities encoding
- Integration test: Core client → bridge health/capabilities with token (macOS CI)

## Privacy constraints

- Bridge never transmits data off-machine
