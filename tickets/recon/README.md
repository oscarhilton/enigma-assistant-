# Reconstruction programme (visible slice)

Dependency-minimal landings onto **current `main`**. Donor history is inspect-only. Do not wholesale-restore C28-era trees.

Visible order after Observatory 01–02:

| Ticket | Title | Status | Hard depends |
| --- | --- | --- | --- |
| [RECON-06](./RECON-06-event-action-spine.md) | C28 event / action spine | `future` | OBSERVATORY-02 |
| [RECON-07](./RECON-07-life-scripts.md) | Life Scripts on current spine | `future` | RECON-06 |
| [RECON-08](./RECON-08-alex-eval-catalogue.md) | Alex eval catalogue | `future` | RECON-07 |

Earlier RECON-04 / 05A–D (vault, retention, recall, worker) are the **current tranche** on `main` — finish those before Observatory-01. Ticket files for 05C/D may live only on `main`; this folder does not re-own them and this docs branch must not merge `main` to pull them.

[RECON-07](./RECON-07-life-scripts.md) also specifies **startup / readiness graphs** (HOW) for later Harbour — not a rigid automation engine.

C38 / C39 stay parked until this spine exists ([C38](../conversational-ui/C38-shared-uncertainty-collapse.md)). Harbour tickets live under [harbour/](../harbour/).
