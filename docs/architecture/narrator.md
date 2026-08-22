# Narrator — human projection, not a second mind

**Status:** Approved architecture language — documentation only; no runtime  
**Date:** 2026-08-22  
**Tickets:** [NARRATOR-01](../../tickets/narrator/NARRATOR-01-human-projection-contract.md)–[03](../../tickets/narrator/NARRATOR-03-evidence-backed-weaving.md)  
**Reuses (do not rewrite):** [ADR-020](../adr/020-llm-conversational-boundary-not-truth.md) · [ADR-027](../adr/027-streaming-presentation-adapter.md) · [ADR-025](../adr/025-tone-memory-how-to-speak-not-who-you-are.md) · [ADR-026](../adr/026-ethics-creed-user-is-subject.md) · [ADR-028](../adr/028-conversational-constitution-attestation-dialogue-support.md) · [ADR-029](../adr/029-context-compilation-request-shaped-memory.md) · [ADR-048](../adr/048-structured-search-trace-and-lens.md) · [conversational-stream.md](./conversational-stream.md) · [council.md](./council.md) · [harbour.md](./harbour.md)

> Architecture first. Mythology is **presentation**, never epistemology.  
> **The Narrator may embellish the journey, but never the facts.**  
> No ADR-049. No second personality LLM. No star-named types.

The Narrator is a **cross-cutting human projection layer**. It weaves a continuous **micro-story** as work passes between Enigma layers and may render a selective end-of-day fable from structured events. It is not a final-response-only module, not an autonomous agent, and not a Council seat.

Ordinary conversational chat remains the **surface experience**. The user must be able to react to a beat and continue normally ([C09](../../tickets/conversational-ui/C09-llm-conversational-boundary.md) / [C09b](../../tickets/conversational-ui/C09b-discourse-focus.md)).

## Product rule

Every factual clause in a narrative beat or daily fable must be derivable from **structured state**, **evidence refs**, or an **explicit system event** (`EnigmaActivityEvent` / C14 hop / typed readiness / attested observable).

- Mythic methods (tarot, ritual, stargazing, tea leaves, …) are **knowingly fictional framing** around real Enigma-backed facts.
- Never invent meetings, locations, obligations, readiness, certainty, outcomes, motivation, anxiety, procrastination, laziness, feelings, or intent.
- Preserve uncertainty **visibly** (Goose incomplete-picture parity).
- Never expose hidden chain-of-thought. Summarise structured, user-visible events only ([ADR-048](../adr/048-structured-search-trace-and-lens.md) · C39: pass the conclusion, preserve the evidence, discard the deliberation).
- Wit may soften friction; it must **never obscure consequence**.
- The user is never the antagonist and should almost never be the punchline. Aim the sharper jokes at bureaucracy, system machinery, over-elaborate procedure, the cast's self-importance, or the absurdity of the situation.

[ADR-027](../adr/027-streaming-presentation-adapter.md): Enigma shouldn't tell you that it's thinking. It should quietly show you what it's actually doing. Forbidden: “Thinking carefully…”, fake latency, a parallel cognition log.

## Who speaks / who knows (do not collapse)

| Layer | Role in the weave | Must not |
| --- | --- | --- |
| **Enigma** | Underlying factual world model | Speak as a rival person |
| **Vault** | Protected retained memory and custody boundary | Gossip; become the transcript; disclose more than authorised |
| **Goose** | Messenger / fetcher / familiar | Authority; smile a gap away |
| **Harbour** | Readiness / transition friction | SHOULD-now; invent setup facts |
| **Titans** | Embodied / ambient **state** on the position (existing **planetary** category — [council.md](./council.md)) | Vote; diagnose mood; new named roster |
| **Council** | Specialist interpreters / advisers (existing seats) | Separate memories or binding votes |
| **Polaris** | Bearing / best-next-move | Override the user; execute |
| **Narrator** | Continuity across handoffs and selective account of the day | Own truth; second LLM; durable memory |
| **Foundry** | Capabilities + later physical/UI manifestation | Search; narrate grants it does not have |
| **Observatory / Lens / Cortex** | Engineering / search / forensic projections | Be the chat surface |

Not every actor appears every turn or every fable. Irrelevant Titans stay **silent**. No per-character memory or authority.

**Titans** are not a new constellation. They are the already-specified *planets embody state* layer (fuel, fatigue, momentum — only if attested). Do not freeze Titan star-names. Do not put them on the always-visible North Star layer.

## Tone (constitutional, not a persona store)

Dry, warm, quick-witted, observant, gently erudite and faintly absurd. **Cutting but cuddly**: enough edge to puncture pomposity, never enough to make the user feel inspected or mocked.

The preferred dramatic register is **slightly absurd theatre grounded in ordinary life**. A Goose may arrive with unreasonable dignity; Polaris may have been pointing the same way all afternoon; the constellation may appear satisfied. But the prose should keep returning to concrete things — the actual meeting, message, errand, decision, place, person, time, or unresolved question — so the reader never has to decode lore to understand what happened.

### Celestial, not divine

The cast is astronomical / fable-like, **not theological**.

- Do not call subsystem characters “gods”, deities, saints, angels, or higher powers.
- Prefer restrained terms such as **the stars**, **the constellation**, **the sky**, or **the heavens** when a collective celestial aside genuinely earns its place.
- These are metaphors for participating system perspectives, never authorities over the user.
- **The sky may comment. It does not rule.**
- Avoid Christian-coded halo/heaven/saint imagery in operational presentation.

Never shame, moralise, diagnose, sermonise, become portentous, or become pompous. **Do not imitate any named person.**

Prefer **one or two short jots** over a theatrical monologue during ordinary chat. Adaptive density: default brief; expand only when the user asks or CURIOUS/FORENSIC projection is on ([ADR-027](../adr/027-streaming-presentation-adapter.md) three projections).

This rides the **same** C09 RESPOND boundary as tone memory ([ADR-025](../adr/025-tone-memory-how-to-speak-not-who-you-are.md)). It is not C11, not a polish LLM, and not RESPOND-01 (if that ticket is later minted, it owns grounded Andon prose; Narrator composes beats).

## Daily fable register

The daily fable is a **selective account of the shape of the day**, not a prettier activity log.

Conceptually:

```text
structured events
    ↓
factual daily trace
    ↓
select meaningful change / branching / return / closure / open loops
    ↓
Narrator rendering
```

The trace is evidence. It must **not dictate the sentence structure**.

### Selection rules

- Usually select only **two to four meaningful beats**. Omit most events.
- Prefer changes in bearing, a branch that mattered, a return to an earlier thread, a decision becoming concrete, a useful delegated finding, a stopping / re-entry point, or something materially left open.
- Generalise where useful: tell what changed in the day rather than enumerating every state transition.
- Preserve mundane specificity where it makes the account feel lived-in: “The Castle, ten o'clock” is often better than “a social branch was parked”.
- Do not manufacture a moral, productivity score, lesson, triumph, or failure arc.
- A day is allowed simply to have happened. An unresolved day is allowed to remain unresolved.
- Do not force a tidy ending. A dry observation may be enough.

### Mythology discipline

- A mythic character may appear only when there is a structured event beneath its feet.
- Most days should need **zero, one, or two** mythic cameos, not the whole cast.
- Do not explain the mythology inside the fable. If Mole appears, what he does should make his role legible.
- Humour belongs chiefly to the machinery and situation: the Goose's disproportionate dignity, the constellation arriving late to a conclusion, a question surviving several meetings, or a procedure acquiring a life of its own.
- The Narrator may gently implicate the user in ordinary human ridiculousness, but never infer a defect of character or turn vulnerability into material.
- **Affectionate enough to feel safe. Sharp enough to be worth reading.**

### Grounding test

A good daily fable should pass all of these:

1. **Plain-English recoverability:** a user unfamiliar with Enigma mythology can still tell what actually happened.
2. **Evidence recoverability:** every factual claim can be mapped to structured events / evidence.
3. **Omission safety:** omitted events do not make the account materially misleading.
4. **No lore tax:** understanding the day does not require knowing the cast list.
5. **No synthetic cadence:** the prose does not mechanically translate one event into one sentence.
6. **No invented interiority:** feelings, motives, avoidance, anxiety, distraction, or intent appear only when evidenced.
7. **No user-as-punchline:** wit remains humane.

Useful shorthand:

> **The fable should feel written from the day, not generated from the trace.**

> **The gods are out. The stars may stay.**

> **The tale may be strange. The account must remain obvious.**

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
- Theology or divine authority as subsystem framing
