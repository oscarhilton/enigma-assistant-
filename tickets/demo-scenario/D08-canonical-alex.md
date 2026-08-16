# D08 — Canonical Alex scenario

| Field | Value |
| --- | --- |
| Status | `done` (merged #35) |
| Branch | `ticket/D08-canonical-alex` |
| Domain | `demo-scenario` |

## Package boundary (hard)

- May edit: `scenarios/alex-v1/**` (entities, timeline, content, ground_truth)
- Must not edit: `packages/simulation` engine (D5), eval metrics (D7), attacks-only packs beyond light hooks (D9)

## Hard depends

- D3

## Soft depends (~)

- D4, D5

## Unlocks / enhances

- Primary benchmark corpus for D7
- Product narrative substrate for D12

## Non-goals

- Adversarial injection packs (D9)
- Curated 5–10 minute walkthrough scripting (D12)

## Acceptance criteria

- [x] Min-viable coherent fictional life for Alex Morgan: **3 weeks** (2026-01-05 → 2026-01-25). Full multi-month expansion is a future version bump, not this release.
- [x] Work, personal, projects, relationships, deadlines, noise, ambiguity, cross-source cases
- [x] Scenario remains immutable after release (bump `version` in `scenario.yaml` under the same `alex-v1` package id)

## Test plan

- Loader + determinism smoke over full corpus
- Spot-check ground-truth coverage for sample weeks

## Privacy constraints

- All content fictional; no real names/emails from Private Mode
