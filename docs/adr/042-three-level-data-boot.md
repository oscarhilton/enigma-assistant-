# ADR-042: Three-level data boot (Life Scripts / full-life corpus / My Enigma)

## Status

Accepted

## Context

Alex Lab already boots from in-repo deterministic fixtures (P01 isolation, P02 Life Scripts, Goose/AgentWork, forensic debugging). A Hugging Face messy synthetic Alex life exists as a possible richer world. The failure modes to avoid:

1. **Treating HF download as tonight's boot path** — replacing resettable constitutional fixtures with a network corpus.
2. **Folding the corpus into UI2-06** — UI2-06 is Level 1 graduation of the five Life Scripts through `/v2`, not a noisy-life stress test.
3. **Magical prebuilt Alex brain** — loading a precomputed memory dump so Cases / attention / AgentWork never run on ingested observations.

FinePersonas (D08b–e) already supplies **background density** around an authored spine. That is not a full-life reprime: the spine still defines meaning. Level 2 is a different question — messy email / WhatsApp / calendar / history as the world itself, still through production machinery.

## Decision

1. **Three explicit boot levels.** Documented in [data-boot.md](../architecture/data-boot.md):

   | Level | Question | Home |
   | --- | --- | --- |
   | 1 Life Scripts | Does the system behave correctly? | P02 / UI2-06 |
   | 2 Full Alex corpus | Does it behave correctly when life is noisy? | [P04](../../tickets/pilot/P04-alex-full-life-reprime.md) |
   | 3 My Enigma | Does it genuinely help? | P03+ |

2. **Level 1 remains the current boot path.** In-repo fixtures stay resettable and reproducible. Hugging Face is not required to run P01, P02, UI2-06, Goose, or forensics.

3. **Level 2 is its own ticket (P04), not UI2-06.** UI2-06 stays five constitutional scripts. The HF corpus must not be claimed, downloaded, or wired as part of that graduation.

4. **Level 2 must use normal machinery.** Synthetic adapters under `packages/simulation` (not `packages/ingestion` Apple/Google files) feed the same conceptual path as production: DataSource → observations / grounding → governed retained memory → Cases / attention / AgentWork → `/v2`. Forbidden: dataset → prebuilt memory as the primary path.

5. **Level 2 is Demo storage only** ([ADR-005](./005-demo-private-storage-roots.md)). Resettable HMAC / demo root. Never Private / My Enigma.

## Consequences

- Agents must not download Hugging Face data to unstick UI2 or Life Script work.
- D08 FinePersonas remains background-around-spine; P04 is a distinct stress-test world.
- Unscripted post-reprime questions ("What am I doing this weekend?", "Did I ever reply to Elena?", "What did I actually book?", "Anything I've forgotten?") are Level 2 probes, not Level 1 script steps.

## Related

- [data-boot.md](../architecture/data-boot.md) · [ADR-005](./005-demo-private-storage-roots.md) · [ADR-040](./040-product-worlds-same-enigma.md) · [ADR-007](./007-demo-corpus-provenance.md)
- Tickets: [P02](../../tickets/pilot/P02-alex-life-scripts-as-product-tests.md) · [P04](../../tickets/pilot/P04-alex-full-life-reprime.md) · [P03](../../tickets/pilot/P03-calendar-read-support.md) · UI2-06 (Level 1 only; HF corpus out of scope)
