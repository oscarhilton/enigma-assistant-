# Harbour — activity readiness, not a second planner

**Status:** Approved architecture language — documentation only; no runtime  
**Date:** 2026-08-22  
**Tickets:** [HARBOUR-01](../../tickets/harbour/HARBOUR-01-activity-readiness-model.md)–[03](../../tickets/harbour/HARBOUR-03-friction-learning.md)  
**Fits:** [polaris-search.md](./polaris-search.md) · [council.md](./council.md) · [observatory.md](./observatory.md) · C12 / [RECON-07](../../tickets/recon/RECON-07-life-scripts.md)

> Architecture first. No celestial name, no star alias, no extra ADR.  
> **Polaris decides whether now is a good move. Harbour gets the user across the gap between wanting and starting.**

Harbour is a **readiness / transition-friction** layer over one Enigma world model. It is not a sovereign planner, not a Council seat, not Foundry, not Goose, and not a second memory.

## Product principle

Externalise **working-memory friction** (what stands between intention and starting) without becoming a productivity tyrant. [Search deeply. Act shallowly. Replan constantly](./polaris-search.md) still applies. Harbour may compile setup cost; it must not nag, auto-COMMIT, or hide-optimise a life.

## Who answers what (do not collapse)

| Layer | Question | Must not |
| --- | --- | --- |
| **Polaris** | **SHOULD** the user do this activity *now*? Opportunity cost / best-next-move against the current `DecisionPosition`. | Own setup facts; discard a deferred intention |
| **Harbour** | **CAN** the user begin, and what stands between intention and starting? | Search futures; bind COMMIT; invent missing facts |
| **Life Scripts** | **HOW** does this activity normally get started? Reusable prerequisite / setup graphs and variants. | Become a rigid automation engine; replace C12 product-acceptance episodes |
| **Foundry** | What may the *system* attempt (named capabilities, legality, effects)? | Own user-body/setup readiness |
| **Goose** | Carry / fetch / report setup facts; help name friction | Independent authority; smile a gap away |
| **Craft / Council** | Why the activity *matters* on this position (assessments) | Own canonical readiness or world state |
| **Observatory** | What the programme is *true* about (implemented / wired / runtime-verified / user-usable) | Show Harbour CoT |
| **Narrator** | How the turn is *told* ([narrator.md](./narrator.md)) | Invent readiness facts to decorate a jot |

All of the above share **one** Enigma Context Graph / Vault. No per-character memory, no per-role truth.

## Motivating example (Alex)

Utterance: *“I fancy making some music.”*

Known / unknown (must stay distinguished):

| Fact | Epistemic |
| --- | --- |
| Keyboard is in the cupboard | Known (attested / last placed) |
| Power cable is in the garage | Known |
| Ableton update state | **Unknown** — must not be filled in |

Desired compile (Harbour):

1. Readiness blockers: fetch keyboard; fetch cable; software state unknown.
2. Transition cost: cupboard + garage + (maybe) update — expensive vs sitting down.
3. Minimum viable start: if Life Script variants + capabilities allow **Ableton + headphones without the keyboard**, prefer that over the full fetch — never invent that the keyboard is already out.
4. PolarIS, **independently**, scores whether *now* is a good window (energy, calendar, opportunity cost). Ready ≠ should.
5. If not now: **preserve / protect the intention** (typed open loop, forgettable) — do not discard it, do not manufacture urgency, do not COMMIT.

Catalogue sketch: [RECON-08](../../tickets/recon/RECON-08-alex-eval-catalogue.md) `alex-music-readiness`.

## Result shape (normative intent)

A readiness result is inspectable structure, not a vibe and not chain-of-thought:

- Activity / intention id
- Prerequisites, resources, locations, software-state, **unknowns**
- `transition_cost` (coarse, evidence-linked)
- `blockers[]` with reason codes + evidence refs
- `minimum_viable_start` (optional variant id) or `not_ready`
- `unknowns_preserved[]` — empty means “we claimed completeness,” which must be earned

No autonomous action. Authority stays READ / PREVIEW / PREPARE / COMMIT ([ADR-019](../adr/019-delegated-authority-and-execution-ladder.md)). Schema sketch: [eval-stubs/activity_readiness.v0.json](./eval-stubs/activity_readiness.v0.json).

## Programme order

Harbour implementation is **later** than the Observatory-first sprint and later than `DecisionPosition` ([POLARIS-SEARCH-01](../../tickets/polaris/POLARIS-SEARCH-01-decision-position.md)). Life Script startup graphs are specified on [RECON-07](../../tickets/recon/RECON-07-life-scripts.md) so the HOW exists before Harbour types consume it. PolarIS internal ticket graph is unchanged.

## Out of scope

- Runtime, UI, or a Home-page Harbour
- Star names; `class Harbour`; a Council seat
- ADR-049 (still reserved unused — Council did not take it; Harbour does not take it either)
- Profiling, hidden optimisation, or environment changes without an explicit advisory proposal ([HARBOUR-03](../../tickets/harbour/HARBOUR-03-friction-learning.md))
- Replacing Recipes ([ADR-024](../adr/024-shareable-recipes-procedure-never-personal-state.md)), Next Action, or PolarIS search
