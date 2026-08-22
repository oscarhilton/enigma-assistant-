# HARBOUR-01 — Activity readiness model

| Field | Value |
| --- | --- |
| Status | `future` |
| Branch | `ticket/HARBOUR-01-activity-readiness-model` |
| Domain | `harbour` |

## Package boundary (hard)

- May edit: readiness types (prefer pinned `packages/domain/**/*readiness*` / `*harbour*` **or** a thin `packages/harbour` **if this ticket introduces it with an architecture pointer**), [harbour.md](../../docs/architecture/harbour.md), [activity_readiness.v0.json](../../docs/architecture/eval-stubs/activity_readiness.v0.json) (additive), tests, this ticket
- Must not edit: `DecisionPosition` definition ([POLARIS-SEARCH-01](../polaris/POLARIS-SEARCH-01-decision-position.md)); PolarIS searcher; Assist COMMIT; Council copy; Observatory UI; C12 frozen rules; `scenarios/alex-v1/timeline/**`

## Hard depends

- [RECON-07](../recon/RECON-07-life-scripts.md) `done` (startup / prerequisite graphs exist as a Life Script use case)
- [POLARIS-SEARCH-01](../polaris/POLARIS-SEARCH-01-decision-position.md) `done` (Harbour **reads** a position; does not own it)
- [OBSERVATORY-01](../observatory/OBSERVATORY-01-truth-registry.md)–[02](../observatory/OBSERVATORY-02-observatory-ui.md) `done` (programme gate)

## Soft depends (~)

- Foundry / PolarIS-02 capability names (read-only)
- [open-loop-commitments.md](../../docs/architecture/open-loop-commitments.md) / SE11 for deferred-intention handles
- [ADR-019](../../docs/adr/019-delegated-authority-and-execution-ladder.md) — no parallel ladder

## Unlocks / enhances

- HARBOUR-02; Observatory later Harbour evidence payload; PolarIS may *consume* readiness without owning it

## Intent

Typed prerequisites / resources / locations / software-state / unknowns / transition-cost and a **readiness result**. No autonomous action. Headline: **CAN the user begin**, not SHOULD they now ([harbour.md](../../docs/architecture/harbour.md)).

## Non-goals

- PolarIS search, ply-0 ranking, or opportunity-cost
- Minimum-viable-start derivation (02)
- Friction learning (03)
- Star names; Council seat; ADR-049
- Inventing missing facts; COMMIT

## Acceptance criteria

- [ ] Types cover: prerequisite, resource, location, software_state, unknown, transition_cost, readiness result
- [ ] `unknown` facts cannot be coerced to `known` without a new evidence ref
- [ ] Result is inspectable structure (ids, reason codes, evidence refs) — not CoT, not a percent
- [ ] Ready is independent of PolarIS ply-0 (fixture: ready + PolarIS defers)
- [ ] No method on the type starts, fetches, or COMMITs
- [ ] Seed compile of `alex-music-readiness` (keyboard cupboard, cable garage, Ableton unknown)
- [ ] Observatory can mark Harbour `SPECIFIED` / later `IMPLEMENTED` with evidence refs
- [ ] Docs remain the constitution; this ticket does not rewrite [council.md](../../docs/architecture/council.md)

## Exit conditions

Done when 02 can derive a minimum viable start from a typed result **without** inventing Ableton-update or keyboard-already-out, and PolarIS can ignore `ready` when the window is bad.

## Test plan

- Music fixture: three facts (2 known, 1 unknown) round-trip
- Negative: filling `ableton_update` as known without evidence is rejected
- Negative: `ready=true` does not imply a PolarIS ply-0 of “make music now”

## Privacy constraints

- Setup facts are purpose-bound (this intention), not a home inventory biography
- Demo/Alex first; no Oscar garage dump
