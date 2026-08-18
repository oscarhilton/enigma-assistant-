# ADR-039: Goose pixels project work; C34 only changes expressiveness

**Status:** Accepted  
**Date:** 2026-08-18  
**Ticket:** [C35](../../tickets/conversational-ui/C35-goose-pixel-licence.md)

> **THE Goose may become quieter. It may never make the system less transparent.**
>
> **C34 governs expression, not existence.**

## Context

[C34](../../tickets/conversational-ui/C34-relational-bootstrap.md) compiles a relational bootstrap: culture palette available or suppressed by current frame. A first reading of the pixel hearing treated palette suppression as “hide THE Goose.” That would let the relational layer change observability of underlying work — backwards.

[#97](https://github.com/oscarhilton/enigma-assistant-/pull/97) SURFACE is You / Assistant / THE Goose / Cases. INSPECTABLE stays Vault/Memory, Machine, Sources. FORENSIC stays Cortex. Those layers must not gain a mascot.

## Decision

```
CORE WORK STATE → PRESENCE / MOTION
C34 CURRENT FRAME → EXPRESSIVENESS
```

- Presence (`absent` / `idle` / `walk` / `return`) is a projection of **real work** already visible as C14 activity, in-flight turns, or pending assist.
- Expressiveness (`restrained` / `playful`) is a projection of C34 `culture_palette_available`.
- Serious frame: same place, same retrieval, no gag. Not disappearance.
- No work: no Goose — including when the culture palette is available.
- Click opens the **existing** inspectable explanation (Why / provenance / activity labels). Goose state is not truth.
- v0: one tiny SURFACE sprite. No Shadows, speech, affection, or autonomous wandering.

Pixels must not enter the remote working set. They must not grant authority or evidence.

## Consequences

- Do not hide the sprite on `ephemeral_register="serious"` when work exists.
- Later Goose work-projection (C31) may enrich motion from a fuller AgentWork spine; it inherits this fence.
- Cargo / Shadows need a separate licence.

## Related

- [C34](../../tickets/conversational-ui/C34-relational-bootstrap.md) · [ADR-027](./027-streaming-presentation-adapter.md) · [conversational-ui.md](../architecture/conversational-ui.md)
