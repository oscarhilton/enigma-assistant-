# Observatory programme

Engineering-facing **programme truth**: what exists, what is wired, what is tested, what is running, what a user can use. Doctrine: [observatory.md](../../docs/architecture/observatory.md). Schema: [capability_status.v0.json](../../docs/architecture/eval-stubs/capability_status.v0.json).

**Not** Cortex, Lens, Council, or a Home-page sky. Architecture first; celestial graph language must stay truthful.

## Next sprint (claim order)

```text
Finish current tranche (RECON-05A–D on main)
        │
        ▼
OBSERVATORY-01  truth registry
        │
        ▼
OBSERVATORY-02  Observatory UI          ← first visible deliverable
        │
        ▼
RECON-06  C28 event / action spine
        │
        ▼
RECON-07  Life Scripts
        │
        ▼
RECON-08  Alex eval catalogue
        │
        ▼
OBSERVATORY-03  runtime / wiring probes
        │
        ▼
Polaris Search / BRAIN-* (later; internal chain unchanged)
        │
        ▼
HARBOUR-01…03  (after PolarIS-01 + RECON-07; not this sprint)
        │
        ▼
NARRATOR-01…03  (after Observatory 01–02 + C14; presentation)
```

| Ticket | Title | Status | Hard depends |
| --- | --- | --- | --- |
| [OBSERVATORY-01](./OBSERVATORY-01-truth-registry.md) | Capability truth registry | `future` | RECON-05 tranche closed on `main` |
| [OBSERVATORY-02](./OBSERVATORY-02-observatory-ui.md) | Engineering UI | `future` | 01 |
| [RECON-06](../recon/RECON-06-event-action-spine.md) | C28 event / action spine | `future` | OBSERVATORY-02 |
| [RECON-07](../recon/RECON-07-life-scripts.md) | Life Scripts on current main | `future` | RECON-06 |
| [RECON-08](../recon/RECON-08-alex-eval-catalogue.md) | Alex eval catalogue | `future` | RECON-07 |
| [OBSERVATORY-03](./OBSERVATORY-03-runtime-probes.md) | Probes for RUNNING / USABLE | `future` | 02 + RECON-08 |

Do **not** claim PolarIS implementation until 01–02 are `done`.

## Conflicts with existing docs (reconciled)

| Existing | This programme |
| --- | --- |
| Cortex (C10) | Events Enigma **did**. Observatory is programme **truth**. |
| Lens (`BRAIN-*`) | Search PV + Council assessments. Later; not this UI. |
| Council / star aliases | Unchanged. No new named seats for the graph. |
| C12 Life Scripts `landed` | Product-acceptance YAML exists. [RECON-07](../recon/RECON-07-life-scripts.md) is scripts **against the restored C28 spine**, not a second C12. |
| [ALEX-EVAL-01](../demo-evaluation/ALEX-EVAL-01-life-positions.md) | PolarIS search positions after PolarIS-01. [RECON-08](../recon/RECON-08-alex-eval-catalogue.md) is the earlier general Alex catalogue those positions may cite. |
| C28 ticket file missing on `main` | [RECON-06](../recon/RECON-06-event-action-spine.md) lands the spine on **current** `main`; do not wholesale-restore donor C28. |
| Relay `RELAY_MAX_IN_FLIGHT` default `3` | Conductor **policy** is serial / max 2; slot 3 reserved. Docs first; do not silently change relay code in this wave. |
| PolarIS-01 hard-dep NORTHSTAR-SEARCH-DOCS | Unchanged. Programme gate (do not claim yet) is Observatory 01–02. |
| Harbour readiness | Later sibling ([harbour.md](../../docs/architecture/harbour.md)). Observatory may later show blockers/unknowns, not CoT. Implemented / wired / runtime-verified / user-usable stay the six-rung ladder. |
| Narrator jots | Later projection ([narrator.md](../../docs/architecture/narrator.md)). Observatory maps jot → hop + evidence; strips mythic frame; no CoT. |
