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
             "What actually matters?"
```

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

See [milestone-map.md](./milestone-map.md) for ticket ownership of each area.
