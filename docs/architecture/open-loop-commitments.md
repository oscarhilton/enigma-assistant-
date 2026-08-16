# Open-loop commitments (memory ↔ attention bridge)

**Status:** Design note + ticket scaffold ([SE11](../../tickets/shadow/SE11-open-loop-due-resolution.md))  
**Related:** [shadow-silence-evaluation.md](./shadow-silence-evaluation.md) · obligations tickets M15/M16 · attention engine  
**Product rule:** A durable open-loop fact is **not** an attention card.

## Problem

Commitments and open loops are easy to conflate with “interrupt the user now.” That produces either:

- nagging whenever a due exists, or
- silent miss when a real open loop never becomes an attention decision.

Enigma needs a clean bridge: **memory stores the fact; attention decides whether today is the day to speak.**

## Durable fact ≠ attention card

| Layer | Owns | Does not own |
| --- | --- | --- |
| Memory / obligations | That a commitment exists; evidence; due phrase; resolved due; status | Whether to interrupt now |
| Attention policy | Whether / when to surface over the week | Rewriting whether the commitment is real |

Having `due_at` populated must **not** by itself enqueue a surface. Silence about an open loop is still a **prediction** and should be logged when the candidate is considered ([shadow-silence-evaluation.md](./shadow-silence-evaluation.md)).

## Human due phrase + deterministic resolve

Store both:

1. **Human due phrase** — what the user (or evidence) said (`"before Friday"`, `"end of next week"`).
2. **Resolved due** — a concrete calendar date/time computed by a deterministic resolver relative to evidence time / wall clock.

Example:

- Evidence observed Saturday **14 March**
- Phrase: `"before Friday"`
- Resolved due: **Friday 20 March** (next Friday after the observation, unless policy defines same-week Friday when still in the future)

Resolver rules belong in `packages/obligations` (or domain helpers it owns). They must be testable without a model call. Ambiguous phrases may leave `due_resolved_at` null and set status/`uncertain` flags rather than inventing a date.

## Rename “Last” → Last evidence / Last observed

UI and schemas that currently say **Last** for commitment freshness should prefer:

- **Last evidence** — latest supporting source artefact
- **Last observed** — latest time Enigma saw confirming or conflicting signal

Avoid implying “last time we nagged” or “last attention surface.”

## Three axes (orthogonal)

A single open loop can be high-confidence, still open, and correctly suppressed:

| Axis | Question | Example values |
| --- | --- | --- |
| **CONFIDENCE** | Does this commitment exist? | `0.90` |
| **STATUS** | Lifecycle of the loop | `OPEN` · `RESOLVED` · `CANCELLED` · `UNCERTAIN` |
| **ATTENTION** | Surface **now**? | `SURFACE` · `SUPPRESSED` · `DEFERRED` |

Valid combination:

```text
confidence = 0.90
status     = OPEN
attention  = SUPPRESSED
```

That means: Enigma believes the commitment is real and unresolved, and predicts the user does not need an interruption **today**. Shadow silence evaluation audits that prediction; it does not delete the memory fact.

## Memory UI vs privacy / model view

| Surface | Naming |
| --- | --- |
| Memory UI (local, private) | Real display names the user already has in Contacts / mail headers (subject to OS permissions) |
| Privacy inspector / remote model view | Keep `USER` / `PROJECT_B` / `PERSON_*` tokens |

Do not send real names or wholesale Notes to hosted models. Tokenisation remains the remote contract ([privacy-model.md](./privacy-model.md)).

## Attention over the week

Attention policy may schedule:

- early soft awareness
- mid-week nudge
- day-of escalation
- deliberate silence while status stays `OPEN`

Memory continues to show the open loop in browse/search. **Browse ≠ interrupt.**

## Ticket / package boundary

Implementation scaffold: [SE11](../../tickets/shadow/SE11-open-loop-due-resolution.md).

| May edit | Must not |
| --- | --- |
| `packages/obligations/**`, domain commitment fields as needed, focused tests | Demo attention UI, Gmail OAuth, Shadow env enum, full Memory product redesign |

Soft-depends on M16 commitment tracking (already `done`) and Shadow silence tickets only where suppress decisions reference open-loop candidates.
