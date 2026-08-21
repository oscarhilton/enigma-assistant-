# THE ENIGMA INTERIOR

**Status:** North Star — documentation only. No Brain UI, Goose choreography, or second memory store.  
**Date:** 2026-08-18  
**Characters:** [product-characters.md](./product-characters.md)  
**Humour:** [ADR-038](../adr/038-humour-constitution-not-user-trainable.md)  
**Memory:** [C29](../../tickets/conversational-ui/C29-life-memory-and-retention.md) · [ADR-036](../adr/036-retention-gate-life-memory.md) — inventory is a **projection** over governed memory; TTL hide ≠ fully forgotten  
**Follow-on UI:** [C30](../../tickets/conversational-ui/C30-brain-cortex-case-file.md) compiles these rooms; it does not invent a Brain store

> **The Vault remembers. THE Goose fetches. The Assistant makes sense of it. You decide what happens.**

Stop treating “Brain” as one mysterious thinking organ. That implies everything Enigma knows sits in one place — opposite of what was built.

**Brain** may remain the friendly UI entry: *“Brain — What does Enigma remember?”*  
Internally the metaphor is **THE ENIGMA INTERIOR**. The whole system is the brain. The Vault is memory. Cortex is activity.

```
                         OUTSIDE
                  remote reasoning model
                         ▲
                         │
                  PRIVACY BOUNDARY
                 only reduced context
                         │
                         ▼
     ┌──────────────── INSIDE ENIGMA ────────────────┐
     │                  WORKBENCH                     │
     │             Assistant / Cortex                 │
     │       "What are we trying to establish?"       │
     │                     │                          │
     │                    🪿 THE Goose                │
     │             /      |      \                    │
     │      VAULT      CASE      SOURCES              │
     └────────────────────────────────────────────────┘
```

| Room | What it is | What it is not |
| --- | --- | --- |
| **Vault** | Retained governed meaning | Raw `.eml` / WhatsApp archives |
| **Sources** | Private original material, local only | Working memory |
| **Cases** | Current structured life/work | A biography |
| **Workbench** | Temporary reasoning context | Durable store |
| **Cortex** | What is currently happening and why | Chain-of-thought theatre |
| **Boundary** | What is permitted to leave the device | A confirm-every-hop modal |
| **Goose** | Visible retrieval / work | Epistemic authority; interlocutor |
| **Assistant** | Interpretation at the Workbench | Retriever; vault rummager |

C29 freeze still holds: **The vault remembers. The inventory explains.** Brain/inventory is a projection. Satchel emptied = no inventory-owned state. Satchel contents are **Shadows** ([shadows-and-machine.md](./shadows-and-machine.md)), not source icons.

## Vault is not the raw-data cupboard

Must be legible. Carefully labelled **safe-deposit objects**, not rows of mail files.

Each object (matches `MemoryInventory`):

- what Enigma believes
- epistemic status
- why retained
- provenance
- expiry / review
- dependencies
- controls: [Why?] [Correct] [Forget]

No raw source by default.

**The Vault stores governed meaning, not biographical exhaust.**

Maya example:

| Field | Value |
| --- | --- |
| Belief | Birthday 14 March |
| Status | `USER_CONFIRMED` |
| Also | likes ceramics `USER_CONFIRMED` |
| Purpose | gift & birthday planning |
| Derived from | conversation evidence |
| Raw source retained here | **NO** |

## Sources is deliberately less inviting

SOURCE STORE: Mail / Calendar / Messages / Files. **LOCAL ONLY.** Raw source is not working memory. Accessed only when a specific job requires evidence.

Visual distinction that is also a privacy distinction:

| Movement | Meaning |
| --- | --- |
| Goose → **Vault** | Checking something Enigma has **deliberately retained** |
| Goose → **Sources** | Inspecting **original evidence for this job** |

Those are meaningfully different **privacy events**.

## Every Goose movement has inspectable privacy meaning

| Movement | Privacy event |
| --- | --- |
| enters Vault | governed retained-memory read |
| enters Sources | raw / local evidence access |
| enters Case File | structured current-work read |
| crosses Outside boundary | reduced context egress |
| returns | evidence / result received |
| goes to Verification | effect / result being checked |

Cartoon: *“THE Goose went into the Vault and came back with two things.”*  
Cortex: `memory.inventory.lookup subject PERSON_B purpose gift_planning; returned assertion ids; raw sources accessed false; remote disclosure none.`

**Same event. Two levels of literacy.**

## Visible satchel = EvidenceBundle / EvidencePack

Goose does not bring the Vault. It fills a **satchel** (request-shaped). Reduce, then Assistant / remote model. Turn over → satchel emptied (ephemeral).

**The Goose takes only what fits the job.** Satchel / beak = [GooseCargo](./shadows-and-machine.md#cargo-is-working-set-not-memory): inspectable working set. Holding is not remembering. Dropped pieces are gone, not retained.

Novice sees a goose carrying a tiny satchel.  
Engineer sees purpose-bound context compilation with inspectable provenance and egress control ([ADR-029](../adr/029-context-compilation-request-shaped-memory.md) · [ADR-034](../adr/034-evidence-coverage-bundle.md) · [ADR-035](../adr/035-grounded-assertions-and-evidence-pack.md)).  
**They are looking at the same thing.**

## Outside boundary: observable, not a modal every time

Threshold. Before crossing, show purpose + sending + keeping private. No confirmation spam. The user can always ask “What left?” and get an exact answer.

Embodies: **Select first. Transform second. Transmit last.**

Birthday gift example:

- Goose entered Vault: retrieved birthday, 2 confirmed preferences, previous gift; **not** accessed raw messages / email / calendar / health / finance.
- Goose went outside: sent ceramics preference, approximate budget, delivery deadline; **not** sent Maya's identity, raw conversation, relationship history, source messages.

Assistant, conversationally: *“I already had two confirmed gift preferences in the Vault, so I didn't need to open your messages. I sent the search only the preferences, budget and deadline — not who they're about.”*

Attitude: **“Of course I didn't send your entire WhatsApp history. Why on earth would I need to?”**  
Privacy as competence, not restriction.

## Safety story is positive

| Not | Yes |
| --- | --- |
| Don't worry! We promise not to misuse all the terrifying data we've collected. | Enigma was designed so most of your data never needs to go anywhere in the first place. **Visually demonstrate it.** |

User intuition to develop:

- Vault = reduced governed memory
- raw sources mostly sleep
- Goose only fetches what a mission earns
- satchel is temporary
- crossing the boundary is visible
- Assistant doesn't get magical omniscience
- nothing consequential without user authority

## Assistant stays at the Workbench

Doesn't rummage the Vault. Doesn't vanish into email.

*“I need to establish whether you're actually free Monday.”* Then sends THE Goose.

USER + ASSISTANT decide what needs knowing → GOOSE safely retrieves → VAULT / SOURCES / WORLD.

Character constitution still applies ([product-characters.md](./product-characters.md)): Goose does not write interpretation paragraphs. Vault does not banter. Assistant is not the retriever.

## C30

When [C30](../../tickets/conversational-ui/C30-brain-cortex-case-file.md) is claimed, compile **these rooms** from existing substrate (inventory, events, evidence bundle, egress). Do not start from a single Brain organ. Do not implement that UI in C33.

## Freeze tests (C33)

| Id | Rule |
| --- | --- |
| `INTERIOR_01` | Brain is UI label; interior has rooms, not one store |
| `VAULT_MEANING_01` | Vault objects are governed meaning; raw source default NO |
| `GOOSE_PRIVACY_01` | Goose→Vault ≠ Goose→Sources (distinct privacy events) |
| `SATCHEL_01` | Satchel = request-shaped bundle; emptied when the turn ends |
| `BOUNDARY_01` | Crossing Outside is visible; select / transform / transmit last |
| `WORKBENCH_01` | Assistant stays at the Workbench; sends Goose; no vault rummage |
| `SHADOW_01` | Goose carries Shadows, not secrets ([shadows-and-machine.md](./shadows-and-machine.md)) |
| `CARGO_HOLD_01` | Beak / satchel is working set, not Vault |
| `CARGO_PLOP_01` | Dropped cargo is gone, not retained |
| `VISIBLE_01` | You, Assistant, Goose, Cases on the surface; interior metaphors stay inspectable |
