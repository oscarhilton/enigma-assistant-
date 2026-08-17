# Architecture overview

Enigma is a **private personal context** system. Applications are evidence sources; the central domain objects are obligations, commitments, events, relationships, and relevant context — not “an email” or “a reminder.”

**Philosophy:** [north-star.md](./north-star.md) — Enigma turns private, messy human life into a small, actionable state machine — without trying to permanently own the life that produced it.

```text
                PRIVATE PERSONAL CONTEXT

        Calendar     Reminders      Email      Chat
             \           |           /          /
              \          |          /          /
               \         |         /          /
                Contacts + Notes + messages
                       │
                       ▼
                ENIGMA MEMORY
                       │
                       ▼
               obligation model
                       │
                       ▼
                attention engine
                       │
                       ▼
             "What needs you?" + optional Next Action
```

Attention may be empty (legitimate silence). Next Action is a separate optional suggestion that must not fake urgency — [next-action.md](./next-action.md).

## Governing rule for sources

Every integration performs the same transformation:

```text
provider-specific object
        ↓
canonical private object
        ↓
Enigma domain reasoning
```

Provider-specific types (e.g. `EKEvent`, Google Calendar Event) exist only at the ingestion boundary. Downstream components reason about `PrivateCalendarEvent`, `PrivateReminder`, `PrivatePerson`, `PrivateNote`, `PrivateChatMessage`, and merged `Obligation` records.

## Local vs remote

| Local | Remote |
| --- | --- |
| Ingest Apple / Google sources | Reason over carefully transformed context |
| Entity resolution / Contacts | PAYG reasoning provider |
| Privacy / leakage analysis | Never receive raw `PrivatePerson` or wholesale Notes |
| Local embeddings + retrieval | |

Apple Bridge is trusted local software. It does not call an LLM and does not expose an internet-facing API.

## Monorepo map

| Path | Role |
| --- | --- |
| `apps/api` | Enigma Core (FastAPI) |
| `apps/worker` | Ingestion / attention jobs |
| `apps/web` | Settings / privacy UI |
| `apps/apple-bridge` | Swift macOS companion |
| `packages/domain` | Canonical models |
| `packages/ingestion` | `DataSource` protocol + per-source adapters |
| `packages/identity` | Local entity resolution / PERSON_* |
| `packages/dedupe` | Cross-provider calendar dedupe |
| `packages/privacy` | Privacy levels / invariants |
| `packages/transformation` | Enigma transformer |
| `packages/attention` | Attention engine |
| `packages/embeddings` | Local vector search |
| `packages/fixtures` | Synthetic private-world data |
| `packages/simulation` | Demo / Shadow environment, clock, synthetic sources |
| `packages/evaluation` | Demo / Shadow evaluation runner / metrics |
| `scenarios/` | Immutable Demo scenario packages (e.g. `alex-v1`) |

**North Star:** [north-star.md](./north-star.md) (private OS for intent · seven squeezes).  
See [milestone-map.md](./milestone-map.md) for ticket ownership of each area.  
Phase 2 Demo Mode: [demo-mode.md](./demo-mode.md).  
Background email corpus + six-month ordinary Alex: [demo-corpus.md](./demo-corpus.md) ([D08f](../../tickets/demo-scenario/D08f-alex-six-month.md)).  
Attention surface + Next Action: [attention-surface.md](./attention-surface.md) · [next-action.md](./next-action.md).  
Support fitness benchmark (Phase 2.5): [executive-function-support-benchmark.md](./executive-function-support-benchmark.md).  
Phase 3 Shadow Mode: [shadow-mode.md](./shadow-mode.md) · evaluation rubric [shadow-evaluation.md](./shadow-evaluation.md) · silence evaluation [shadow-silence-evaluation.md](./shadow-silence-evaluation.md) ([ADR-009](../adr/009-silence-as-prediction.md)) · open loops [open-loop-commitments.md](./open-loop-commitments.md).  
Inter-Enigma coordination (programme): [enigma-coordination-protocol.md](./enigma-coordination-protocol.md) ([ADR-013](../adr/013-inter-enigma-coordination-trust-boundary.md)–[019](../adr/019-delegated-authority-and-execution-ladder.md)).  
**Shareable recipes (North Star, not now):** [shareable-recipes.md](./shareable-recipes.md) ([ADR-024](../adr/024-shareable-recipes-procedure-never-personal-state.md) · [REC00](../../tickets/recipes/REC00-shareable-recipes-north-star.md)). Declarative procedure — never personal state, never executable code, never a prompt bundle. Sequence: C09 LLM proof → SEC-05 PASS → recipe engine. Do not hardcode EF patterns into product.  
**Tone memory (North Star, not now):** [tone-memory.md](./tone-memory.md) ([ADR-025](../adr/025-tone-memory-how-to-speak-not-who-you-are.md) · [C11](../../tickets/conversational-ui/C11-tone-memory.md)). Style preferences, not a personality dossier, not conversation logs. Sequence: C09 LLM proof → unpark C11. Do not send last-N messages as style memory.  
**Personal-data pilot (after C09):** [personal-data-security.md](./personal-data-security.md) · [data-retention.md](./data-retention.md) ([ADR-021](../adr/021-personal-data-security-boundary.md) · [SEC-00](../../tickets/security/SEC-00-personal-data-threat-model.md)–[SEC-07](../../tickets/security/SEC-07-shadow-reconstruction-benchmark.md) → [SEC-05](../../tickets/security/SEC-05-personal-data-pilot-gate.md)). Sequence: C09 → SEC programme PASS → Oscar's inbox. Real Gmail requires `gmail.readonly` only, encrypted local storage (SEC-01), retention / forget boundary (SEC-06 — co-equal half), shadow benchmark (SEC-07), audited egress gate, adversarial Alex tests, and SEC-05 hard checklist (Q1–Q16, three gate dimensions) — not M11 scaffold alone.  
**Ethics creed (binding, docs only):** [ethics.md](./ethics.md) ([ADR-026](../adr/026-ethics-creed-user-is-subject.md)). Know only what is necessary · Infer only for a purpose · Remember less than you could · Make memory and action inspectable. The user is the subject of Enigma, never its raw material. Ethics creed before real inbox. Alex is a fictional crash-test dummy — not a biography.  
**Conversation activity (C14):** [conversational-stream.md](./conversational-stream.md) ([ADR-027](../adr/027-streaming-presentation-adapter.md) · [ADR-029](../adr/029-context-compilation-request-shaped-memory.md)). Show what Enigma is doing — not fake thinking. The request chooses the context; compiled turns carry an auditable manifest. assistant-ui on Vite as adapter; FastAPI remains the agent.  
**Grounded evidence foundation:** [enigma-master-gap-analysis.md](./enigma-master-gap-analysis.md) · [ADR-035](../adr/035-grounded-assertions-and-evidence-pack.md). Proposition-shaped assertions, epistemic status, unknowns, and challenges are the substrate for later continuity, Brain/Cortex, and proactivity.  
**Conversation continuity and action integrity (C16–C23, before more assists):** attested completion must leave next-action; external-action claims need receipts; “did you do it?” inspects the ledger ([ADR-032](../adr/032-action-ledger-execution-receipts-verification.md) · [conversational-ui.md](./conversational-ui.md#conversation-continuity-and-action-integrity-c16c23)). Capsule stays frozen ([ADR-030](../adr/030-conversation-capsule.md)). Bounded workers after P0 ([ADR-033](../adr/033-bounded-subtask-workers.md) · [C24](../../tickets/conversational-ui/C24-read-only-evidence-worker.md)) — one speaking agent, not extra personalities.

> **Enigma deliberately forgets narrative detail while preserving enough state to remain useful.**
