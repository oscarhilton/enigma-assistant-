# D12 — Curated product demo / Phase 2 exit gate

| Field | Value |
| --- | --- |
| Status | `todo` |
| Branch | `ticket/D12-product-demo-scenario` |
| Domain | `demo-scenario` |
| Baseline | `v0.1.0-mvp` |

## Package boundary (hard)

- May edit: a curated walkthrough scenario (e.g. `scenarios/product-demo/**`) and docs under `docs/architecture/` / `docs/demo/`
- May edit: D10 UI copy/routes for the scripted walkthrough only
- Must not reopen MVP architecture unless exit-gate metrics reveal a hard failure

## Hard depends

- D07
- D08
- D10

## Soft depends (~)

- D09
- D11

## Unlocks / enhances

- Phase 2 exit: credible answer to “does continuity help?”
- Safe onboarding demo for humans

## Non-goals

- Public launch marketing site
- Claiming production readiness for real Private lives without explicit sign-off

## Acceptance criteria

- [ ] Scripted demo path: day-one emptiness → weeks of evidence → attention that reflects open loops
- [ ] Walkthrough doc: operator steps, expected screens, eval snapshot vs `v0.1.0-mvp` control
- [ ] Exit-gate checklist: environment separation holds, feature+Alex evals green, adversarial privacy pack green, remote optional
- [ ] Explicit statement of what Phase 2 proved and what remains out of scope (Mail, Messages, etc.)

## Test plan

- Automated smoke of the product-demo scenario through engine + eval
- Manual checklist attached to PR

## Privacy constraints

- Demo remains structurally unable to reach real sources (D01 invariant still tested)
