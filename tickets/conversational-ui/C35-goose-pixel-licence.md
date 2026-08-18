# C35 — Goose pixel licence (work presence, C34 expressiveness)

**Status:** done  
**Merged:** [#102](https://github.com/oscarhilton/enigma-assistant-/pull/102)  
**Domain:** conversational-ui  
**Hard depends:** [C34](./C34-relational-bootstrap.md) frozen · C14 activity projection on main  
**Soft (~):** C31 later choreography (not on this main) · C28 AgentWork when it lands on main · [#97](https://github.com/oscarhilton/enigma-assistant-/pull/97) SURFACE contract

## Scope (package boundary)

- `apps/api/src/personal_enigma/api/goose_pixels.py`
- `apps/api/tests/test_c35_goose_pixel_licence.py`
- `apps/web/src/enigma/goosePixels.ts`
- `apps/web/src/enigma/goosePixels.test.ts`
- `apps/web/src/enigma/GoosePresence.tsx`
- `apps/web/src/enigma/GoosePresence.test.tsx`
- `apps/web/src/pages/HomePage.tsx` (SURFACE rail only)
- `apps/web/src/styles.css` (sprite motion only)
- `apps/web/src/App.test.tsx` · `apps/web/src/enigma/ConversationViewport.test.tsx` · `apps/web/src/enigma/ActivityStrip.test.tsx` · `apps/web/src/enigma/cortex/CortexPanel.test.tsx` (crowbar asserts)
- `docs/adr/039-goose-pixels-project-work-not-mascot.md`
- `docs/architecture/conversational-ui.md` (licence note)
- this ticket · `tickets/conversational-ui/README.md` row

**Must not edit:** C34 `relational_bootstrap.py` · Cortex / Memory / Sources UI · Engine Room · humour engine · Shadows / cargo · C09 tools · C31 full courier

## Pixel licence (the hearing)

THE Goose may now appear on SURFACE as a **tiny, frame-sensitive projection of real work**.

This is not a mascot licence. It is not “we may now have a character.”

```
CORE WORK STATE
        ↓
does Goose have real work to portray?
        ↓
    PRESENCE / MOTION
        │
        └─────────────── C34 CURRENT FRAME
                              ↓
                         EXPRESSIVENESS
```

| Axis | Governs | Must not govern |
| --- | --- | --- |
| **Work** (C14 hops / in-flight turn / pending assist) | existence, idle / walk / return | jokes, culture, personality |
| **C34 relational bootstrap** | theatrical register (playful vs restrained) | whether work is visible |

**C34 governs the Goose’s expression, not the Goose’s existence.**

If THE Goose is projecting AgentWork, it must **not** disappear because the conversation became serious. Otherwise the relational layer would change observability of the underlying system — backwards.

- Playful: slightly more motion (a small skid on walk).
- Serious / support / no culture palette: quietly walks to the **same place**, retrieves the same thing, returns, no gag.
- Same work. Same provenance. Same inspectability.
- C34 changes theatrical register, never semantic state.

Constitutional: **The Goose may become quieter. It may never make the system less transparent.**

### SURFACE / INSPECTABLE / FORENSIC

| Layer | Cast | Goose pixels |
| --- | --- | --- |
| **SURFACE** | You, Assistant, THE Goose, Cases | v0 sprite lives **only** here |
| **INSPECTABLE** | Vault / Memory, Machine, Sources | click opens **existing** Why / activity / provenance — not a Goose store |
| **FORENSIC** | Cortex, lineage, egress, authority | never crowbar a sprite here |

Design language (Shadow, satchel, Workbench, Engine Room, cargo) stays internal. **No Shadows in v0** — cargo earns its own licence later.

### Allowed (v0)

- One tiny Goose sprite on SURFACE
- Motions: `absent` · `idle` · `walk` · `return` — perhaps nothing else
- Location / state derived entirely from existing real work
- Playful vs restrained from compiled C34 `culture_palette_available`
- Click / tap opens the **existing inspectable explanation** of that work
- Removable: no work → no Goose (does not wander to look alive)

### Forbidden

- Hide Goose on serious frame while work exists
- Fabricate activity when there is no work (playful palette ≠ permission to appear)
- Sprite sheet / character select / talking-duck interlocutor
- Speech bubbles, affection, “pet needs attention”, autonomous wandering
- Personality taxonomy, relationship score, callback ranking, new memory model
- Goose as truth, evidence, or authority
- Goose-specific truth store
- Crowbar into Memory, Cortex, Sources, egress disclosure
- Shadows / cargo pixels
- Always-on mascot chrome

Retrieval success still does not imply conversational *banter*. A Goose in the bootstrap may yield prose with zero goose. Pixels follow **work**, not bootstrap mention.

## v0 derivation (real work already on main)

C28 AgentWork lifecycle is not on this main. Do not invent a parallel work engine.

| Surface fact | Motion |
| --- | --- |
| No in-flight turn, no thread activity, no pending assist | `absent` |
| `busy` / `loading` (turn in flight) | `walk` |
| Pending `assist_proposal` (work waiting on the user) | `idle` |
| Completed C14 thread activity on the latest turn | `return` |

Inspect target = existing subject id / activity labels / Why provenance. Never a Goose dossier.

## Acceptance

- [x] Ticket is this licence
- [x] ADR-039
- [x] Tests named below
- [x] SURFACE sprite only; INSPECTABLE/FORENSIC stay goose-free
- [x] Click explains underlying work, not mascot state

## Freeze tests

| Id | Intent |
| --- | --- |
| `NO_WORK` | Goose does not fabricate activity (including playful frame) |
| `WORK_EXISTS` | Motion corresponds to real work |
| `SERIOUS_FRAME` | Work remains visible; comic expression suppressed |
| `PLAYFUL_FRAME` | Same semantic work may be presented playfully |
| `FRAME_CHANGE` | Presentation changes; AgentWork does not |
| `GOOSE_CLICK` | Explains underlying work/state; no separate mascot state treated as truth |
| `LAYER_01` | Sprite is SURFACE-only; never Memory / Cortex / activity-as-forensic |
| `AUTHORITY_01` | Pixels grant neither evidence nor authority |

## Test plan

```bash
uv run pytest apps/api/tests/test_c35_goose_pixel_licence.py -q
uv run ruff check apps/api/src/personal_enigma/api/goose_pixels.py apps/api/tests/test_c35_goose_pixel_licence.py
uv run basedpyright apps/api/src/personal_enigma/api/goose_pixels.py apps/api/tests/test_c35_goose_pixel_licence.py
pnpm --filter @personal-enigma/web test
pnpm --filter @personal-enigma/web typecheck
```

## Non-goals / deferred

Later Goose work-projection polish · Shadows / cargo · satchel · speech · humour budget bits · Cases chrome · C28 lifecycle names as runtime · always-visible cast row · Brain UI

## Privacy

Goose pixels are a local SURFACE projection. They must not enlarge the remote model’s view. Do not attach sprite state to the compiled remote working set.
