# Architecture overview

Enigma is a **private personal context** system. Applications are evidence sources; the central domain objects are obligations, commitments, events, relationships, and relevant context — not “an email” or “a reminder.”

```text
                PRIVATE PERSONAL CONTEXT

        Calendar     Reminders      Email
             \           |           /
              \          |          /
               \         |         /
                Contacts + Notes
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

Attention may be empty (legitimate silence). Next Action is a separate optional suggestion that must not fake urgency — [next-action.md](./next-action.md). Receding-horizon search (Polaris) may later rank WORTH DOING by searching local futures; the Council is an advisory projection over that search, not a second mind. Neither replaces Attention nor authorises a life-plan — [polaris-search.md](./polaris-search.md) · [council.md](./council.md).

## Governing rule for sources

Every integration performs the same transformation:

```text
provider-specific object
        ↓
canonical private object
        ↓
Enigma domain reasoning
```

Provider-specific types (e.g. `EKEvent`, Google Calendar Event) exist only at the ingestion boundary. Downstream components reason about `PrivateCalendarEvent`, `PrivateReminder`, `PrivatePerson`, `PrivateNote`, and merged `Obligation` records.

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

## Product worlds (PILOT-01)

Alex Lab and My Enigma are the **same Enigma** against different worlds — not a demo app vs a real app ([ADR-040](../adr/040-product-worlds-same-enigma.md)):

```text
                        ENIGMA
                           │
              ┌────────────┴────────────┐
              │                         │
          ALEX LAB                 MY ENIGMA
       deterministic              real governed
       synthetic world               world
```

Same shell (Today, Cases, Assistant, THE Goose). Different adapters, storage roots, clocks, and identities. Demo never shares Private HMAC / PERSON_* keys ([ADR-005](../adr/005-demo-private-storage-roots.md)).

**Data boot** is three levels — do not collapse them ([data-boot.md](./data-boot.md) · [ADR-042](../adr/042-three-level-data-boot.md)):

```text
LEVEL 1 — Life Scripts     "Does the system behave correctly?"     = P02 / UI2-06
LEVEL 2 — Full Alex corpus "Does it behave correctly when noisy?" = P04 (NOT UI2-06)
LEVEL 3 — My Enigma        "Does it genuinely help?"              = P03+
```

Current Alex Lab boot uses in-repo deterministic fixtures. It does **not** need Hugging Face. Level 2 must ingest the HF corpus through normal machinery — never a prebuilt Alex brain.

See [milestone-map.md](./milestone-map.md) for ticket ownership of each area.  
Phase 2 Demo Mode: [demo-mode.md](./demo-mode.md).  
Background email corpus: [demo-corpus.md](./demo-corpus.md).  
Attention surface + Next Action: [attention-surface.md](./attention-surface.md) · [next-action.md](./next-action.md).  
Polaris search (docs): [polaris-search.md](./polaris-search.md) · [council.md](./council.md) · [ADR-044](../adr/044-receding-horizon-action-search.md)–[048](../adr/048-structured-search-trace-and-lens.md).  
Support fitness benchmark (Phase 2.5): [executive-function-support-benchmark.md](./executive-function-support-benchmark.md).  
Phase 3 Shadow Mode: [shadow-mode.md](./shadow-mode.md) · evaluation rubric [shadow-evaluation.md](./shadow-evaluation.md) · silence evaluation [shadow-silence-evaluation.md](./shadow-silence-evaluation.md) ([ADR-009](../adr/009-silence-as-prediction.md)) · open loops [open-loop-commitments.md](./open-loop-commitments.md).
