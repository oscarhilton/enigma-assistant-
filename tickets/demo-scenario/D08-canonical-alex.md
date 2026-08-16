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

### Amendment — corpus subtasks (plan §79 / §85)

Corpus density is **not** a new top-level milestone. Track under:

| Subtask | Ticket | Status |
| --- | --- | --- |
| Canonical spine | [D08a](./D08a-canonical-spine.md) | `done` |
| Corpus pipeline | [D08b](./D08b-corpus-pipeline.md) | `done` |
| Background integration | [D08c](./D08c-background-integration.md) | `todo` |
| Noise layer | [D08d](./D08d-noise-layer.md) | `todo` |
| Canonical scale | [D08e](./D08e-canonical-scale.md) | `todo` |

Governing rule: **Story creates meaning. Corpus creates noise.** See [demo-corpus.md](../../docs/architecture/demo-corpus.md).

## Test plan

- Loader + determinism smoke over full corpus
- Spot-check ground-truth coverage for sample weeks
- (amendment) A/B critical recall with vs without background (D08c+)

## Privacy constraints

- All content fictional; no real names/emails from Private Mode
- Public Demo: `SYNTHETIC_CONFIRMED` corpora only ([ADR-007](../../docs/adr/007-demo-corpus-provenance.md))
