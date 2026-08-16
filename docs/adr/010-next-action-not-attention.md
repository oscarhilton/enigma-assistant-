# ADR-010: NextAction is not AttentionItem

## Status

Accepted

## Context

Enigma’s Attention surface answers interruption: what may go wrong if ignored. Product feedback requires a second output that is **always** present and **never** fakes urgency — walks, inbox tidy-ups, open-loop clears, and rest/nothing when obligations are under control.

Folding those suggestions into `AttentionItem` would:

- inflate interrupt rate and undo Attention compression ([attention-surface.md](../architecture/attention-surface.md));
- teach the model that optional usefulness equals Priority;
- break the Shadow claim that silence is a prediction about *needs you*, not about *worth doing*.

## Decision

- Introduce a distinct canonical `NextAction` model in `packages/domain` (categories, effort, context, optional scoring fields).
- Keep `AttentionItem` for **NEEDS YOU** only; it may be empty.
- `NextAction` is **WORTH DOING**: never empty in product UX; `optional=True` by default; urgency applies only when urgency exists.
- Scorer / preference memory live outside Attention interrupt ranking (tickets N01–N03).
- Demo chrome may stub Next Action beside Attention ([D18](../../tickets/demo-ui/D18-demo-next-action.md)); Shadow may later log suggested Next Actions as observations without notifying.

## Consequences

- Three-level surface: NEEDS YOU / WORTH DOING / CAN WAIT — see [next-action.md](../architecture/next-action.md).
- “Something else” rejects train cautious preference memory, not hard category bans.
- REST / NOTHING are legitimate recommendations; objective ≠ max task throughput.
- Agents must not widen `AttentionItem` to carry walks or junk tidy-ups.
