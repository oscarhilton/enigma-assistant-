# P04 — Alex Full-Life Reprime

| Field | Value |
| --- | --- |
| Status | `todo` (unclaimed — policy frozen; **do not implement in this docs PR**) |
| Branch | `ticket/P04-alex-full-life-reprime` |
| Domain | `pilot` |
| Programme | [PILOT-01](./README.md) · [data-boot.md](../../docs/architecture/data-boot.md) |
| Level | **2** of 3 (noisy synthetic life) — **not** UI2-06 |

**Do not fold into UI2-06.** UI2-06 is Level 1 only (five constitutional Life Scripts through `/v2`). This ticket is the Hugging Face messy full-life stress-test world.

**Do not download Hugging Face data until this ticket is claimed and a slice explicitly requires a pinned fetch.** Current Alex Lab boot does not need the corpus.

## Intent

Reprime Alex Lab from a **messy synthetic full life** (email / WhatsApp / calendar / history on Hugging Face) so we can ask whether Enigma still behaves when life is noisy — not whether a small scripted world is internally consistent (that is P02 / UI2-06) and not whether Oscar's real sources help (that is P03+).

The corpus is a **stress-test world**. It must pass through normal machinery:

```text
Alex HF raw synthetic sources
        ↓
normal source ingestion  (synthetic adapters under packages/simulation)
        ↓
observations / grounding
        ↓
governed retained memory
        ↓
Cases / attention / AgentWork
        ↓
same /v2 UI
```

**Forbidden:** download Alex dataset → magical prebuilt Alex brain.

A precomputed memory dump is not the primary path. That would bypass the system we want to test.

After reprime, unscripted questions such as:

- "What am I doing this weekend?"
- "Did I ever reply to Elena?"
- "What did I actually book?"
- "Anything I've forgotten?"

…must be answerable only from what the pipeline actually retained. Failures to look for: subject contamination, false memory, over-retention, bad retrieval, duplicated work.

## Package boundary (when claimed)

- May add synthetic adapters under `packages/simulation/src/personal_enigma/simulation/sources/` — **new files**, not `packages/ingestion/.../sources/*` (Apple/Google stay M08–M13)
- May extend simulation corpus adapters / reprime CLI under `packages/simulation/**` (do not reuse D04's five pinned files as a dump-loader)
- May add Demo-only scenario/profile wiring under `scenarios/` and `packages/simulation`
- May add tests under `packages/simulation/tests/**`, `apps/api/tests/**` for the ingest → memory → attention path
- May use `/v2` as the product surface (read-model only); must **not** own `apps/web/src/v2/**` Life Script graduation (UI2-06)
- Must not edit: P02 / UI2-06 Life Script fixtures as the replacement boot path
- Must not edit: `packages/ingestion/src/personal_enigma/ingestion/sources/**`
- Must not touch My Enigma / Private roots, HMAC, or P03 calendar store

Do not cross D04's existing five adapter files unless a dedicated follow-up claims a protocol change; prefer new source modules for HF streams (mail / chat / calendar / history).

## Hard depends

- [P01](./P01-world-isolation-pilot-shell.md) `done` — Alex Lab Demo root + reset
- [P02](./P02-alex-life-scripts-as-product-tests.md) `done` — Level 1 fixtures must **remain** the constitutional boot
- [D01](../demo-environment/D01-environment-separation.md) `done` — Demo vs Private
- [D04](../demo-simulation/D04-synthetic-adapters.md) `done` — `DataSource` synthetic adapters (conceptual path)

## Soft depends (~)

- [D08b](../demo-scenario/D08b-corpus-pipeline.md) sanitiser / provenance / pinned revision (`--force-network`, never PR CI) — **FinePersonas is background-around-spine, not this corpus**
- [D16](../demo-ui/D16-demo-reset.md) Demo reset
- UI2 `/v2` shell — same UI after reprime; **UI2-06 remains Level 1 only**
- [ADR-007](../../docs/adr/007-demo-corpus-provenance.md) pin HF revision if/when fetch is claimed

## Unlocks / enhances

- Stress evidence for contamination, false memory, over-retention, retrieval, duplicated AgentWork
- Confidence that Level 1 green is not "the world was too small"

## Non-goals

- Downloading Hugging Face in PR CI or as part of UI2-06 / P02
- Replacing in-repo Life Script fixtures as the default Alex Lab boot
- Magical prebuilt memory / attention dump as the primary path
- My Enigma / Oscar's real sources (Level 3 — P03+)
- Authoring D08f six-month ordinary events (still Level-1-shaped authored spine)
- FinePersonas 115k as this world (D08c background density ≠ full-life reprime)
- Real Apple/Google ingestion files
- Merging this work into `tickets/ui2/`

## Acceptance criteria (when implemented)

- [ ] HF raw synthetic sources land as **synthetic adapters under `packages/simulation`**, implementing the same `DataSource` (or equivalent) contract conceptually as production
- [ ] Path is ingest → observations / grounding → governed retained memory → Cases / attention / AgentWork → `/v2` — no skip to a prebuilt brain
- [ ] Demo storage only ([ADR-005](../../docs/adr/005-demo-private-storage-roots.md)); never Private / My Enigma
- [ ] HMAC + demo root remain resettable; reprime is a Demo wipe + replay, not a merge into Level 1 fixtures
- [ ] No precomputed memory dump as the primary path (optional debug snapshot after a real ingest is fine; it must not be how Alex Lab boots)
- [ ] Level 1 fixtures (P01 / P02 / UI2-06 / Goose / forensics) still boot without HF and stay deterministic
- [ ] Unscripted post-reprime probes documented (weekend / Elena / booked / forgotten) with expected failure classes
- [ ] PR CI does not download the HF corpus; any fetch is pinned, opt-in, never CI ([ADR-007](../../docs/adr/007-demo-corpus-provenance.md))

## Test plan

- Reset Alex Lab → Level 1 fixtures still pass without network
- Reprime on Demo root only; My Enigma store / HMAC unchanged
- Round-trip: synthetic HF-shaped source → domain records → grounding → retained memory (no `Obligation(...)` minted in the adapter)
- After reprime, `/v2` (or API equivalent) can be asked the unscripted probes; assertions target contamination / false memory / over-retention / retrieval / duplicate work — not script YAML
- Isolation: equal Demo vs Private roots or HMAC fingerprints still raise `WorldIsolationError`

## Privacy constraints

- Synthetic / `SYNTHETIC_CONFIRMED` only for any public demo artefact
- Demo root and Demo HMAC only; never `PRIVATE_HMAC_KEY`
- Do not send wholesale HF message bodies or `PrivatePerson` to hosted models
- Pin corpus revision; do not depend on "whatever Hugging Face serves today"

## Numbering

**P04** in `tickets/pilot/` — same product-worlds programme as P02 (Level 1) and P03 (Level 3). Not D19: Demo Mode polish is frozen; D08 is authored spine + FinePersonas *background*, not this stress-test world. Not UI2-06: that ticket is Level 1 graduation only.
