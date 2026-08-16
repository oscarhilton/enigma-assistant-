# F-corpus-unexpected-real-entity — zero-tolerance import boundary

| Field | Value |
| --- | --- |
| Status | `done` |
| Domain | `demo-evaluation` |
| Branch | `ticket/f-import-boundary-gates` |
| Related | D08b, D09 |
| Package boundary | `packages/simulation/.../corpus/sanitise.py`, `packages/simulation/tests/fixtures/corpus/import-boundary/**`, `packages/simulation/tests/test_f_import_boundary_gates.py` |

## Intent

Public-demo sanitiser rejects conversations with high density of recognisable real-world named entities. Conservative rejection preferred over heroic rewriting.

## Acceptance

- [x] Dense real-entity mini fixture rejected under demo-safe sanitiser
- [x] Rejection reason recorded (`unexpected_real_entity:*`)
- [x] `assert_import_boundary_clean` fails hard on the dirty fixture
