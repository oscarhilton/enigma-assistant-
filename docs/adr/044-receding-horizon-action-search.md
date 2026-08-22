# ADR-044: Receding-horizon action search — search deeply, act shallowly, replan constantly

## Status

Accepted (docs only; no runtime)

## Date

2026-08-22

## Context

Enigma already separates **what needs you** from **what is worth doing** ([ADR-010](./010-next-action-not-attention.md)), holds **world truth and execution** in core rather than in a model ([ADR-020](./020-llm-conversational-boundary-not-truth.md)), and compiles **request-shaped** context rather than loading a life ([ADR-029](./029-context-compilation-request-shaped-memory.md)). Next Action scoring ([next-action.md](../architecture/next-action.md) · N01) ranks a local candidate for *now*. It does not yet search a tree of *later*.

A tempting product story is that Enigma “thinks 20 moves ahead” and then commits the user to that line. That would:

- fake certainty about a life that is not a chess position with perfect information;
- treat search depth as a user promise or a granted plan;
- silently optimise a person rather than help them choose ([ADR-026](./026-ethics-creed-user-is-subject.md));
- collapse PREPARE into COMMIT.

The missing constitution is **receding-horizon search**: look far enough to choose the next legal move well; authorise only that move; replan when the world changes.

This ADR names **Polaris** as that search engine **and** as the product chair/navigator over specialist assessments ([council.md](../architecture/council.md)). It does not replace Enigma, Attention, Next Action, Assist, or the LLM conversational boundary. Architecture: [polaris-search.md](../architecture/polaris-search.md).

## Decision

### Motto

> **Search deeply. Act shallowly. Replan constantly.**

Planning depth may exceed execution depth. Iterative deepening is the default search schedule. Only the next **bounded** action may be authorised. Future branches lose confidence with depth. “Twenty moves ahead” is an **internal search budget**, never a deterministic promise and never a user commitment.

### Layers (do not collapse)

| Layer | Owns | Must not |
| --- | --- | --- |
| **Enigma** | Hidden cognitive substrate; canonical world model; compiler; policy | Be a character with separate opinions; optimise a life |
| **Vault** | Protected retained memory — user-controlled, forgettable, provenance-aware | A Council-owned second store; gossip |
| **Council** | User-facing advisory **projection** of specialist lenses over one Enigma state | Separate memories, agents, truths, or sovereign decisions |
| **Polaris** | Chair / navigator: receding-horizon search; next bounded move | Override the user; define reality; execute |
| **Goose** | Familiar / courier: fetch, carry, explain gaps | Independent authority; mask missing evidence |
| **Foundry** | Capabilities + governed effects; later physical/UI externalisation of the model | A second searcher; skip READ → PREVIEW → PREPARE → COMMIT |

Mythology is product/interface ontology. Internals stay `ContextGraph`, `DecisionPosition`, `CandidateMove`, `PrivateVault`, … ([council.md](../architecture/council.md)).

Semantic models may **propose or rank** candidate lines. They do not define the position, legality, or permission ([ADR-020](./020-llm-conversational-boundary-not-truth.md) · [ADR-012](./012-reasoning-value-gate-decision.md): semantics yes, authority no).

Polaris may **aggregate** specialist assessments. It never overrules the user's will. The Council serves the user; it does not govern them.

### Horizon rules

1. **Search depth ≠ execution depth.** The engine may evaluate a principal variation of many plies; the product may offer only the first legal, authorised step.
2. **Iterative deepening.** Shallow complete searches before deeper ones. Time / uncertainty / consequence ([ADR-046](./046-local-evaluation-under-uncertainty.md)) bound effort.
3. **Next-action-only execution.** Authorising ply 0 does not authorise ply 1. Replan after every committed effect, attestation, or invalidating stimulus.
4. **Confidence fades with depth.** Deeper nodes are hypotheses, not plans the user is “on.”
5. **Silence remains legitimate.** An empty Attention surface ([ADR-009](./009-silence-as-prediction.md)) may still have a WORTH DOING Next Action, including REST / NOTHING. Search must not manufacture urgency to fill a tree.

### Authority (map, do not replace)

Polaris does not get a new ladder. Search may **READ** a `DecisionPosition` ([ADR-045](./045-decision-position-moves-legality.md)), **PREVIEW** a principal variation, **PREPARE** an Assist, and **COMMIT** only through existing Assist + execution ([ADR-019](./019-delegated-authority-and-execution-ladder.md) · [ADR-028](./028-conversational-constitution-attestation-dialogue-support.md) · [ADR-029](./029-context-compilation-request-shaped-memory.md)):

| Search word | Existing rung / speech act |
| --- | --- |
| **READ** | A0 inspect; `READ` / `SUPPORT` tools |
| **PREVIEW** | Structured line the user can see (A3 preview / Cortex / Lens) — not execution |
| **PREPARE** | `assist.propose` |
| **COMMIT** | Explicit `APPROVE` → `EXECUTING` → `VERIFIED` |

Distress may increase supportiveness, never authority ([ADR-028](./028-conversational-constitution-attestation-dialogue-support.md)).

### Product principle (frozen)

> **Enigma does not optimise a person's life. It helps the user choose among locally available actions according to their own goals, constraints and current circumstances.**
>
> **Search deeply. Act shallowly. Replan constantly.** Show branches of possible futures, not a deterministic life plan.

## Consequences

- Tickets [POLARIS-SEARCH-04](../../tickets/polaris/POLARIS-SEARCH-04-receding-horizon-search.md) implement iterative deepening, pruning, chance nodes, quiescence, and next-action-only output.
- [POLARIS-SEARCH-06](../../tickets/polaris/POLARIS-SEARCH-06-shadow-mode.md) must run beside the existing Next Action planner without changing user-visible output until [POLARIS-SEARCH-07](../../tickets/polaris/POLARIS-SEARCH-07-controlled-promotion.md) has benchmark + shadow evidence.
- UI copy must not say Enigma has “already decided the next twenty steps.”
- Brain / Lens ([ADR-048](./048-structured-search-trace-and-lens.md)) shows structured lines, not theatrical thoughts.

## Alternatives considered

| Alternative | Why rejected |
| --- | --- |
| Commit the full principal variation | Treats hypotheses as a granted plan; violates receding horizon |
| Model-direct “what should I do with my life?” | Authority in the LLM; global objective; ethics creed fail |
| Replace Next Action with search in one ticket | Existing WORTH DOING surface and N01 scorer still needed; promotion is gated |
| Promise a fixed search depth to users | Depth is a budget under uncertainty, not a product SLA |

## Related

- [polaris-search.md](../architecture/polaris-search.md) · [council.md](../architecture/council.md)
- [ADR-010](./010-next-action-not-attention.md) · [ADR-019](./019-delegated-authority-and-execution-ladder.md) · [ADR-020](./020-llm-conversational-boundary-not-truth.md) · [ADR-026](./026-ethics-creed-user-is-subject.md) · [ADR-029](./029-context-compilation-request-shaped-memory.md)
- [NORTHSTAR-SEARCH-DOCS](../../tickets/northstar/NORTHSTAR-SEARCH-DOCS.md)
