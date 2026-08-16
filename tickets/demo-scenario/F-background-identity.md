# Feature scenario — background-identity

| Field | Value |
| --- | --- |
| Status | `done` |
| Domain | `demo-scenario` |
| Related | D08c, M10 |
| Branch | `ticket/F-background-identity` |
| Path | `scenarios/feature/background-identity/` |

## Intent

Same synthetic background person appears consistently across messages (rewritten identities, not FinePersonas native names).

## Package boundary

- `scenarios/feature/background-identity/**`
- May edit: `packages/simulation/.../corpus/background.py` cast helpers + contacts wiring
- May edit: `packages/simulation/tests/`
- May edit: `packages/identity/tests/` (namespace disjointness proofs)

## Acceptance

- [x] Background person namespace disjoint from canonical people
- [x] Contacts stream can materialise background cast without importance labels
