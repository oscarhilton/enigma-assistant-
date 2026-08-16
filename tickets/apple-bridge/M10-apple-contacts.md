# M10 — Apple Contacts / entity resolution

| Field | Value |
| --- | --- |
| Status | `todo` |
| Branch | `ticket/M10-apple-contacts` |
| Domain | `apple-bridge` |

## Package boundary (hard)

- May edit: `apps/apple-bridge` Contacts module
- May edit: `packages/domain` / new `packages/identity` if needed for resolver
- May edit: `packages/ingestion` contacts source
- Must not send `PrivatePerson` to remote providers

## Depends on

- M01, M07

## Unlocks

- Stable PERSON_* IDs for M03, M11, M15

## Non-goals

- Writing contacts
- Messages / Mail identity sources beyond Contacts + email headers later

## Acceptance criteria

- [ ] Request Contacts permission via `CNContactStore`
- [ ] Map to `PrivatePerson` (display name, aliases, emails, phones, orgs, provider_ids)
- [ ] Entity resolver unifies email / calendar invite name / contact record → canonical person → HMAC pseudonym
- [ ] Contact identity mappings remain private/local
- [ ] `GET /contacts/changes`

## Test plan

- Resolver tests: joe@example.com + "Joe" + "Joseph Atkinson" → one PERSON id
- Negative test: remote payload builders reject raw PrivatePerson

## Privacy constraints

- Contacts default HIGH; remote sees pseudonyms only
