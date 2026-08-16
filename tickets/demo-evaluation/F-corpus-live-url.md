# F-corpus-live-url — zero-tolerance import boundary

| Field | Value |
| --- | --- |
| Status | `done` |
| Domain | `demo-evaluation` |
| Branch | `ticket/f-import-boundary-gates` |
| Related | D08b, D09 |
| Package boundary | `packages/simulation/.../corpus/sanitise.py`, `packages/simulation/tests/fixtures/corpus/import-boundary/**`, `packages/simulation/tests/test_f_import_boundary_gates.py` |

## Intent

Live external URLs in corpus candidates are rewritten to `.example` hosts or cause rejection. Emitting a live third-party URL is a hard gate failure.

## Acceptance

- [x] Mini fixture with live http(s) URLs is rewritten to `portal.company-*.example`
- [x] Public-demo sanitiser never emits live third-party URL hosts
- [x] Zero-tolerance post-scan rejects if rewrite misses a live host
