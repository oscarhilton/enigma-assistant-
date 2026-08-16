# M14 — Local embedding / retrieval layer

| Field | Value |
| --- | --- |
| Status | `todo` |
| Branch | `ticket/M14-local-embeddings` |
| Domain | `retrieval` |

## Package boundary (hard)

- May edit: `packages/embeddings/**`
- May wire worker indexing jobs
- Must not call hosted embedding APIs for raw Notes corpora

## Depends on

- M13 (primary); also useful for email/reminders/calendar descriptions

## Unlocks

- Better M15 context; memory-style Notes use cases

## Non-goals

- Hosted embeddings for raw private text
- Replacing PAYG reasoning model with local giant LLM

## Acceptance criteria

- [ ] Local embedding model integration
- [ ] Chunk → embed → local vector index pipeline
- [ ] Retrieve top passages for a query; return text suitable for transformation
- [ ] Index email/notes/reminders/calendar descriptions as configured

## Test plan

- Deterministic fake embedder for CI
- Integration test: note corpus → retrieve relevant chunk for query
- Guard test: no network calls in embed path

## Privacy constraints

- Embeddings local-only for raw content; remote gets retrieved transformed passages only
