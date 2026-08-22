# Council — advisory projection, not a second mind

**Status:** Approved product language — documentation only; no runtime  
**Date:** 2026-08-22  
**Carried by:** [NORTHSTAR-SEARCH-DOCS](../../tickets/northstar/NORTHSTAR-SEARCH-DOCS.md) (no extra ticket)  
**Search constitution:** [polaris-search.md](./polaris-search.md) · [ADR-044](../adr/044-receding-horizon-action-search.md)–[048](../adr/048-structured-search-trace-and-lens.md)

> **The Council serves the user; it does not govern them.**  
> **No member of the Council possesses truth independently of Enigma's evidence.**  
> **Polaris chairs the Council but does not overrule the user's will.**  
> **Mythology is a product/interface ontology, not a replacement for typed architecture.**

This page does not authorise a Council UI, extra agents, extra vaults, or star-named types. Functional seats come **before** names.

## Brand thesis (product language, not a technical invariant)

> Enigma understands the sky. The Council reads it. Polaris shows the way. The Goose brings the answer.

Compact hierarchy:

```text
USER
  ↓ authors the life; retains COMMIT
POLARIS                         chair / navigator — what matters now; next bounded move
  ↓ aggregates specialist assessments
COUNCIL                         advisory projection over ONE Enigma state
  ↓ stellar lenses (orient) · planetary imagery (embody state)
ENIGMA                          hidden cognitive substrate · canonical world model
  ↓
VAULT                           protected retained memory (user-controlled, forgettable)
GOOSE                           familiar / courier / messenger — no authority
FOUNDRY                         invisible model externalised into matter / effectors
```

Star names (Aldebaran, Spica, …) are **copy aliases**. Internals stay `ContextGraph`, `DecisionPosition`, `CandidateMove`, `PrivateVault`, `RetentionDecision`, `SemanticRecall`, factor ids below. Do **not** rename packages after gods.

## Architecture-first mapping

| Product | Typed home | Must not |
| --- | --- | --- |
| **Enigma** | World model, Context Graph, compiler, policy ([ADR-020](../adr/020-llm-conversational-boundary-not-truth.md) · [ADR-029](../adr/029-context-compilation-request-shaped-memory.md)) | A character with separate opinions; a second biography |
| **Vault** | Governed retained memory ([ADR-022](../adr/022-private-vault-storage.md) · [ADR-036](../adr/036-retention-gate-life-memory.md)) | Gossip, secret profile, Council-owned store |
| **Council** | Structured specialist **assessments** over one `DecisionPosition` ([ADR-046](../adr/046-local-evaluation-under-uncertainty.md)) | Separate memories, agents, truths, or votes that bind the user |
| **Polaris** | Receding-horizon search + ply-0 recommendation ([ADR-044](../adr/044-receding-horizon-action-search.md)) | Override the user; define reality; execute |
| **Goose** | Evidence courier / work projection (historical ADR-034 satchel; C14 hops) | Independent authority; masking missing evidence |
| **Foundry** | Named capabilities, legality, governed effects — later physical/UI manifestation ([ADR-044](../adr/044-receding-horizon-action-search.md) · [ADR-019](../adr/019-delegated-authority-and-execution-ladder.md)) | A second searcher or world model |
| **Lens** | Inspectable PV + Council assessments ([ADR-048](../adr/048-structured-search-trace-and-lens.md)) | Chain-of-thought; click-to-COMMIT |
| **Observatory** | Programme truth registry + engineering UI ([observatory.md](./observatory.md)) | A Council seat, Home constellation, or sky theatre |

Conversational **Assistant** remains the language boundary ([ADR-020](../adr/020-llm-conversational-boundary-not-truth.md)): it understands and speaks. It is not a rival chair and not Enigma. Product copy may let Polaris “show the way” without putting search authority in the LLM.

North Star still forbids a theme-park cast ([north-star.md](./north-star.md)). Council members are **inspectable lenses**, not a front-page sitcom. Do not add Aldebaran/Spica/Canopus to the always-visible layer.

## Stars guide; planets embody

| Imagery | Means in product | Typed analog |
| --- | --- | --- |
| **Stellar figures** | Advisory / orienting lenses (how a specialist *reads* this position) | Factor families / assessments on a node |
| **Planetary / gas-giant imagery** | Embodied forces and *state* — energy, appetite, exertion, recovery, emotion (only if attested), momentum | Observables on `DecisionPosition` — **not** extra planners |

Planets do not vote. They are circumstances the lenses read.

## Functional Council v1 (names after function)

Polaris **aggregates**; specialists **assess**. No majority vote that binds COMMIT. Seats are earned by measurable decision impact on Alex positions, not by a complete zodiac.

| Seat | Function | Status | Product-name candidate | Internal id |
| --- | --- | --- | --- | --- |
| Navigation / executive prioritisation | What matters now; next bounded legal move | **Definite** (chair) | **Polaris** | `navigation` (chair, not a peer voter) |
| Body / training | Physical capability, training state, session fit, momentum, constraints | **Definite** | Aldebaran (strong) | `body` |
| Nourishment | Food, hydration, meal timing, available fuel, groceries/ingredients, explicit nutrition goals | **Likely definite** | Spica (strong) | `nourishment` |
| Recovery / sustainability | Sleep, fatigue, rest, workload, sustainable pacing | **Definite** | Canopus (strong) | `recovery` |
| People / social | Promises, unanswered coordination, commitments affecting others, social consequence | **Likely seat** | **TBD** — do not freeze a star | `people` |
| Craft / work / making | Project momentum, context-switch cost, blockers, deadlines, coherent units of work | **Likely seat** | **TBD** — do not freeze a star | `craft` |
| Stewardship / resources | Bills, admin, renewals, household, resource constraints | **Candidate** | Earn via scenarios; do not force | `stewardship` |
| Herald / forcing-change | Notices important state changes; can trigger replan / quiescence | **Not a voting peer** | Sirius (better as Herald) | `herald` |
| Chronicle / long horizon | Trajectory over months | **Optional projection** | Vega — not a core seat | `chronicle` |

`herald` maps to stimulus → invalidation / quiescence ([ADR-044](../adr/044-receding-horizon-action-search.md) replan · [BRAIN-03](../../tickets/conversational-ui/BRAIN-03-live-recalculation.md)), not to a value head that outranks `recovery` or `craft`.  
`chronicle` must not widen the working set “just in case” ([ADR-023](../adr/023-persistent-shadow-abstract-state-not-biography.md) · [ADR-029](../adr/029-context-compilation-request-shaped-memory.md)).

## Goose: incomplete picture over hallucination

THE Goose fetches, carries, explains uncertainty and failures, replays what the system **found**, and may provide warmth. It has **no independent authority**.

If a source cannot be read, Goose (and the trace) must say the picture is **incomplete**. Polaris must not invent a free afternoon. Example:

- Calendar access fails or coverage is inadequate → ply-0 is not “you’re free; start deep work.”  
- Trace: `coverage_adequate: false` (historical satchel rule). Goose copy may HONK / carry an empty satchel; it must not smile the gap away.

Empty cupboard ≠ empty house. Distress may increase supportiveness, never authority ([ADR-028](../adr/028-conversational-constitution-attestation-dialogue-support.md)).

## Lens / Brain programme

Alex Lab Lens ([ADR-048](../adr/048-structured-search-trace-and-lens.md)) shows **structured** Council assessments: specialist factor families, candidate branches, principal variation, provenance, uncertainty, and **which lenses materially changed ranking**. Not hidden chain-of-thought. Not “Aldebaran felt tired.”

## Earning seats on Alex (docs fixtures)

Do not edit `scenarios/alex-v1` timeline in this wave. Positions live as evaluator-only sketches ([ALEX-EVAL-01](../../tickets/demo-evaluation/ALEX-EVAL-01-life-positions.md) · [life_position.v0.json](./eval-stubs/life_position.v0.json)). A seat is earned when ablating that lens **changes** ply-0 (or `must_consider`) on a frozen position — never via a universal life score or moral ranking of Alex.

## Out of scope

- Runtime Council objects, star-named classes, extra vaults
- Voting that bypasses Assist COMMIT
- Personality profiling; planetary “mood” as diagnosis
- Replacing Cortex, C12 Life Scripts, or the conversational constitution
- New named Council members to decorate an Observatory graph; Observatory is not a seat
