# ADR-045: DecisionPosition — life position, candidate moves, and legality

## Status

Accepted (docs only; no runtime)

## Date

2026-08-22

## Context

Chess engines search over a **position**, **legal moves**, and an **evaluation**. Enigma has world state (obligations, commitments, attention, availability, blockers) but not yet a **minimum sufficient decision state** that search can hash, compare, and replan from.

Two failure modes to avoid:

1. Dumping the vault, mail, or a biography into the searcher (“the whole life is the board”).
2. Letting a language model declare what is real or what is allowed.

Existing doctrine already points at the right shape: abstract state, not biography ([ADR-023](./023-persistent-shadow-abstract-state-not-biography.md)); request-shaped compilation ([ADR-029](./029-context-compilation-request-shaped-memory.md)); capability-scoped permission ([ADR-015](./015-capability-scoped-disclosure-not-data-access.md)); recipes as procedure over named capabilities ([ADR-024](./024-shareable-recipes-procedure-never-personal-state.md)).

## Decision

### Context Graph is canonical decision-relevant state

The **Context Graph** is Enigma’s structured, purpose-bound graph of what still matters for choice: obligations, open loops, blockers, availability, attention qualification, resource/energy suitability signals, consent and authority facts, and typed stimulus that invalidates them.

It is **not** a second archive, not a personality model, and not the remote prompt. Stimulus (ingest, clock, attestation, execution receipts, user reject/accept) updates the graph. Search reads a compiled projection of it.

### `DecisionPosition`

Polaris compiles the Context Graph into a stable typed **`DecisionPosition`**: the minimum decision-relevant snapshot for one search. Same position ⇒ same legal move set (given the same capability grant). It is a **transposition key**, not a diary.

Minimum contents (illustrative, not a schema freeze):

| Field | Role |
| --- | --- |
| Clock / horizon | Injected clock ([ADR-006](./006-clock-injection.md)); near-term windows |
| Open obligations / loops | What is still unresolved |
| Blockers / waiting-on | External dependencies |
| Availability / conflicts | Calendar as situation, not as obligation ([attention-surface.md](../architecture/attention-surface.md)) |
| Attention qualification | NEEDS YOU vs CONTEXT vs CAN WAIT — not merged into moves |
| Resources | Time, effort budget, energy suitability (observable, not a diagnosis) |
| Authority facts | What rungs are granted for which capabilities |
| Provenance refs | Evidence / assertion ids that would invalidate the position |
| Assumptions | Explicit, typed, falsifiable |

Do **not** include raw mail bodies, Notes wholesale, `PrivatePerson`, diagnostic labels ([ADR-011](./011-observable-support-challenges-only.md)), or conversational chain-of-thought.

### Candidate moves come from capabilities

**Foundry** enumerates **candidate moves** from named capabilities (query, prepare, communicate, wait, rest, nothing, ask-the-user, …). A move is a typed, bounded action plus predicted local effects — not English advice.

Shareable recipes ([ADR-024](./024-shareable-recipes-procedure-never-personal-state.md)) may later appear as **procedure-shaped move generators**. They still bind to *this* user’s graph locally and still cannot skip authority.

### Legality is not ranking

A move is **legal** only if all of the following hold:

1. **Authority** — required rung is granted (READ / PREVIEW / PREPARE / COMMIT mapped in [ADR-044](./044-receding-horizon-action-search.md)).
2. **Consent** — bilateral / disclosure rules ([ADR-016](./016-bilateral-consent-and-shared-commitments.md) · [ADR-018](./018-disclosure-ledger-and-inference-attack-protection.md)).
3. **Resources** — time, tools, and energy suitability make the move physically available *now*.
4. **Constraints** — user goals, hard calendar conflicts, policy, Demo/Private/Shadow roots.

Illegal moves are **out of the tree**, not “low score.” Semantic models may propose or order candidates; they **do not** define reality or permission.

```text
Context Graph
    ↓ compile
DecisionPosition
    ↓ Foundry capabilities
Candidate moves
    ↓ authority / consent / resources / constraints
Legal moves
    ↓ Polaris search ([ADR-044](./044-receding-horizon-action-search.md))
Principal variation (hypotheses)
    ↓ ply-0 only, if authorised
PREPARE / COMMIT
```

## Consequences

- [POLARIS-SEARCH-01](../../tickets/polaris/POLARIS-SEARCH-01-decision-position.md) owns `DecisionPosition` compilation.
- [POLARIS-SEARCH-02](../../tickets/polaris/POLARIS-SEARCH-02-move-generation-legality.md) owns candidate generation + legality filter.
- Core continues to reason in domain objects, not `EKEvent` shapes.
- Transposition-style reuse ([ADR-047](./047-executive-motifs-and-search-efficiency.md)) keys on `DecisionPosition`, not on chat transcripts.

## Alternatives considered

| Alternative | Why rejected |
| --- | --- |
| Search over raw sources / vault dump | Biography; violates select-first and SEC-07 |
| Model emits “the board” in prose | Model as truth; untyped; not hashable |
| Rank illegal moves instead of filtering | Permission becomes a score; silent authority leak |
| One global life-state object | Competes with vault / inventory; curiosity-as-retention |

## Related

- [polaris-search.md](../architecture/polaris-search.md)
- [ADR-015](./015-capability-scoped-disclosure-not-data-access.md) · [ADR-019](./019-delegated-authority-and-execution-ladder.md) · [ADR-023](./023-persistent-shadow-abstract-state-not-biography.md) · [ADR-024](./024-shareable-recipes-procedure-never-personal-state.md) · [ADR-029](./029-context-compilation-request-shaped-memory.md)
