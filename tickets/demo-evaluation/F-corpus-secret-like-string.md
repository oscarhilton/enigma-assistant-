# F-corpus-secret-like-string — zero-tolerance import boundary

| Field | Value |
| --- | --- |
| Status | `done` |
| Domain | `demo-evaluation` |
| Branch | `ticket/f-import-boundary-gates` |
| Related | D08b, D09 |
| Package boundary | `packages/simulation/.../corpus/sanitise.py`, `packages/simulation/tests/fixtures/corpus/import-boundary/**`, `packages/simulation/tests/test_f_import_boundary_gates.py` |

## Intent

Conversations containing API keys / JWTs / private-key-like material are rejected by the sanitiser. Acceptance is binary — never a soft leak rate.

## Acceptance

- [x] Mini fixture with synthetic secret-like string is rejected
- [x] Rejection reason recorded in sanitiser diagnostics (`secret:*`)
