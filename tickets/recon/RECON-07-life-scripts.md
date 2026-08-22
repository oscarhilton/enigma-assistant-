# RECON-07 — Life Scripts on the restored spine

| Field | Value |
| --- | --- |
| Status | `future` |
| Branch | `ticket/RECON-07-life-scripts` |
| Domain | `recon` |

## Package boundary (hard)

- May edit: Life Script runner / CLI adapters needed for the **current** spine, tests, docs pointers, this ticket
- Must not edit: [C12](../conversational-ui/C12-life-scripts.md) frozen rules (scripts still speak like Alex); PolarIS strategy scripts ([ADR-047](../../docs/adr/047-executive-motifs-and-search-efficiency.md)); `persona.yaml` as engine input; Observatory UI

## Hard depends

- [RECON-06](./RECON-06-event-action-spine.md) `done`

## Soft depends (~)

- [C12](../conversational-ui/C12-life-scripts.md) `landed` YAML + runner — **reuse**, do not fork
- [C13](../conversational-ui/C13-life-script-reliability.md) reliability (may remain a sibling; do not absorb unless the runner change is required)
- [P02](../pilot/P02-alex-life-scripts-as-product-tests.md) browser product tests

## Unlocks / enhances

- RECON-08 (catalogue moments from scripts); C13 quality; [HARBOUR-01](../harbour/HARBOUR-01-activity-readiness-model.md) (startup graphs as HOW)

## Intent

C12 already froze Life Scripts as **product-acceptance episodes**. After C28-class spine lands, scripts must run against **current main** causal events — not a ghost orchestrator.

**First-class use case (this ticket):** readiness / startup graphs — **HOW** an activity normally gets started (prerequisites, variants, setup). Harbour later compiles those graphs; PolarIS still decides **whether now**. Scripts remain reusable descriptions, not a rigid automation engine.

This is **not** a second Life Scripts constitution and **not** PolarIS strategy scripts.

## Non-goals

- Architecture-named utterances in YAML
- `ALEX_BIOGRAPHY.md`
- PolarIS opening book
- New Council seats
- Auto-playing setup as COMMIT
- Implementing Harbour types (01)

## Acceptance criteria

- [ ] Existing C12 frozen rules still hold (Alex speech; public-effect assertions)
- [ ] At least one January script exercises a spine `work.*` / assist lifecycle event as a public effect (or defers with an explicit hole the Observatory can show)
- [ ] At least one script (or adjacent evaluator YAML) encodes a **startup graph** with ≥2 variants (example: make-music full hardware vs headphones-only) without becoming an automation engine
- [ ] Failures attribute to world/spine/capability — not “the model felt”
- [ ] C12 ticket is not rewritten as `todo`

## Exit conditions

Done when RECON-08 can cite scripted moments (including one readiness/startup graph) as catalogue sources without ingesting them into Enigma, and Harbour-01 can later attach types without rewriting C12.

## Test plan

- Replay one landed C12 script on the new spine
- Negative: YAML mentioning PolarIS type names is rejected (C12 smell rule)

## Privacy constraints

- Scripts stay synthetic Alex
- Never ingested as biography
