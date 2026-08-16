# D12 — Product demo scenario

| Field | Value |
| --- | --- |
| Status | `todo` |
| Branch | `ticket/D12-product-demo-scenario` |
| Domain | `demo-scenario` |

## Package boundary (hard)

- May edit: curated walkthrough scenario under `scenarios/` (e.g. `scenarios/product-demo-v1/**`) and docs for the 5–10 minute script
- Soft touch: `apps/web` demo entry presets only if needed
- Must not edit: full alex-v1 three-month authorship (D8) except referencing checkpoints

## Hard depends

- D1, D3

## Soft depends (~)

- D8, D10, D11

## Unlocks / enhances

- Sales / onboarding narrative without real accounts

## Non-goals

- Replacing the canonical eval corpus (D8)

## Acceptance criteria

- [ ] Curated 5–10 minute walkthrough demonstrating: initial ignorance → memory formation → cross-source reasoning → attention selection → privacy transformation → automatic resolution
- [ ] Runs without connecting a real account

## Test plan

- Scripted batch replay of walkthrough checkpoints
- Manual checklist in ticket PR description

## Privacy constraints

- Fictional data only; banner required throughout
