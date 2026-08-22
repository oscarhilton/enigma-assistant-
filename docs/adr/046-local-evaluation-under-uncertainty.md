# ADR-046: Local evaluation under uncertainty — no universal life score

## Status

Accepted (docs only; no runtime)

## Date

2026-08-22

## Context

Chess engines can collapse a position to a single centipawn score because the game has a shared terminal objective. A human life does not. A universal “life score” would:

- silently pick whose values count;
- turn Enigma into an optimiser of the person ([ADR-026](./026-ethics-creed-user-is-subject.md));
- punish rest, waiting, and legitimate silence ([ADR-010](./010-next-action-not-attention.md) · [ADR-009](./009-silence-as-prediction.md));
- invite diagnostic or personality labels as features ([ADR-011](./011-observable-support-challenges-only.md)).

N01 already sketches a **local** fitness product (usefulness × actionability × contextual fit × capacity × time fit × novelty penalty), with urgency multiplying **only when urgency exists**. Polaris needs the same idea at tree nodes: evaluate **this user’s local future state**, not a global ranking of lives.

Policy (what may be done) stays separate from value (how a legal future looks). That split already won the reasoning gate ([ADR-012](./012-reasoning-value-gate-decision.md)).

## Decision

### No universal life score

Polaris evaluates **local successor positions** relative to the user’s explicit goals, constraints, and current circumstances. There is no scalar “how good is this life.” REST / NOTHING / wait remain first-class outcomes.

### Evaluation factors (open list, not a personality model)

A node may be described with typed, inspectable factors. Illustrative catalogue — implementers may subset; they must not add covert psychometrics:

| Factor | Question |
| --- | --- |
| Urgency | Does delay actually cost, or are we faking Priority? |
| Consequence | What breaks if this branch is wrong? |
| Effort | Size of the ply-0 action |
| Switching cost | Context-switch tax from the current position |
| Momentum | Is a thread already in motion? |
| Energy suitability | Observable capacity fit — not a diagnosis |
| Uncertainty reduction | Does this move buy information that unblocks others? |
| Reversibility | Can the user undo cheaply? |
| Optionality | Does the move keep later choices open? |
| Blockers released | Does it free other work? |
| Social consequence | Relationship / commitment effects the user already owns |

Factors are **evidence-linked**. They are not vibes and not chain-of-thought.

### Specialist lenses (Council projection)

The same factors group into **functional lenses** — the Council’s assessments over one `DecisionPosition` ([council.md](../architecture/council.md)). Lenses are not extra evaluators of record and not extra memories.

| Internal id | Function | v1 seat |
| --- | --- | --- |
| `navigation` | Chair aggregate: what matters now; ply-0 | Polaris (chair, not a peer vote) |
| `body` | Training / physical capability / session fit | Definite (product alias Aldebaran) |
| `nourishment` | Fuel, meal timing, groceries, explicit nutrition goals | Likely definite (Spica) |
| `recovery` | Sleep, fatigue, rest, sustainable pacing | Definite (Canopus) |
| `people` | Promises, unanswered coordination, social consequence | Likely; **name TBD** |
| `craft` | Project momentum, switch cost, blockers, coherent units | Likely; **name TBD** |
| `stewardship` | Bills / admin / household / resource constraints | Candidate — earn via Alex scenarios |
| `herald` | Forcing-change detector; replan / quiescence | Sirius-as-Herald — **not** a voting peer |
| `chronicle` | Long-horizon trajectory | Optional projection (Vega) — not a core seat |

Star names are product copy only. Types stay `body`, `recovery`, … Polaris may aggregate lens outputs; it must not emit a moral ranking of the person. Ablating a lens on an Alex position must be able to **change ply-0** or the lens is not yet earned.

`herald` is stimulus/invalidation, not a value head. `chronicle` must not load months of biography into the working set.

### Uncertainty × consequence controls search effort

Search budget (depth, branching, quiescence) scales with **how uncertain the node is** times **how bad a mistake would be**. Low-stakes, high-certainty positions stay shallow. Forcing / unstable positions spend more ([ADR-047](./047-executive-motifs-and-search-efficiency.md) quiescence).

### Policy / prior ≠ value / evaluation

| Object | Answers | Must not |
| --- | --- | --- |
| **Policy / legality** | May this move be considered? | Quietly become a score |
| **Move-ordering prior** | Which legal moves to try first? | Hide illegal moves as “low value” |
| **Local evaluation** | How does this successor look *for this user, now*? | Optimise engagement, throughput, or a vendor outcome |

Semantic models may propose factor estimates. Deterministic policy still decides interruption and authority. Evaluator labels (`MUST_SURFACE`, …) stay evaluator-only ([ADR-011](./011-observable-support-challenges-only.md)).

## Consequences

- [POLARIS-SEARCH-03](../../tickets/polaris/POLARIS-SEARCH-03-local-evaluator.md) implements user-relative local eval; it must not emit a global life score.
- N01 remains the current Next Action stub; Polaris eval is a later, richer local function, not a replacement of the three-level surface.
- Benchmarks assert **invariants** on factors and illegal/poor moves, not one exact “best move” ([ALEX-EVAL-01](../../tickets/demo-evaluation/ALEX-EVAL-01-life-positions.md)).
- Energy / capacity signals are situational. They must not become `adhd: true` on the person record.

## Alternatives considered

| Alternative | Why rejected |
| --- | --- |
| Single centipawn-style life score | Implicit values; ethics creed fail |
| Maximise completed tasks | Productivity treadmill; rest becomes a bug |
| Let the LLM be the evaluator of record | Authority in the model; unreplayable |
| Fold policy into the value head | Illegal-but-high-value moves leak into user output |

## Related

- [polaris-search.md](../architecture/polaris-search.md) · [council.md](../architecture/council.md)
- [ADR-010](./010-next-action-not-attention.md) · [ADR-011](./011-observable-support-challenges-only.md) · [ADR-012](./012-reasoning-value-gate-decision.md) · [ADR-026](./026-ethics-creed-user-is-subject.md)
- [next-action.md](../architecture/next-action.md) · [executive-function-support-benchmark.md](../architecture/executive-function-support-benchmark.md)
