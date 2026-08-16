# M07 — macOS Apple Bridge shell

| Field | Value |
| --- | --- |
| Status | `done` |
| Branch | `ticket/M07-bridge-shell` |
| Domain | `apple-bridge` |

## Package boundary (hard)

- May edit: `apps/apple-bridge/Sources/EnigmaAppleBridge/**`
- May edit: `apps/apple-bridge/Sources/EnigmaAppleBridgeCore/Transport/**`
- May edit: `packages/ingestion/src/personal_enigma/ingestion/bridge_client.py`
- May edit: `apps/api/src/personal_enigma/api/bridge/**` (create as needed) for token install + client config only
- Must not edit: Calendar/Reminders/Contacts/Notes source adapters beyond existing stubs
- Must not edit: `packages/ingestion/src/personal_enigma/ingestion/sources/**`

## Hard depends

- Scaffold (ADR-002)

## Soft depends (~)

- M00a (persist token metadata)
- M00b (settings capability display)

## Unlocks / enhances

- Hard-unlocks M08–M10, M13

## Non-goals

- Real calendar/reminder/contact/note reads
- Internet-facing bind
- EventKit permission flows beyond stubs (source tickets)

## Acceptance criteria

- [x] Local server on Unix socket or `127.0.0.1` only
- [x] Bearer token auth (Keychain-backed secret generation documented; Core generates token)
- [x] `GET /capabilities` returns capability JSON
- [x] Permission request hooks stubbed per source
- [x] Continues if individual sources unauthorised
- [x] No LLM provider calls from bridge

## Test plan

- XCTest for capabilities encoding
- Integration test: Core client → bridge health/capabilities with token (macOS CI)

## Privacy constraints

- Bridge never transmits data off-machine
