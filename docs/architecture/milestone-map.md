# Milestone → ticket map

Immutable MVP baseline: git tag **`v0.1.0-mvp`** → commit `6253f96`.

## Phase 1 — MVP — COMPLETE (21 / 21)

Each milestone is a ticket under `tickets/<domain>/`. Do not reopen MVP architecture unless Phase 2 reveals an actual abstraction failure.

| # | Milestone | Status | Ticket |
| --- | --- | --- | --- |
| 00a | Private persistence | `done` | [M00a](../../tickets/platform/M00a-persistence.md) |
| 00b | Settings / calendar selection | `done` | [M00b](../../tickets/platform/M00b-settings.md) |
| 01 | Core schemas | `done` | [M01](../../tickets/domain-model/M01-core-schemas.md) |
| 02 | Synthetic fixture pipeline | `done` | [M02](../../tickets/fixtures/M02-synthetic-fixture-pipeline.md) |
| 03 | Enigma transformation | `done` | [M03](../../tickets/transformation/M03-enigma-transformation.md) |
| 04 | Privacy invariant tests | `done` | [M04](../../tickets/privacy/M04-privacy-invariant-tests.md) |
| 05 | PAYG reasoning provider | `done` | [M05](../../tickets/reasoning/M05-payg-reasoning-provider.md) |
| 06 | Attention engine | `done` | [M06](../../tickets/attention/M06-attention-engine.md) |
| 07 | macOS Apple Bridge shell | `done` | [M07](../../tickets/apple-bridge/M07-bridge-shell.md) |
| 08 | Apple Calendar | `done` | [M08](../../tickets/apple-bridge/M08-apple-calendar.md) |
| 09 | Apple Reminders | `done` | [M09](../../tickets/apple-bridge/M09-apple-reminders.md) |
| 10 | Apple Contacts / entity resolution | `done` | [M10](../../tickets/apple-bridge/M10-apple-contacts.md) |
| 11 | Gmail | `done` | [M11](../../tickets/google/M11-gmail.md) |
| 12 | Google Calendar | `done` | [M12](../../tickets/google/M12-google-calendar.md) |
| 13 | Apple Notes experimental adapter | `done` | [M13](../../tickets/apple-bridge/M13-apple-notes.md) |
| 14 | Local embedding / retrieval | `done` | [M14](../../tickets/retrieval/M14-local-embeddings.md) |
| 15 | Cross-source obligation merging | `done` | [M15](../../tickets/obligations/M15-cross-source-merging.md) |
| 16 | Commitment tracking | `done` | [M16](../../tickets/obligations/M16-commitment-tracking.md) |
| 17 | Privacy inspector | `done` | [M17](../../tickets/privacy/M17-privacy-inspector.md) |
| 18 | External sanitised API | `done` | [M18](../../tickets/api-surface/M18-external-sanitised-api.md) |
| 19 | ChatGPT integration | `done` | [M19](../../tickets/api-surface/M19-chatgpt-integration.md) |

### MVP waves (historical)

0. M01 → 1. M02 ∥ M07 ∥ M00b → 2. M03 → M04; M06; M00a → 3. M08 ∥ M09 ∥ M10 → 4. M11 ∥ M12 ∥ M13; M05 ∥ M17 → 5. M14 → M15 → M16 → 6. M18 → M19

---

## Phase 2 — Demo Mode — 0 / 12

Architecture: [demo-mode.md](./demo-mode.md). Branches: `ticket/Dxx-slug`.  
Control point for “did Enigma get better?”: compare evals to **`v0.1.0-mvp`**.

| # | Milestone | Status | Ticket |
| --- | --- | --- | --- |
| D01 | Environment separation | READY | [D01](../../tickets/demo-environment/D01-environment-separation.md) |
| D02 | Simulation clock | BLOCKED BY D01 | [D02](../../tickets/demo-environment/D02-simulation-clock.md) |
| D03 | Scenario format + validation | BLOCKED BY D01 | [D03](../../tickets/demo-scenario/D03-scenario-format.md) |
| D04 | Synthetic source adapters | BLOCKED BY D01 | [D04](../../tickets/demo-simulation/D04-synthetic-adapters.md) |
| D05 | Simulation engine | BLOCKED BY D02+D03 | [D05](../../tickets/demo-simulation/D05-event-engine.md) |
| D06 | Ground-truth model | BLOCKED BY D03 | [D06](../../tickets/demo-evaluation/D06-ground-truth.md) |
| D07 | Evaluation runner + metrics | BLOCKED BY D06 | [D07](../../tickets/demo-evaluation/D07-evaluation-runner.md) |
| D08 | Alex v1 canonical synthetic life | BLOCKED BY D01–D07 | [D08](../../tickets/demo-scenario/D08-canonical-alex.md) |
| D09 | Adversarial / privacy scenario pack | BLOCKED BY D03+D06+D07 | [D09](../../tickets/demo-scenario/D09-adversarial.md) |
| D10 | Demo UI + explainability | BLOCKED BY D01+D05+D07 | [D10](../../tickets/demo-ui/D10-demo-ui.md) |
| D11 | Provider recording + deterministic replay | BLOCKED BY D05+D07 | [D11](../../tickets/demo-evaluation/D11-replay-provider.md) |
| D12 | Curated product demo / Phase 2 exit gate | BLOCKED BY D07+D08+D10 | [D12](../../tickets/demo-scenario/D12-product-demo-scenario.md) |

### Phase 2 waves

```text
v0.1.0-mvp
    │
    ▼
D01 Environment separation          ← structural Demo/Private split
    │
    ▼
D02 Simulation clock
    │
    ├──────────────┐
    ▼              ▼
D03 Scenario    D04 Synthetic sources
format             │
    │              │
    └──────┬───────┘
           ▼
    D05 Simulation engine
           │
           ▼
    D06 Ground truth
           │
           ▼
    D07 Evaluation runner           ← laboratory complete
           │
           ▼
    D08 Build Alex                  ← first serious continuity test
           │
    ┌──────┼──────────┐
    ▼      ▼          ▼
   D09    D10        D11
adversarial  UI     replay
    │      │          │
    └──────┴────┬─────┘
                ▼
              D12 exit gate
```

**Hard rules**

- Demo never shares Private storage roots or HMAC / PERSON_* keys ([ADR-005](../adr/005-demo-private-storage-roots.md)).
- Domain time goes through injected `Clock` ([ADR-006](../adr/006-clock-injection.md)).
- Synthetic adapters stop at the **source layer**; Enigma must discover obligations (D04 must not emit `SyntheticObligation`).
- Keep `scenarios/alex-v1/` mostly empty until D08; use tiny `scenarios/feature/*` packs for D03–D07.
- D08 consumes D01–D07 — it is not “invent a life and patch the platform.”
