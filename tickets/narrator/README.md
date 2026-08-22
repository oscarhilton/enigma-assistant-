# Narrator programme

Cross-cutting **human projection**: continuity across Goose / Harbour / Titans / Council / PolarIS / ordinary chat. Doctrine: [narrator.md](../../docs/architecture/narrator.md). Beat sketch: [narrative_beat.v0.json](../../docs/architecture/eval-stubs/narrative_beat.v0.json).

**Not** a second LLM, not C14 itself, not Lens, not Cortex, not C39, not a Council seat, not ADR-049. Mythology is presentation, never epistemology.

## Claim order (later than Observatory 01–02)

```text
Observatory 01–02  (first visible; unchanged)
        │
        ▼
C14 activity types + C09 RESPOND boundary
        │
        ▼
NARRATOR-01  human projection contract
        │
        ▼
NARRATOR-02  NarrativeBeat + streaming / suppression
        │
        ▼
NARRATOR-03  evidence-backed weaving, receipts, Alex eval
```

PolarIS / Harbour / BRAIN graphs unchanged. Conductor economics unchanged.

| Ticket | Title | Status | Hard depends |
| --- | --- | --- | --- |
| [NARRATOR-01](./NARRATOR-01-human-projection-contract.md) | Human projection contract | `future` | Observatory 01–02 |
| [NARRATOR-02](./NARRATOR-02-handoff-narrative-beats.md) | NarrativeBeat protocol | `future` | 01 + C14 |
| [NARRATOR-03](./NARRATOR-03-evidence-backed-weaving.md) | Weaving, receipts, Alex eval | `future` | 02 + RECON-08 |

## Conflicts reconciled

| Existing | This programme |
| --- | --- |
| C09 RESPOND / ADR-020 | One conversational boundary. Narrator ≠ polish LLM ≠ RESPOND-01. |
| C14 / ADR-027 | Beats **project** `EnigmaActivityEvent`; they do not invent hops or fake CoT. |
| C11 / ADR-025 | Tone enums stay parked until C09 proof. Narrator tone spec is constitutional copy, not a store. |
| C39 handoff | Agent replacement: conclusion + evidence, discard deliberation. Type is `NarrativeBeat`, not HandoffBeat. |
| Lens / Cortex | Structured search / forensic events. Narrator is ordinary-chat weaving. |
| Titans vs planets | Same embodied-state category ([council.md](../../docs/architecture/council.md)). No new named roster. |
| Goose | Warmth + incomplete picture. Narrator must not smile gaps away. |
| Harbour / PolarIS | CAN vs SHOULD. Narrator may jot both; must not collapse them. |
| Observatory | Later maps a mythic jot → event + evidence, no CoT. |
| ADR-049 | **Not created.** |
