# Observatory — programme truth, not a sky theatre

**Status:** Approved engineering surface — documentation only; no runtime in this wave  
**Date:** 2026-08-22  
**Tickets:** [OBSERVATORY-01](../../tickets/observatory/OBSERVATORY-01-truth-registry.md)–[03](../../tickets/observatory/OBSERVATORY-03-runtime-probes.md)  
**Product ontology (unchanged):** [council.md](./council.md) · [polaris-search.md](./polaris-search.md) · [harbour.md](./harbour.md)

> Architecture first. Mythology second.  
> Progress is derived from explicit ticket / exit-condition / evidence state.  
> **No manually asserted percentages.**

The Observatory is an **engineering-facing** truth surface. It is not Enigma, not a Council member, not Cortex, not Lens, and not a Home-screen constellation. Celestial language (wiring graph as a “constellation”) is restrained and **must remain truthful**: missing edges stay missing.

## What it answers

| Question | Status that may claim it | Evidence |
| --- | --- | --- |
| What exists as design? | `SPECIFIED` | Ticket + acceptance + typed contract |
| What exists as code? | `IMPLEMENTED` | Paths landed; unit tests |
| What is connected? | `WIRED` | Import / route / adapter / job edge |
| What is tested? | `VERIFIED` | Exit conditions + green evidence refs |
| What is running? | `RUNNING` | Fresh probe / receipt ([OBSERVATORY-03](../../tickets/observatory/OBSERVATORY-03-runtime-probes.md)) |
| What can a user use? | `USABLE` | `RUNNING` + user path + no broken hard deps |
| What is missing, and why? | absent / broken edge | Dependency state + reason codes |

**Can I use this now?** is `USABLE == true` for that capability — never a vibe, never a dashboard percent.

Visible product phrases map onto this ladder (do **not** invent a second status enum):

| Phrase | Rungs that may claim it |
| --- | --- |
| Implemented | `IMPLEMENTED` |
| Wired | `WIRED` |
| Runtime-verified | `VERIFIED` evidenced **and** `RUNNING` (probe / receipt) |
| User-usable | `USABLE` |

## Status ladder (monotonic evidence, not a mood)

A capability may hold **one derived headline status**: the highest rung whose **required evidence is present**. Lower rungs remain inspectable.

| Rung | Meaning | Must not |
| --- | --- | --- |
| `SPECIFIED` | Contract written | Count as shipped |
| `IMPLEMENTED` | Code exists in-tree | Imply it is wired or tested |
| `WIRED` | Integration edge exists | Imply it runs in this environment |
| `VERIFIED` | Exit conditions evidenced | Imply it is running now |
| `RUNNING` | Probe/receipt within freshness | Imply a user can use it |
| `USABLE` | User-facing path works here | Be set by hand |

**Derivation rules (normative):**

1. No stored `percent_complete` / `progress` field. A UI may **count** capabilities per rung.
2. A rung is true only if its evidence refs resolve (ticket id, test path, CI run, probe id).
3. Hard-dependency failure **demotes** the headline: a child cannot be `USABLE` if a hard dep is not `USABLE` (or `VERIFIED` when the child is not yet probed).
4. Stale `RUNNING` / `USABLE` (freshness elapsed, probe fail, broken wire) **fall back** to `VERIFIED` or `WIRED` and surface `broken_wires[]`.
5. Docs-only checkboxes cannot mint `RUNNING` or `USABLE`. Those rungs require [OBSERVATORY-03](../../tickets/observatory/OBSERVATORY-03-runtime-probes.md).

Schema sketch: [eval-stubs/capability_status.v0.json](./eval-stubs/capability_status.v0.json).

## Evidence clocks

| Field | Means |
| --- | --- |
| `last_verified` | Clock of the newest successful `VERIFIED` evidence or probe receipt. Absent = never. |
| Freshness | Window defined by [OBSERVATORY-03](../../tickets/observatory/OBSERVATORY-03-runtime-probes.md). Elapsed or failed probes demote `RUNNING` / `USABLE`. |
| Ticket `Status` / markdown checkboxes | Inputs to `SPECIFIED` / sometimes `IMPLEMENTED`. **Never** sufficient for `VERIFIED`, `RUNNING`, or `USABLE`, and they do not move `last_verified`. |

## Surfaces (do not collapse)

| Surface | Question | Programme |
| --- | --- | --- |
| **Observatory** | What is the programme *true* about? | Engineering truth |
| **Cortex** | What did Enigma *do*? | [cortex-visualizer.md](./cortex-visualizer.md) |
| **Lens** | What lines did Polaris *search*? | [ADR-048](../adr/048-structured-search-trace-and-lens.md) |
| **Council** | How do specialist lenses *read* a position? | [council.md](./council.md) |
| **Harbour** | What stands between intention and starting? | [harbour.md](./harbour.md) — evidence / blockers only, **never CoT** |
| **Narrator** | How did the turn *read* as a micro-story? | [narrator.md](./narrator.md) — map jot → hop + evidence; **strip mythic frame; no CoT** |

Do **not** add Observatory or Harbour seats to the Council. Do **not** name new stars to decorate the graph. Later, a capability detail pane may attach a Harbour readiness payload (`blockers[]`, `unknowns`, evidence refs) without showing deliberation.

## Next-sprint order (visible deliverable first)

```text
Finish current tranche (RECON-05A–D on main: vault / retention / recall / worker)
        │
        ▼
OBSERVATORY-01  machine-readable truth registry
        │
        ▼
OBSERVATORY-02  engineering UI over that registry   ← first visible deliverable
        │
        ▼
RECON-06        C28 event / action spine on current main
        │
        ▼
RECON-07        Life Scripts against the restored spine
        │
        ▼
RECON-08        Alex eval catalogue (evaluator-only)
        │
        ▼
OBSERVATORY-03  runtime / wiring probes (RUNNING + USABLE evidence)
        │
        ▼
Polaris Search / Lens (BRAIN-*) — later; internal chain unchanged
        │
        ▼
HARBOUR-01…03  readiness (after PolarIS-01 + RECON-07)
        │
        ▼
NARRATOR-01…03  human projection (after C14; not this sprint)
```

Polaris / Brain View keep their existing ticket graph ([tickets/polaris/README.md](../../tickets/polaris/README.md)). Do not claim `POLARIS-SEARCH-*` implementation until Observatory 01–02 are `done` (programme gate, not a rewrite of PolarIS internals). Harbour does not join the PolarIS graph ([tickets/harbour/](../../tickets/harbour/)).

## Out of scope

- Runtime registry, UI, or probes in this docs wave
- Fake completion scores; theatrical sky UI; Home-page Observatory
- New Council members; renaming `ContextGraph` / tickets after stars
- Restoring C28 / Life Scripts / eval catalogue inside Observatory tickets
