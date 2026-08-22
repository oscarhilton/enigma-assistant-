# NARRATOR-02 — NarrativeBeat protocol

| Field | Value |
| --- | --- |
| Status | `future` |
| Branch | `ticket/NARRATOR-02-handoff-narrative-beats` |
| Domain | `narrator` |

## Package boundary (hard)

- May edit: `NarrativeBeat` types (prefer pinned files beside C14 `activity.ts` **or** a thin projection module introduced with an architecture pointer), [narrative_beat.v0.json](../../docs/architecture/eval-stubs/narrative_beat.v0.json) (additive), tests, docs pointers, this ticket
- Must not edit: C09 tool registry / orchestrator authority; PolarIS searcher; C14 hop *vocabulary* (extend only with real Core events); Cortex `BrainEvent`; C39 durable handoff store

## Hard depends

- [NARRATOR-01](./NARRATOR-01-human-projection-contract.md) `done`
- [C14](../conversational-ui/C14-conversation-activity-stream.md) `done` (or its landed v0 types + later stream slices as specified on that ticket)

## Soft depends (~)

- C09 token/event streaming (follow-on; v0 may project completed traces)
- [C09b](../conversational-ui/C09b-discourse-focus.md) — reply to a beat is a normal turn
- C39 constitution (discard deliberation) — do **not** name this type `HandoffBeat`

## Unlocks / enhances

- NARRATOR-03; C14 NORMAL lines may be beat `line`s

## Intent

Structured **cross-layer** beat protocol + streaming / suppression rules. Support interludes while the system ducks under and returns (fetch → readiness → specialist lenses → PolarIS) without fake CoT.

Fields in the spirit of: `kind`, `actor` / `from_actor` / `to_actor`, `event` / `status`, `fact_refs` / `evidence_refs`, `uncertainty`, optional `line`, `verbosity` / `suppress`.

## Non-goals

- Inventing hops Core did not perform
- Delaying Core for a visual story
- Weaving quality / receipts (03)
- Durable narrative memory

## Acceptance criteria

- [ ] Types conform to [narrative_beat.v0.json](../../docs/architecture/eval-stubs/narrative_beat.v0.json)
- [ ] A beat without `fact_refs` / `evidence_refs` cannot carry a factual `line`
- [ ] `suppress: true` or `verbosity: silent` for irrelevant Titans / unused seats
- [ ] Streaming: beats emit as events exist; prose remains a separate stream ([ADR-027](../../docs/adr/027-streaming-presentation-adapter.md))
- [ ] User can send a follow-up after a beat; next turn is ordinary C09 (no “narrator mode”)
- [ ] Forbidden copy tests: “Thinking carefully…”, invented meetings/locations
- [ ] Observatory/FORENSIC can read `event` + refs with `line` optional / stripped

## Exit conditions

Done when 03 can weave a music-readiness turn from a sequence of beats that each cite a real hop, and C14 still owns the hop vocabulary.

## Test plan

- Fixture hop list → beat list (no extra events)
- Negative: `line` asserting `ableton_updated` with `uncertainty: unknown` rejected
- Negative: Titan `recovery` beat when no recovery observable is attested → must be `suppress`

## Privacy constraints

- Beats hold ids and short jots, not Notes bodies or attendee emails
- Demo/Alex first
