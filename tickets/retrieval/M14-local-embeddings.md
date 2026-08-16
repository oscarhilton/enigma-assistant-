# M14 — Local embedding / retrieval layer

| Field | Value |
| --- | --- |
| Status | `todo` |
| Branch | `ticket/M14-local-embeddings` |
| Domain | `retrieval` |

## Package boundary (hard)

- May edit: `packages/embeddings/**`
- May edit: `apps/worker/src/personal_enigma/worker/embeddings/**` (create) for indexing jobs
- Must not edit: Apple Notes adapter (M13), hosted embedding API clients for raw private text

## Hard depends

- None beyond scaffold embeddings package

## Soft depends (~)

- M13 (Notes corpus — primary consumer)
- M02 / M11 (email and other corpora can be indexed earlier)

## Unlocks / enhances

- Soft-enhances M15 context retrieval and Notes memory use cases

## Non-goals

- Hosted embeddings for raw private text
- Replacing PAYG reasoning model with local giant LLM

## Acceptance criteria

- [ ] Local embedding model integration
- [ ] Chunk → embed → local vector index pipeline
- [ ] Retrieve top passages for a query; return text suitable for transformation
- [ ] Index email/notes/reminders/calendar descriptions as configured
- [ ] Works for non-Notes corpora even if M13 incomplete

## Test plan

- Deterministic fake embedder for CI
- Integration test: corpus → retrieve relevant chunk
- Guard test: no network calls in embed path

## Privacy constraints

- Embeddings local-only for raw content; remote gets retrieved transformed passages only
