# ADR-047: Executive motifs and search efficiency — not personality profiling

## Status

Accepted (docs only; no runtime)

## Date

2026-08-22

## Context

Search over a human Context Graph is expensive if every position is treated as novel. Chess engines reuse **opening books**, **move ordering**, **pruning**, **transposition tables**, and **quiescence search**. Enigma already has two related, **different** objects:

| Object | Meaning | Must not become |
| --- | --- | --- |
| **C12 Life Scripts** | Product-acceptance episodes: Alex lives an ordinary fictional day through Enigma | A hidden person model; architecture-named utterances |
| **ADR-024 Recipes** | Shareable declarative procedures over named capabilities | Personal state, executable code, prompt packs |

Polaris needs a third object: **recurring executive-function positions** and **reusable strategy priors** that make search cheap without profiling who the user “is.”

## Decision

### Executive motifs (recurring positions)

A **motif** is a class of `DecisionPosition`, not a personality trait. First corpus is **Alex synthetic data** (never Oscar’s inbox):

| Motif (examples) | Observable situation |
| --- | --- |
| Double-booked | Two hard calendar intervals overlap |
| Waiting-on-someone | Next real step is an external dependency |
| Deadline compression | Multiple real dues share a short window |
| Blocked-task | Work cannot start without a missing artefact / reply |
| Low-energy / high-effort mismatch | Capacity signals vs a heavy candidate ([ADR-011](./011-observable-support-challenges-only.md) situational tags) |
| Transition / switching cost | Imminent calendar boundary |
| Overwhelm / too many threads | Many OPEN loops; initiation is the bottleneck |

Motifs are **evaluator- and search-facing**. They are not written onto the person record. No `ALEX_BIOGRAPHY.md`. No ADHD flag in runtime ([ADR-011](./011-observable-support-challenges-only.md)).

### Strategy scripts (opening-book metaphor)

Polaris may keep **strategy scripts**: reusable, inspectable move-ordering / prune priors for a motif (“when double-booked, try resolve-conflict and ask-user before starting deep work”).

**Naming freeze:** product-acceptance YAML remains **Life Scripts** ([C12](../../tickets/conversational-ui/C12-life-scripts.md)). Polaris opening-book priors are **strategy scripts** in tickets and code. Informal speech may analogise them to an opening book; implementers must not overwrite C12 files or treat episode YAML as a psych dossier.

Recipes ([ADR-024](./024-shareable-recipes-procedure-never-personal-state.md)) may later *bind* as legal procedures inside a script. Scripts cannot grant authority.

### Search efficiency (safe reuse)

| Device | Allowed use | Forbidden use |
| --- | --- | --- |
| **Move ordering** | Try motif-prior legal moves first | Hide illegal moves |
| **Pruning** | Drop dominated / low-consequence / low-uncertainty branches | Drop rest/wait because they score “unproductive” |
| **Transposition-style reuse** | Reuse eval for the same `DecisionPosition` key | Reuse a line after invalidating evidence |
| **Quiescence** | Extend search in unstable / forcing positions (conflict, deadline cliff, blocker just arrived) | Infinite search; user-facing “still thinking” theatre |

Minimum sufficient decision state is the reuse key ([ADR-045](./045-decision-position-moves-legality.md)). Chat transcripts are not.

### Never personality profiling

Strategy scripts encode **what to try when this situation obtains**, not **what kind of person this is**. Tone memory ([ADR-025](./025-tone-memory-how-to-speak-not-who-you-are.md)) remains how to speak. Relational bootstrap is continuation mechanics, not a hidden self.

## Consequences

- [POLARIS-SEARCH-05](../../tickets/polaris/POLARIS-SEARCH-05-executive-motifs.md) owns motifs, strategy-script priors, and safe reuse.
- [ALEX-EVAL-01](../../tickets/demo-evaluation/ALEX-EVAL-01-life-positions.md) turns Alex arcs into replayable positions labelled with motifs + invariants.
- C12 Life Scripts stay the product test of ordinary life; they are a **source of positions**, not the opening book itself.

## Alternatives considered

| Alternative | Why rejected |
| --- | --- |
| Reuse the name Life Scripts for opening books without qualification | Collides with C12 constitutional meaning |
| User embedding / personality vector as prior | Secret profile; ethics creed fail |
| Hard-code “Alex is avoidant so never suggest admin” | Diagnosis in runtime; not generalisable |
| Skip motifs until My Enigma | Alex is the safe corpus; waiting on Oscar data is the wrong order |

## Related

- [polaris-search.md](../architecture/polaris-search.md)
- [ADR-011](./011-observable-support-challenges-only.md) · [ADR-024](./024-shareable-recipes-procedure-never-personal-state.md) · [ADR-025](./025-tone-memory-how-to-speak-not-who-you-are.md) · [ADR-026](./026-ethics-creed-user-is-subject.md)
- [C12](../../tickets/conversational-ui/C12-life-scripts.md) · [executive-function-support-benchmark.md](../architecture/executive-function-support-benchmark.md)
