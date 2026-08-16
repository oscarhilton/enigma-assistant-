# F-corpus-real-domain-rewrite — zero-tolerance import boundary

| Field | Value |
| --- | --- |
| Status | `done` |
| Domain | `demo-evaluation` |
| Branch | `ticket/f-import-boundary-gates` |
| Related | D08b, D09 |
| Package boundary | `packages/simulation/.../corpus/sanitise.py`, `packages/simulation/tests/fixtures/corpus/import-boundary/**`, `packages/simulation/tests/test_f_import_boundary_gates.py` |

## Intent

Sanitiser rewrites all imported addresses to reserved `.example` domains. Remaining real-world domains are a hard gate failure — not a soft metric.

## Acceptance

- [x] Mini fixture with live domains is rewritten to `.example`
- [x] `assert_import_boundary_clean` fails hard if any non-reserved domain remains
- [x] In-body addresses rewritten (not only header fields)
