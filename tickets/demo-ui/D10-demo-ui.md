# D10 — Demo UI

| Field | Value |
| --- | --- |
| Status | `done` (merged #34) |
| Branch | `ticket/D10-demo-ui` |
| Domain | `demo-ui` |

## Package boundary (hard)

- May edit: `apps/web/src/demo/**`, demo pages/routes, styles
- May edit: `apps/api` demo control routes (`/demo/*`) as needed for UI
- Must not edit: settings/privacy pages except shared banner shell; scenario corpus (D8)

## Hard depends

- D1

## Soft depends (~)

- D5, D2

## Unlocks / enhances

- Product demos without CLI
- Onboarding path into Shadow/Private later

## Non-goals

- Full Alex corpus (D8)
- Eval report visualisations beyond basic status (D7)

## Acceptance criteria

- [x] Timeline controls (step / day / speed as available)
- [x] Attention dashboard, memory browser, why view, privacy inspector hooks
- [x] Simulation status + persistent `DEMO MODE — FICTIONAL DATA ONLY` banner

### Amendment — compression / suppression (plan §85)

- [x] Dashboard stats: signals considered vs surfaced / suppressed
- [x] Developer-only suppression inspector (`/demo/suppressed`)
- [x] Why-not-surfaced view for false-positive debugging (developer mode)

Follow-up branch: `ticket/demo-suppression-ui`

## Test plan

- Component tests for controls + banner
- Smoke: advance day updates displayed simulated time
- (amendment) Suppression counts never expose ground-truth `signal_class` labels in public chrome

## Privacy constraints

- Ground truth must not appear in the default user demo chrome
