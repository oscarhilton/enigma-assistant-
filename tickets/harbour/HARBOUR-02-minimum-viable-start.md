# HARBOUR-02 — Minimum viable start

| Field | Value |
| --- | --- |
| Status | `future` |
| Branch | `ticket/HARBOUR-02-minimum-viable-start` |
| Domain | `harbour` |

## Package boundary (hard)

- May edit: start-derivation over readiness types + Life Script **variants**, tests, docs pointers, this ticket
- Must not edit: PolarIS searcher / evaluator; C12 frozen speech rules; Assist execution; Harbour-03 learning store; Observatory visual language

## Hard depends

- [HARBOUR-01](./HARBOUR-01-activity-readiness-model.md) `done`

## Soft depends (~)

- [RECON-07](../recon/RECON-07-life-scripts.md) startup-graph variants (already a hard dep of 01)
- Foundry legality: a variant that requires a disallowed capability is not viable
- [ADR-024](../../docs/adr/024-shareable-recipes-procedure-never-personal-state.md) — may *cite* a recipe id; do not ingest personal state

## Unlocks / enhances

- HARBOUR-03 (repeated unused full-setups); RECON-08 / ALEX-EVAL music invariants

## Intent

Derive the **smallest valid setup** that crosses from intention to doing, using Life Script variants and canonical capabilities / constraints. Prefer Ableton + headphones over cupboard + garage + keyboard **when that variant is valid**. Never invent missing facts.

## Non-goals

- Rigid script playback as the product
- PolarIS “is now a good window”
- Auto-rearranging the user’s house
- Filling unknowns to make a prettier start

## Acceptance criteria

- [ ] Given the music fixture, if a headphones-only variant is legal, it is preferred over full hardware fetch
- [ ] If no smaller variant is legal, result is `not_ready` + blockers — not a hallucinated layout
- [ ] Unknown software state remains unknown; it may block a variant, not become “probably updated”
- [ ] Output names variant / script ids + required facts; it does not COMMIT
- [ ] Authority ceiling stays PREPARE unless Assist already granted more ([ADR-019](../../docs/adr/019-delegated-authority-and-execution-ladder.md))

## Exit conditions

Done when the music eval (RECON-08) can assert “minimum viable start preferred over unnecessary full setup” from this derivation, and PolarIS can still say “not now.”

## Test plan

- Headphones variant present → chosen; full fetch not required
- Headphones variant absent / illegal → `not_ready`, keyboard+cable remain blockers
- Negative: inventing “keyboard already on desk” is rejected

## Privacy constraints

- Variants are procedures, not a psych profile of how Alex “really” works
- Demo/Alex first
