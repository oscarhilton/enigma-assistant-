# ADR-009: Silence is a logged prediction

## Status

Accepted

## Context

Shadow Mode (and eventually Private Mode) often correctly chooses **not** to notify. An empty attention surface feels like success but does not prove that Enigma avoided a miss. Demo Mode can score against authored labels; a real life cannot. Behavioural traces after suppression (a late reply, a calendar edit) are useful signals but are **not** automatic ground truth — new information may arrive after a correct morning silence.

We already separate Demo / Private / Shadow storage ([ADR-008](./008-shadow-storage-roots.md)) and define seven evaluation goals ([shadow-evaluation.md](../architecture/shadow-evaluation.md)). Those goals emphasise act-on hits and would-notify waste. They under-specify how to evaluate **suppressions** as first-class decisions.

## Decision

1. **Every silence is a prediction.** Choosing `SUPPRESS` (or equivalent non-delivery) must be logged as an evaluable decision, not merely as “nothing rendered.”
2. **Frozen decision snapshots.** Each suppression persists the candidate id, `decided_at`, available evidence refs, retrieval snapshot refs, priority, confidence, threshold, and reason codes so later review can replay **what was knowable then** without hindsight contamination. See [shadow-silence-evaluation.md](../architecture/shadow-silence-evaluation.md).
3. **Behavioural evidence ≠ ground truth.** Post-suppression traces may enqueue suppression-review candidates; they do not auto-label `FALSE_NEGATIVE`.
4. **Human channels complete the proof.** Stratified sampling audits and explicit miss reports supply adjudicated labels; headline metrics are **Suppression Accuracy** (silence precision) and **Silent Miss Rate**.
5. **Open loops stay orthogonal.** Commitment confidence/status in memory does not force attention surface; attention remains a separate axis ([open-loop-commitments.md](../architecture/open-loop-commitments.md)).

## Consequences

- S04 attention logs and SE02 would-notify audits are necessary but not sufficient; SE04+ own suppress-decision snapshots and silence metrics.
- Empty-screen demos and Shadow banners must not be treated as exit evidence for attention quality.
- Agents must not implement silence evaluation by scraping Demo ground truth or by shipping invasive OS monitoring; use first-party Enigma observations and user adjudication.
- Counterfactual A/B (surface-everything vs Enigma policy) is the long-horizon measure; it soft-depends on frozen logs and remains a later ticket.

## References

- [shadow-silence-evaluation.md](../architecture/shadow-silence-evaluation.md)
- [shadow-mode.md](../architecture/shadow-mode.md)
- [shadow-evaluation.md](../architecture/shadow-evaluation.md)
- Tickets SE04–SE11 under `tickets/shadow/`
