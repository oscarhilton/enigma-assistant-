# UI2-05 — Inspectability minimal

| Field | Value |
| --- | --- |
| Status | `todo` |
| Branch | `ticket/UI2-05-inspectability-minimal` |
| Domain | `ui2` |
| Programme | [UI2](./README.md) |

## Package boundary (hard)

- May edit: `apps/web/src/v2/**`
- Must not edit: Cortex surface placement; no Cortex on v2 main surface

## Hard depends

- UI2-01 v2 shell
- C35 Goose (`done`)

## Frozen spec (launchpad)

**UI:** Show what matters, what Enigma is doing, and why — without requiring users to understand architecture.

## Acceptance criteria

- [ ] Goose click opens compact Why/work sheet (not Cortex)
- [ ] Why projection read-model only — no semantic reconstruction in React
- [ ] Sheet dismisses cleanly; no stale AgentWork after world switch

## Test plan

- Goose inspect shows work labels from licence
- No `CortexPanel` on v2 conversation surface

## Privacy constraints

- Why sheet uses transformed projections only
