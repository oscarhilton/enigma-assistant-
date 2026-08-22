# ADR-048: Structured search trace and Lens — introspection, not chain-of-thought

## Status

Accepted (docs only; no runtime)

## Date

2026-08-22

## Context

Users (and eval) need to see **why** Polaris offered a next move. Two existing surfaces already forbid fake cognition:

- **Cortex** ([cortex-visualizer.md](../architecture/cortex-visualizer.md) · [C10](../../tickets/conversational-ui/C10-cortex-brain-visualizer.md)): system events and data movement. Preferred product name is **Cortex**, not “Brain View.” It must never show LLM chain-of-thought. Frozen: Cortex observes Enigma; it is not a control plane.
- **C14 activity stream**: public-effect hops, not theatrical thoughts.

C39 already freezes the sibling rule for agent handoff: **pass the conclusion, preserve the evidence, discard the deliberation.**

Polaris still needs a **typed search trace** — Stockfish-style principal variation over structured state — without resurrecting “Brain View” as a mind that thinks about the user.

## Decision

### Typed decision trace (machine-readable)

Every search emits a **structured trace**, not a prose monologue. Minimum vocabulary:

| Field | Meaning |
| --- | --- |
| Position id / `DecisionPosition` key | What was searched |
| Candidate moves | Generated, with capability ids |
| Rejected / pruned | Reason codes (illegal, dominated, motif prune, budget) |
| Evidence refs | Assertion / source handles that support a node |
| Uncertainty | Typed; fades with depth |
| Assumptions | Explicit, falsifiable |
| Principal variation | Best line **as hypotheses**, ply 0 authorised separately |
| Alternatives | Next-best legal lines |
| Authority | Rung required vs granted per move |
| Invalidation triggers | Which stimulus would stale this tree |
| Specialist assessments | Per-lens factor bundles (`body`, `nourishment`, `recovery`, `people`, `craft`, …) with evidence refs |
| Ranking attribution | Which lens ids **materially changed** ply-0 vs a baseline without them |
| Coverage | Source/capability adequacy (calendar failed → incomplete picture, not a free day) |

Deliberation text, hidden chain-of-thought, and “THE Goose wondered whether…” / “Aldebaran felt tired” are **not** trace fields. Models may help *fill* typed slots; the slots remain the product. Council assessments are this structured payload — not inner lives.

### Lens (PV explorer) vs Cortex vs C30 Brain

| Surface | Question | Programme |
| --- | --- | --- |
| **Cortex** (C10) | What did Enigma *do* (ingest, qualify, egress, forget)? | Observability |
| **C30 Brain / inventory** (historical, not on `main`) | What does Enigma *remember* and why? | Memory projection |
| **Lens** (this ADR) | What lines did Polaris *search*, with confidence fading by depth, plus structured Council assessments? | Search introspection |

Ticket ids **BRAIN-01…03** name the programme. **Product copy in Alex Lab is Lens** (principal-variation explorer). Do not ship “Brain View” as theatrical inner life. Lens may be nicknamed Brain View in internal tickets; it still shows **structured specialist factors, branches, PV, provenance/uncertainty, and ranking attribution** — never hidden CoT. Do not operate Enigma by clicking a node to COMMIT ([C10](../../tickets/conversational-ui/C10-cortex-brain-visualizer.md) frozen rule still holds: inspect ≠ control plane). PREVIEW of a line is allowed; COMMIT stays Assist.

### Planner evaluation

The eval catalogue becomes replayable **life positions** ([ALEX-EVAL-01](../../tickets/demo-evaluation/ALEX-EVAL-01-life-positions.md)): same `DecisionPosition`, expected **invariants** (must-not-illegal, must-consider, must-not-poor), not one exact move. [ALEX-EVAL-02](../../tickets/demo-evaluation/ALEX-EVAL-02-planner-tournament.md) compares planners on those positions, including a **shadow-safe** comparison against the current Next Action planner ([ADR-010](./010-next-action-not-attention.md)).

Traces are the regression artefact. They must be deterministic given position + planner version + clock.

### Live invalidation

When evidence or state changes, the tree is **recomputed**. Stale branches are marked invalid in Lens — never silently shown as current ([BRAIN-03](../../tickets/conversational-ui/BRAIN-03-live-recalculation.md)).

## Consequences

- [BRAIN-01](../../tickets/conversational-ui/BRAIN-01-structured-search-trace.md) owns the trace schema and feed.
- [BRAIN-02](../../tickets/conversational-ui/BRAIN-02-pv-explorer.md) owns the Alex Lab explorer (current position, best line, alternatives, fading confidence, specialist factors, which lenses changed ranking, provenance, assumptions, invalidation triggers).
- Remote prompts still must not receive the raw trace as a second biography ([ADR-029](./029-context-compilation-request-shaped-memory.md)).
- This ADR does not authorise wiring Cortex as a search UI, nor restoring missing C30 files.

## Alternatives considered

| Alternative | Why rejected |
| --- | --- |
| Show model chain-of-thought as Brain View | Fake mind; ethics anthropomorphism fail; untestable |
| Reuse Cortex event log as the search tree | Wrong grain; Cortex is what *happened*, not hypothetical plies |
| Store deliberation prose as durable memory | C39 fossil problem; SEC-07 reconstructability |
| Click-to-execute from Lens | Makes observability a control plane |

## Related

- [polaris-search.md](../architecture/polaris-search.md) · [council.md](../architecture/council.md) · [cortex-visualizer.md](../architecture/cortex-visualizer.md)
- [ADR-020](./020-llm-conversational-boundary-not-truth.md) · [ADR-026](./026-ethics-creed-user-is-subject.md) · [ADR-029](./029-context-compilation-request-shaped-memory.md)
- [C10](../../tickets/conversational-ui/C10-cortex-brain-visualizer.md) · [C14](../../tickets/conversational-ui/C14-conversation-activity-stream.md) · [C39](../../tickets/conversational-ui/C39-handoff-working-conclusion.md)
