# NARRATOR-01 — Human projection contract

| Field | Value |
| --- | --- |
| Status | `future` |
| Branch | `ticket/NARRATOR-01-human-projection-contract` |
| Domain | `narrator` |

## Package boundary (hard)

- May edit: [narrator.md](../../docs/architecture/narrator.md), [narrative_beat.v0.json](../../docs/architecture/eval-stubs/narrative_beat.v0.json) (additive), pointer-only amendments to conversational-stream / council / north-star, this ticket
- Must not edit: C09 orchestrator; C14 hop map as source of truth; PolarIS searcher; Assist COMMIT; Council seats; Observatory UI; `scenarios/alex-v1/timeline/**`

## Hard depends

- [OBSERVATORY-01](../observatory/OBSERVATORY-01-truth-registry.md)–[02](../observatory/OBSERVATORY-02-observatory-ui.md) `done` (programme gate — Observatory remains first visible)

## Soft depends (~)

- [C14](../conversational-ui/C14-conversation-activity-stream.md) `EnigmaActivityEvent` + turn parts (already specified)
- [ADR-020](../../docs/adr/020-llm-conversational-boundary-not-truth.md) · [ADR-027](../../docs/adr/027-streaming-presentation-adapter.md) · [ADR-025](../../docs/adr/025-tone-memory-how-to-speak-not-who-you-are.md) · [ADR-028](../../docs/adr/028-conversational-constitution-attestation-dialogue-support.md)
- C09 RESPOND graduation (still stub) — do not wait to *specify*; do not implement a second respond model
- If **RESPOND-01** is later minted: it owns grounded Andon prose; this ticket does not fork it

## Unlocks / enhances

- NARRATOR-02

## Intent

Constitutional boundaries for Narrator as a **cross-cutting projection**: tone, ordinary-chat surface, adaptive density, mythology-is-presentation. Not a final-response-only module. Not an autonomous agent.

## Non-goals

- Runtime streaming
- Beat protocol (02)
- Receipts / Alex eval (03)
- New Council seats, Titan names, ADR-049
- A Home-page Narrator character

## Acceptance criteria

- [ ] [narrator.md](../../docs/architecture/narrator.md) states: mythology ≠ epistemology; every factual clause needs state/evidence/event; uncertainty visible; no CoT
- [ ] Tone spec recorded (witty / soothing / warm / erudite / dry / gently fable-like; never shamey, moralising, portentous, pompous; do not imitate a named person; one or two jots)
- [ ] Ordinary chat remains the surface; user can reply to a jot as a normal turn
- [ ] Adaptive density: default brief; CURIOUS/FORENSIC reuse ADR-027 three projections
- [ ] Cast table: Enigma, Vault, Goose, Harbour, Titans (= planets embody), Council, PolarIS, Narrator, Foundry — selective appearance
- [ ] Explicit: no second personality LLM; C09 is the only speak boundary
- [ ] Conductor economics unchanged

## Exit conditions

Done when 02 can type beats against this contract without inventing a parallel cognition log or a new ADR number.

## Test plan

- Docs link check from narrator.md to ADR-020/027/048, C14, council, harbour
- Copy tests (later): forbidden “Thinking carefully…” and “Aldebaran felt tired”

## Privacy constraints

- No biography store; beats are ephemeral turn parts ([ADR-029](../../docs/adr/029-context-compilation-request-shaped-memory.md))
- Demo/Alex first
