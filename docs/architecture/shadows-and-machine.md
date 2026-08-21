# Shadows and the Machine

**Status:** North Star — documentation only. No Brain UI, Goose choreography, or Engine Room as code.  
**Date:** 2026-08-18  
**Interior:** [enigma-interior.md](./enigma-interior.md)  
**Characters:** [product-characters.md](./product-characters.md)  
**Humour:** [ADR-038](../adr/038-humour-constitution-not-user-trainable.md)  
**Execution substrate:** [C28](../../tickets/conversational-ui/C28-event-spine-agent-work.md) · [C17](../../tickets/conversational-ui/C17-execution-receipts-verification-ledger.md) · [ADR-032](../adr/032-action-ledger-execution-receipts-verification.md)

This page separates **memory, execution, presentation, and agency**. It is not lore-for-lore.

## Shadows (what THE Goose actually carries)

If THE Goose runs back with a bright red **email icon**, users think “it fetched my email.” Architecturally wrong. It fetched a reduced, governed representation.

> **THE Goose carries Shadows, not secrets.**  
> **THE Goose carries references and reduced meaning, never the Vault's contents themselves.**

**Definition:** a Shadow is a deliberately reduced representation of private information, created for a specific purpose, without carrying the original source material with it.

```
REAL THING (email / message / calendar / file)
  → local extraction / grounding / reduction
  → SHADOW  (small translucent coloured object; almost no literal content)
  → Goose carries the shadow
  → EvidenceBundle / request context
```

Never carrying actual WhatsApp. Semantic ghost of what was needed.

Visual grammar (when a later UI exists — not this slice):

- Translucent “slips” / coloured glass / soft glowing tiles — **not paper** (paper implies documents).
- Abstract marks: ◇ ▱ ●
- **Do not put text on the objects by default.** No `MAYA_LIKES_CERAMICS` on a card — that defeats the privacy theatre. Tiny colour + shape + animation. Hover/click inspects.

Two orthogonal dimensions:

| Axis | Encodes | Must not encode |
| --- | --- | --- |
| **SHAPE** | Kind of thing (▱ memory, ◇ external evidence, ● current case state) | Source-app branding |
| **COLOUR** | How it is known (epistemic / provenance class) | “email is blue” |

Suggested colour (epistemic, **not** source type):

| Colour | Class |
| --- | --- |
| Blue | retained memory |
| Amber | current case / commitment |
| Green | verified external fact |
| Purple | user-confirmed preference |
| Grey | hypothesis / uncertain |
| Red outline | conflict |
| Faded | stale / expiring |

Click a slip → MemoryInventory-style card (claim, `USER_CONFIRMED`, purpose, `raw source accessed: no`). The pixel object contains almost nothing.

Shadows can be ephemeral. Goose brings three to the workbench; Assistant uses them; two dissolve (turn-scoped); one may *point* to a retained Vault assertion but the **carried object still disappears**. Satchel emptied. C29: inventory is a projection; TTL hide ≠ fully forgotten.

Progressive loss of detail outward (design principle, not literal bars):

```
RAW SOURCE ████
local extraction ██████░░░░
grounded assertion ███░░░░
remote-safe shadow ▱
```

Satchel transformation:

| Origin | Path |
| --- | --- |
| **Sources** | slightly more detailed local evidence → Reduction Gate → translucent shadow → privacy boundary |
| **Vault** | already Shadow immediately (governed / reduced) |

Vault interior: shelves of governed objects (Maya: ▱ birthday ▱ ceramics; Work: ▱ office closure; Shared culture: ◇ THE Goose) — **not** EMAILS / WHATSAPP files. The Source Store is where raw artefacts live.

Conflicts: slips wobble / repel; Assistant: “Right. These disagree.” Stale faded; hypothesis fuzzy-edged; verified solidifies. Visual behaviour **is** epistemics ([ADR-035](../adr/035-grounded-assertions-and-evidence-pack.md)).

Canonical cartoon that must stay isomorphic to the log:

- Goose at ludicrous speed, three glowing slips in beak, one falls, skids, 👀, picks up, continues.
- Event log: `retrieved_assertions: 3; raw_sources_accessed: false; egress: none.`
- Novice sees a funny goose. Engineer sees governed semantic projections. **Same event.**

## The Machine / Engine Room (fifth entity)

Jobs that must not mush: remembering, interpreting, speaking, deciding what may be done, **actually doing it**.

| Entity | Labour | Layer |
| --- | --- | --- |
| **User** | Agency, consent, real life | North Star |
| **Assistant** | Conversational mind | North Star + Product Language |
| **Goose** | Visible worker / courier / comic emissary | Product Language |
| **Brain / Vault** | Governed memory | Fundamentals, surfaced in UI |
| **Machine** | Deterministic action substrate (tools, workflows, approvals, execution, verification) | Fundamentals |
| **World** | Inboxes, calendars, web, weather, people, reality | Final authority **outside** the system |

> **The Machine does not think. It executes governed effects.**

Without it, Goose risks seeming to be the actor. Goose is **presentation of work**, not the work engine.

Machine is a fifth *entity*, not a fifth constitutional layer. The four-part character constitution still holds. World is the external judge.

Canonical naming (use this in product copy):

**The Assistant understands. THE Goose fetches. The Brain remembers. The Vault preserves. The Machine acts.**

(Alternate, equivalent: *Enigma remembers in the Brain, stores in the Vault, acts through the Machine, speaks through the Assistant, and shows its work through THE Goose.*)

If nouns overflow: YOU / ASSISTANT / THE GOOSE / MEMORY / MACHINE / WORLD — with Vault as part of Memory.

Engine Room (visual of the Machine, not implemented here): buttons, levers, dials, conveyor of tasks, approval gate, verification lamp, “cannot proceed” buzzer, pneumatic tubes carrying shadow slips.

Canonical Goose destinations:

| Destination | Meaning |
| --- | --- |
| Brain | fetches remembered shadow |
| Vault | retrieves or shelves governed memory |
| Machine | initiates action or waits for verification |
| Boundary | remote-safe payload to egress |
| User | result, query, or apology |

## Charm vs authority

> **The Goose may represent machine state. The Goose may not originate machine authority.**  
> **The Goose can press the cartoon button. Only the Machine can press the real one.**

Goose pecks brass button / honks at lever / stamps pedal / peers into porthole = **representations** of governed state transitions. Underlying: `agenda.get`, status `running`, authority `READ`, approval not required, result success. User sees: Goose pecks calendar lever, waits, runs back with an amber shadow slip.

Consent states **owned by the Machine** (Goose may act them out):

```
REQUESTED → PREPARED → AWAITING_APPROVAL → ACTING → VERIFYING → DONE
```

Machine states: `IDLE` `READY` `ARMED` `WAITING_APPROVAL` `RUNNING` `VERIFYING` `BLOCKED` `FAILED` `DONE`

Goose reactions (Laurel-and-Hardy observability, not authority): loitering / staring foot-tapping / panicked waddling / peering into gauge / walking back in a huff / triumphant beak-up.

Maps to existing substrate: Assist lifecycle, [C28](../../tickets/conversational-ui/C28-event-spine-agent-work.md) event spine, [C17](../../tickets/conversational-ui/C17-execution-receipts-verification-ledger.md) receipts. Do not invent a second execution engine in the UI.

## Cargo is working set, not memory

Do not blur three jobs:

| Now | Labour | Owner |
| --- | --- | --- |
| **Having** | temporary, inspectable hold | Goose cargo / working set |
| **Understanding** | interpretation, challenge, next move | Assistant |
| **Remembering** | governed persistence beyond the job | Vault + Retention Gate ([C29](../../tickets/conversational-ui/C29-life-memory-and-retention.md)) |

Carrying back is funnier **and** architecturally cleaner. THE Goose must not “memorise” things itself.

> **THE Goose may hold information temporarily. It may never remember it merely by holding it.**  
> **What THE Goose carries should always be inspectable.**  
> **If it's in the beak, it's in the working set. This is not retention.**

(The last line is an engineering comment, not product copy.)

### Finite cargo = a mouthful, not a memory

Goose trots to the Machine, pecks the cartoon button, Machine coughs out Shadows. Goose grabs what the **current job** needs and physically carries them back to the Assistant.

The user should understand: these pieces are currently in play. **Not:** Enigma has absorbed more of my life forever.

Limited carry is conceptual (not a literal context-window gauge). Extra things: **plop. Dropped. Gone. Not retained.** Data minimisation as theatre.

Example: holding bank holiday, work calendar closure, weather. Assistant: “We don't need the weather.” plop. Weather Shadow fades.

### Inspect THE Goose

The comedy bird conceals a privacy / debug panel:

- Currently carrying (with epistemic status)
- Dropped (no longer needed / superseded)
- Raw sources: not carrying any
- Leaving device: nothing

> **What does THE Goose currently know? Technically, nothing. It is carrying three claims.**

### Workbench dump

*ptooey* onto the Workbench. Assistant reasons. Most temporary evidence: used → discarded.

Worth remembering? Does **not** auto-enter the Vault.

```
Shadow
  → Assistant establishes meaning
  → Retention Gate
  → no: dissolve
  → yes: Goose gets ONE new errand — “Goose, Vault.”
       waddle; object may change temporary Shadow ◉ → governed memory object ▣
       clunk; returns empty-beaked
```

Visual: **we used this** vs **we remembered this.** A Vault trip is uncommon and significant. C29 still holds: established as true ≠ justified to retain.

### GooseCargo is a presentation projection

```
GooseCargo {
  mission_id
  held_items[]
  capacity_class
  source_visits[]
  dropped_items[]
  delivered_items[]
}
```

Underneath: the real [EvidenceBundle](../adr/034-evidence-coverage-bundle.md) / work-state. After Workbench: holding nothing; delivered the items. Causal observability with a beak. Inventory remains a projection ([C29](../../tickets/conversational-ui/C29-life-memory-and-retention.md)); cargo is not a second store.

### Machine produces objects; it does not retain them

Machine input `"check calendar"` → output ◉ assertion candidate. It does not decide memory.

> **The Machine produces. THE Goose carries. The Assistant understands. The Vault remembers. The User decides.**

(Complements the character line *The Assistant understands. THE Goose fetches. The Brain remembers. The Vault preserves. The Machine acts.* Fetching is retrieval labour; carrying is the temporary hold. Acting is governed execution; producing is the object that comes out.)

Physical comedy **is** request-shaped context selection ([ADR-029](../adr/029-context-compilation-request-shaped-memory.md)): tries to grab a fifth, one falls, 👀, puts another down, picks the more relevant one.

Cortex: `candidate_assertions: 5; selected: 4; excluded assertion_271 not_required_for_request.`

> **The comedy is not concealing the architecture. The comedy is explaining the architecture.**

Do not implement Goose UI, cargo pixels, or an Engine Room from this page. Shadows, satchel, cargo, Workbench, and Engine Room stay **internal / inspectable metaphors** — not a front-page cast ([north-star.md](./north-star.md)).

## Squeeze the Goose (design review protocol)

Find the promising thing. Apply absurd pressure. Keep the gold. **Do not accidentally kill the source.**

That is how this architecture was squeezed: constitution untrainable; motifs not Mad Libs; abstinence success; satchel ephemeral; inventory is a projection; Shadows not secrets; Goose not the Machine; cargo is working set, not memory; **visibility closed — do not add nouns.**

## Freeze tests (C33)

| Id | Rule |
| --- | --- |
| `SHADOW_01` | Goose carries Shadows, not secrets; no raw-email icon as the object |
| `SHADOW_SHAPE_COLOUR_01` | Shape = kind; colour = epistemic class, not source type |
| `SHADOW_NO_TEXT_01` | Pixel object has no claim-text by default |
| `SHADOW_EPHEMERAL_01` | Carried shadow dissolves even if it pointed at a Vault assertion |
| `MACHINE_01` | Goose does not originate machine authority |
| `CARTOON_BUTTON_01` | Cartoon peck ≠ real execution |
| `SQUEEZE_PROTOCOL_01` | Review pressure keeps gold; does not kill the source |
| `CARGO_HOLD_01` | Holding is not remembering; beak ≠ Vault |
| `CARGO_INSPECT_01` | What Goose carries is inspectable; Goose currently knows nothing |
| `CARGO_PLOP_01` | Dropped cargo is gone, not retained |
| `CARGO_PROJECTION_01` | GooseCargo presents EvidenceBundle / work-state; not a memory store |
| `RETENTION_ERRAND_01` | Worth remembering does not auto-enter Vault; needs a Vault errand |
| `MACHINE_NO_MEMORY_01` | Machine produces objects; it does not retain them |
| `HAVING_01` | Having now ≠ understanding ≠ remembering later |

This slice is closed. Do not implement Engine Room, Shadow pixels, or Goose cargo UI here.
