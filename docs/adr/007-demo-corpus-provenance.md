# ADR-007: Demo corpus provenance, revision pinning, and cache layout

## Status

Accepted

## Context

Demo Mode will ingest external email corpora (starting with FinePersonas) to create realistic inbox density around the authored Alex storyline. Some useful corpora (Enron, SpamAssassin, TREC) contain real or copyrighted message text. Public demos and screenshots must remain unambiguously fictional. Dataset cards also drift; silently depending on “whatever Hugging Face serves today” breaks deterministic evaluation.

## Decision

1. **Public Demo provenance gate.** Every corpus used when `public_demo` / public Demo profile is active must declare `CorpusProvenance.SYNTHETIC_CONFIRMED`. Loading `PUBLIC_REAL` or `UNKNOWN` corpora into a public Demo profile raises. Developer and stress profiles may opt into other provenances explicitly.
2. **Pin upstream revisions.** Hugging Face (and similar) manifests must include a pinned `revision` (commit hash or immutable tag). Selection + sanitiser outputs are keyed by `(corpus_id, revision, sanitiser_version, seed)`.
3. **Cache outside scenarios.** Raw downloads live under `~/.cache/enigma/datasets/<corpus_id>/<revision>/`. Derived demo-safe indexes may live under `~/.cache/enigma/datasets-derived/`. Scenario packages reference corpus ids and seeds (e.g. `background.yaml`); they do not vendor bulk third-party mail.
4. **CI never fetches bulk corpora.** PR CI uses checked-in mini fixtures only. Nightly/manual jobs may use larger cached profiles.

## Consequences

- Enron / SpamAssassin / TREC cannot leak into public Demo via a default flag.
- Benchmark identity includes corpus fingerprint (revision + sanitiser + selection seed).
- Licence redistribution review (`licence_reviewed`) remains required before shipping derived subsets with public builds; the downloader may exist before that review completes.
- Agents must not download FinePersonas (~115k) in ordinary PR CI.
