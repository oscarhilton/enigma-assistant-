# D08a — Canonical Alex story spine

| Field | Value |
| --- | --- |
| Status | `done` (landed with D08 / `scenarios/alex-v1/`) |
| Branch | `ticket/D08-canonical-alex` (historical) |
| Domain | `demo-scenario` |
| Parent | [D08](./D08-canonical-alex.md) |

## Package boundary (hard)

- May edit: `scenarios/alex-v1/**` (entities, timeline, content, ground_truth)
- Must not edit: corpus pipeline (D08b), eval metrics (D07)

## Hard depends

- D03–D07 laboratory

## Soft depends (~)

- none

## Unlocks / enhances

- Baseline metrics before background density (D08c+)

## Non-goals

- External corpus import
- Generated noise layer

## Acceptance criteria

- [x] Coherent authored Alex life with known ground truth (`scenarios/alex-v1/`)
- [x] All canonical ground truth passes without background corpus
- [x] No FinePersonas / Enron / SpamAssassin content in the spine

## Notes

Spine already exists from prior Alex work — see `scenarios/alex-v1/`. Corpus density is D08b–e.

## Privacy constraints

- All content fictional; no real names/emails from Private Mode
