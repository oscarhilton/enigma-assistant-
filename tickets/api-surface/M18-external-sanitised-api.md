# M18 — External sanitised API

| Field | Value |
| --- | --- |
| Status | `todo` |
| Branch | `ticket/M18-external-sanitised-api` |
| Domain | `api-surface` |

## Package boundary (hard)

- May edit: `apps/api/src/personal_enigma/api/routes/external/**` (create)
- May edit: OpenAPI schemas under that tree
- Must reuse privacy gate from `packages/privacy`
- Must not edit: `api/reasoning/**` (M05), `api/bridge/**` (M07), `api/google/**` (M11/M12), inspector routes (M17)

## Hard depends

- M04, M05, M06

## Soft depends (~)

- M00a

## Unlocks / enhances

- Hard-unlocks M19

## Non-goals

- Public internet multi-tenant SaaS hardening (single-user local-first MVP)

## Acceptance criteria

- [ ] External API returns only sanitised / transformed resources
- [ ] Auth for local clients
- [ ] Explicit endpoints for attention items and capability status
- [ ] Refusal paths when privacy gate fails

## Test plan

- Contract tests for response schemas
- Negative tests attempting to fetch PrivatePerson

## Privacy constraints

- No wholesale Notes; no raw contacts
