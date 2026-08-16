# Demo suppression UI (D10 amendment)

| Field | Value |
| --- | --- |
| Status | `in_progress` |
| Branch | `ticket/demo-suppression-ui` |
| Domain | `demo-ui` |
| Parent | [D10](./D10-demo-ui.md) |

## Package boundary (hard)

- May edit: `apps/web/src/demo/**`, demo routes/styles, `apps/api` `/demo/*` stubs
- Must not edit: scenario corpus; privacy pages except shared banner shell

## Hard depends

- D10

## Acceptance criteria

- [x] `/demo/status` exposes `signals_considered` alongside surfaced / suppressed
- [x] Attention + simulation status show considered vs surfaced / suppressed
- [x] Developer-only `/demo/suppressed` inspector with reason filters + why-not
- [x] No `signal_class` / ground-truth labels in public chrome or inspector payloads
- [x] Vitest coverage for dashboard stats + inspector

## Test plan

- `pnpm --filter web test` (DemoChrome / SuppressionInspector)
- `uv run pytest apps/api/tests/test_demo.py`
