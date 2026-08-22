# Narrator — human projection, not a second mind

**Status:** Approved architecture language — documentation only; no runtime  
**Date:** 2026-08-22  
**Tickets:** [NARRATOR-01](../../tickets/narrator/NARRATOR-01-human-projection-contract.md)–[03](../../tickets/narrator/NARRATOR-03-evidence-backed-weaving.md)  
**Reuses (do not rewrite):** [ADR-020](../adr/020-llm-conversational-boundary-not-truth.md) · [ADR-027](../adr/027-streaming-presentation-adapter.md) · [ADR-025](../adr/025-tone-memory-how-to-speak-not-who-you-are.md) · [ADR-026](../adr/026-ethics-creed-user-is-subject.md) · [ADR-028](../adr/028-conversational-constitution-attestation-dialogue-support.md) · [ADR-029](../adr/029-context-compilation-request-shaped-memory.md) · [ADR-048](../adr/048-structured-search-trace-and-lens.md) · [conversational-stream.md](./conversational-stream.md) · [council.md](./council.md) · [harbour.md](./harbour.md)

> Architecture first. Mythology is **presentation**, never epistemology.  
> **The Narrator may embellish the journey, but never the facts.**  
> No ADR-049. No second personality LLM. No star-named types.

The Narrator is a **cross-cutting human projection layer**. It weaves a continuous **micro-story** as work passes between Enigma layers. It is not a final-response-only module, not an autonomous agent, and not a Council seat.

Ordinary conversational chat remains the **surface experience**. The user must be able to react to a beat and continue normally ([C09](../../tickets/conversational-ui/C09-llm-conversational-boundary.md) / [C09b](../../tickets/conversational-ui/C09b-discourse-focus.md)).

## Product rule

Every factual clause in a narrative beat must be derivable from **structured state**, **evidence refs**, or an **explicit system event** (`EnigmaActivityEvent` / C14 hop / typed readiness / attested observable).

- Mythic methods (tarot, ritual, stargazing, tea leaves, …) are **knowingly fictional framing** around real Enigma-backed facts.
- Never invent meetings, locations, obligations, readiness, certainty, or outcomes.
- Preserve uncertainty **visibly** (Goose incomplete-picture parity).
- Never expose hidden chain-of-thought. Summarise structured, user-visible events only ([ADR-048](../adr/048-structured-search-trace-and-lens.md) · C39: pass the conclusion, preserve the evidence, discard the deliberation).
- Wit may soften friction; it must **never obscure consequence**.

[ADR-027](../adr/027-streaming-presentation-adapter.md): Enigma shouldn't tell you that it's thinking. It should quietly show you what it's actually doing. Forbidden: “Thinking carefully…”, fake latency, a parallel cognition log.

## Who speaks / who knows (do not collapse)

| Layer | Role in the weave | Must not |
| --- | --- | --- |
| **Enigma** | Underlying factual world model | Speak as a rival person |
| **Vault** | Protected retained memory | Gossip; become the transcript |
| **Goose** | Messenger / fetcher / familiar | Authority; smile a gap away |
| **Harbour** | Readiness / transition friction | SHOULD-now; invent setup facts |
| **Titans** | Embodied / ambient **state** on the position (existing **planetary** category — [council.md](./council.md)) | Vote; diagnose mood; new named roster |
| **Council** | Specialist interpreters / advisers (existing seats) | Separate memories or binding votes |
| **Polaris** | Bearing / best-next-move | Override the user; execute |
| **Narrator** | Continuity across handoffs | Own truth; second LLM; durable memory |
| **Foundry** | Capabilities + later physical/UI manifestation | Search; narrate grants it does not have |
| **Observatory / Lens / Cortex** | Engineering / search / forensic projections | Be the chat surface |

Not every actor appears every turn. Irrelevant Titans stay **silent**. No per-character memory or authority.

**Titans** are not a new constellation. They are the already-specified *planets embody state* layer (fuel, fatigue, momentum — only if attested). Do not freeze Titan star-names. Do not put them on the always-visible North Star layer.

## Tone (constitutional, not a persona store)

Quick-witted, soothing, warm, erudite, dry, gently fable-like.

Never shamey, moralising, portentous, or pompous. **Do not imitate any named person.**

Prefer **one or two short jots** over a theatrical monologue. Adaptive density: default brief; expand only when the user asks or CURIOUS/FORENSIC projection is on ([ADR-027](../adr/027-streaming-presentation-adapter.md) three projections).

This rides the **same** C09 RESPOND boundary as tone memory ([ADR-025](../adr/025-tone-memory-how-to-speak-not-who-you-are.md)). It is not C11, not a polish LLM, and not RESPOND-01 (if that ticket is later minted, it owns grounded Andon prose; Narrator composes beats).

## `NarrativeBeat` (typed projection)

Name chosen to avoid colliding with C39 **handoff** (agent replacement) and C14 `EnigmaActivityEvent` (capability hop). A beat is a **projection** of a real hop or structured result into an optional user-visible jot — a turn part, not a second log.

Schema sketch: [eval-stubs/narrative_beat.v0.json](./eval-stubs/narrative_beat.v0.json).

| Field | Means |
| --- | --- |
| `kind` | Beat family (`fetch`, `readiness`, `lens`, `titan`, `bearing`, `prose`, `suppressed`) |
| `actor` / `from_actor` / `to_actor` | Cast ids (`goose`, `harbour`, `council:<seat>`, `titan:<factor>`, `polaris`, `foundry`, `enigma`) — selective |
| `event` / `status` | Underlying hop or result (`availability.checked`, `ready`, `unknown`, `deferred`) |
| `fact_refs` / `evidence_refs` | Structured ids; empty ⇒ no factual clause allowed |
| `uncertainty` | `known` / `unknown` / `incomplete` — must survive the jot |
| `line` | Optional user-visible jot (NORMAL). Absent = suppress |
| `verbosity` / `suppress` | Density hints; FORENSIC still has the event |

Streaming interludes (duck under → return): emit beats as Core events happen (Goose fetch → Harbour readiness → relevant specialist(s) → PolarIS bearing), then ordinary chat prose. Do not invent hops. Do not delay Core for theatre.

User reply to a beat is a normal turn (C09b). The beat is not a control plane.

## Surfaces (same event, different clothes)

| Projection | What the user sees |
| --- | --- |
| **NORMAL** | One or two jots + ordinary chat |
| **CURIOUS** | Same beats as a short list |
| **FORENSIC / Observatory / Lens** | Event + evidence refs; **mythic framing stripped**; no CoT |

A tarot/stargazing jot must still map 1:1 to a hop + fact refs. Engineering view wins an argument about what happened.

## Programme order

Observatory-first sprint and PolarIS / Harbour graphs are **unchanged**. Narrator implementation is later presentation work:

```text
Observatory 01–02  →  RECON-06…08  →  OBSERVATORY-03
        │
        ▼
C14 activity types (in progress) + C09 RESPOND (same boundary)
        │
        ▼
NARRATOR-01  human projection contract
        │
        ▼
NARRATOR-02  NarrativeBeat protocol + streaming / suppression
        │
        ▼
NARRATOR-03  evidence-backed weaving, receipts, Alex eval
```

Conductor economics unchanged ([conductor-contract.md](../cloud-agents/conductor-contract.md#economics-serial-by-default)).

## Out of scope

- Runtime, a Home-page Narrator character, or `class Aldebaran`
- ADR-049; new Council seats; a named Titan roster
- Second personality / polish LLM
- Durable narrative memory (words remain working memory — [ADR-029](../adr/029-context-compilation-request-shaped-memory.md))
- Replacing C14 labels, Lens, Cortex, or C39
- Fake “thinking” interludes
