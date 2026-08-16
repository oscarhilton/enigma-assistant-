# Feature scenario stub — background-threading

| Field | Value |
| --- | --- |
| Status | `done` |
| Domain | `demo-scenario` |
| Related | D08b, D04 |
| Branch | `ticket/F-background-threading` |
| Path | `scenarios/feature/background-threading/` |

## Intent

Imported multi-message threads preserve conversation identity and chronological ordering after sanitiser + timeline placement.

## Package boundary

- `scenarios/feature/background-threading/**`
- May edit: `packages/simulation/.../corpus/timeline.py` (if needed), tests under `packages/simulation/tests/`

## Acceptance

- [x] Thread ids stable across messages in a conversation
- [x] Relative reply order preserved after timestamp assignment
