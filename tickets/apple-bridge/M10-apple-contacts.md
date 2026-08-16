# M10 — Apple Contacts / entity resolution

| Field | Value |
| --- | --- |
| Status | `todo` |
| Branch | `ticket/M10-apple-contacts` |
| Domain | `apple-bridge` |

## Package boundary (hard)

- May edit: `apps/apple-bridge/Sources/EnigmaAppleBridgeCore/Contacts/**`
- May edit: Transport routes **only** for `/contacts/*`
- May edit: `packages/ingestion/src/personal_enigma/ingestion/sources/apple_contacts.py`
- May edit: `packages/identity/**` only for resolver implementation
- **Must not edit:** `packages/domain/**` (schemas owned by M01)

## Hard depends

- M01, M07

## Soft depends (~)

- M02
- M03 (consumes resolver — M03 may already ship with stub)

## Unlocks / enhances

- Soft-enhances M03/M11/M15 pseudonym stability (**those tickets must not hard-wait on M10**)
- Hard-completes Contacts ingestion path

## Non-goals

- Writing contacts
- Changing domain model shapes (open M01 follow-up if needed)
- Messages / Mail.app identity scraping

## Acceptance criteria

- [ ] Request Contacts permission via `CNContactStore`
- [ ] Map to `PrivatePerson`
- [ ] `EntityResolver` unifies email / calendar invite name / contact → HMAC `PERSON_*`
- [ ] Contact identity mappings remain private/local
- [ ] `GET /contacts/changes`

## Test plan

- Resolver tests: joe@example.com + "Joe" + "Joseph Atkinson" → one PERSON id
- Negative test: remote payload builders reject raw PrivatePerson

## Privacy constraints

- Contacts default HIGH; remote sees pseudonyms only
