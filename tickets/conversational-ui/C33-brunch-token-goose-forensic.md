# C33 — Brunch / token / Goose forensic corpus + humour constitution

**Status:** in_progress  
**Branch:** `ticket/C33-brunch-token-goose-forensic`  
**Domain:** conversational-ui  
**May edit:** `packages/evaluation/fixtures/forensic/alex_brunch_token_goose_forensic.*`, `packages/evaluation/src/personal_enigma/evaluation/forensic_dump.py`, `packages/evaluation/tests/test_alex_brunch_token_goose_forensic.py`, `packages/evaluation/fixtures/forensic/README.md`, `docs/adr/038-*.md`, `docs/architecture/north-star.md`, `docs/architecture/product-characters.md`, `docs/architecture/enigma-interior.md`, `docs/architecture/shadows-and-machine.md`, `docs/architecture/overview.md`, `docs/architecture/conversational-ui.md`, `docs/architecture/ethics.md`, `docs/adr/025-*.md`, `tickets/conversational-ui/**`, `tickets/README.md`

**Must not edit:** Goose UI / choreography · Brain UI · Engine Room as code · C32 semantic recall · C29 vault/inventory modules · humour engine · `phrase_to_insert` Mad Libs · C09 production tools

**Hard depends:** dump attached (BUILD UNKNOWN)  
**Soft (~):** [C23](./C23-continuity-integrity-life-script.md) dump pattern · [C29](./C29-life-memory-and-retention.md) inventory-is-projection · [C31](./C31-goose-work-projection-and-proactivity.md) presentation later · [C11](./C11-tone-memory.md) stays parked

**ADR:** [ADR-038](../../docs/adr/038-humour-constitution-not-user-trainable.md)

## Dump caveat

The dump says **BUILD UNKNOWN — FORENSIC COMPARISON UNSAFE**. Adversarial Life Scripts / regression expectations, **not** proof current main still has these bugs. Live replay is skipped while the build is unknown.

Dump + yaml + helpers, not a full replayable C12 Life Script. Do not encode router internals.

## Goal

Preserve Demo forensic dump `alex_brunch_token_goose_forensic` and freeze humour / character / interior / Shadows / Machine / cargo architecture as docs + tests. **Do not implement Goose UI.** This slice is **closed** — no more theatre nouns.

## Dump

| File | What |
| --- | --- |
| [`alex_brunch_token_goose_forensic.dump.txt`](../../packages/evaluation/fixtures/forensic/alex_brunch_token_goose_forensic.dump.txt) | 12-turn blob (Demo Alex, clock `2026-01-20T11:00:00`) |
| [`alex_brunch_token_goose_forensic.turns.yaml`](../../packages/evaluation/fixtures/forensic/alex_brunch_token_goose_forensic.turns.yaml) | Utterance index + named cases |
| [`alex_brunch_token_goose_forensic.bootstrap.yaml`](../../packages/evaluation/fixtures/forensic/alex_brunch_token_goose_forensic.bootstrap.yaml) | Relational bootstrap sketch (not a C09 payload) |

Prepared / proposed / scheduled / attempted / verified-complete remain distinct.

Dump-executable: `BRUNCH_01` proposal ≠ booked; `BRUNCH_02` calendar ≠ reservation; `SUBJECT_01` brunch facts ↛ token subject; `AGENCY_01` enthusiasm ≠ work; `CONTINUITY_01` explain must not degrade to `"this"`; `GOOSE_01` product language missing from payload; `SQUEEZE_01` / `BEIGE_01` / `SHARED_CULTURE_01`.

## Architecture (docs only; slice closed)

| Doc | Separates |
| --- | --- |
| [ADR-038](../../docs/adr/038-humour-constitution-not-user-trainable.md) | Constitution below personalisation; motifs not Mad Libs; abstinence is success; visibility closed |
| [north-star.md](../../docs/architecture/north-star.md) | Authorship corollary + product NS; visibility layers |
| [product-characters.md](../../docs/architecture/product-characters.md) | You / Assistant / Goose / Cases on the surface |
| [enigma-interior.md](../../docs/architecture/enigma-interior.md) | Brain is a label; rooms, not one organ |
| [shadows-and-machine.md](../../docs/architecture/shadows-and-machine.md) | Shadows not secrets; Machine acts; cargo is working set |

**Having now ≠ understanding ≠ remembering later.** Beak = working set, not retention. Core state drives Goose state.

Always visible: You, Assistant, THE Goose, Cases. Inspectable: Vault, Machine, Sources. Forensic: Cortex / EvidenceBundle / lineage / egress. Do not add nouns.

**Next (not this ticket):** the relationship / relational bootstrap. Not more memory architecture.

## Deliverables

- [x] Dump + turns yaml + bootstrap sketch
- [x] Parser + freeze tests
- [x] ADR-038 + architecture addenda
- [x] Visibility squeeze; slice closed
- [ ] Live dump replay (skipped while BUILD UNKNOWN)

## Out of scope

Goose choreography / Brain UI / Engine Room as code; humour engine; treating the dump as current-main bugs; merging this PR; collapsing Assistant into Goose; front-page Shadow museum.

## Test plan

```bash
uv run pytest packages/evaluation/tests/test_alex_brunch_token_goose_forensic.py -q
uv run ruff check packages/evaluation/src/personal_enigma/evaluation/forensic_dump.py packages/evaluation/tests/test_alex_brunch_token_goose_forensic.py
uv run basedpyright packages/evaluation/src/personal_enigma/evaluation/forensic_dump.py packages/evaluation/tests/test_alex_brunch_token_goose_forensic.py
```
