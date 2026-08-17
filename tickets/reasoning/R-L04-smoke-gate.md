# R-L04 — Smoke gate (live Fireworks lane)

| Field | Value |
| --- | --- |
| Status | `done` |
| Branch | `ticket/R-L04-L08-live-gate` |
| Domain | `demo-evaluation` |

## Package boundary

- May edit: `packages/evaluation/src/personal_enigma/evaluation/live_gate.py`
- May edit: `packages/evaluation/tests/test_live_gate.py`
- May edit: `packages/evaluation/fixtures/smoke/**`

## Acceptance criteria

- [x] `enigma-eval --reasoning-gate-live --smoke-only`
- [x] 3 cases × 3 reps with unanimous 3/3 per case
- [x] Budget cap $0.05; stop on parse/schema/evidence/privacy/unanimous failure

## Test plan

- `uv run pytest packages/evaluation/tests/test_live_gate.py::test_smoke_gate_mock_passes_unanimous`
