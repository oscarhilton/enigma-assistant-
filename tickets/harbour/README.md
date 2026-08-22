# Harbour programme

Activity **readiness / transition-friction**: can the user begin, and what stands in the way? Doctrine: [harbour.md](../../docs/architecture/harbour.md). Schema: [activity_readiness.v0.json](../../docs/architecture/eval-stubs/activity_readiness.v0.json).

**Not** PolarIS (should-now), not Foundry (system capabilities), not a Council seat, not Goose authority, not a Home-page harbour. No star names.

## Claim order (later than Observatory + PolarIS-01)

```text
Observatory 01–02 → RECON-06 → RECON-07 (startup graphs) → RECON-08 → OBSERVATORY-03
        │
        ▼
POLARIS-SEARCH-01 DecisionPosition     (unchanged PolarIS graph)
        │
        ▼
HARBOUR-01  activity readiness model
        │
        ▼
HARBOUR-02  minimum viable start
        │
        ▼
HARBOUR-03  friction learning (advisory)
```

| Ticket | Title | Status | Hard depends |
| --- | --- | --- | --- |
| [HARBOUR-01](./HARBOUR-01-activity-readiness-model.md) | Activity readiness model | `future` | RECON-07 + POLARIS-SEARCH-01 + Observatory 01–02 |
| [HARBOUR-02](./HARBOUR-02-minimum-viable-start.md) | Minimum viable start | `future` | 01 |
| [HARBOUR-03](./HARBOUR-03-friction-learning.md) | Friction learning / environment improvement | `future` | 02 |

No equivalent tickets existed; these are not a fork of C12, N01, Foundry, or PolarIS-02.

## Conflicts reconciled

| Existing | This programme |
| --- | --- |
| PolarIS SHOULD-now | Harbour is CAN-begin only. Ready ≠ should. |
| Foundry capabilities | Foundry = what the *system* may attempt. Harbour = user/setup friction. |
| C12 Life Scripts | Product-acceptance episodes stay. RECON-07 adds **startup graphs** as a use case — not a second C12. |
| Craft / Council | Assessments of *why it matters*. Must not own readiness state. |
| Goose | May fetch/report setup facts. No authority. |
| Observatory rungs | Implemented / wired / runtime-verified / user-usable stay the six-rung ladder. Harbour evidence/blockers are a later inspectable payload, not CoT. |
| ADR-049 | **Not created** (Council reserved the number unused). Harbour is carried by harbour.md + these tickets. |
| Next Action / Recipes | Complementary. Harbour does not replace N01 or ADR-024. |
