# Data boot — three-level progression

**Status:** Policy frozen 2026-08-18  
**ADR:** [042](../adr/042-three-level-data-boot.md)  
**Tickets:** Level 1 [P02](../../tickets/pilot/P02-alex-life-scripts-as-product-tests.md) / UI2-06 · Level 2 [P04](../../tickets/pilot/P04-alex-full-life-reprime.md) · Level 3 [P03](../../tickets/pilot/P03-calendar-read-support.md)+

Alex Lab and My Enigma are the same Enigma against different worlds ([ADR-040](../adr/040-product-worlds-same-enigma.md)). How those worlds are **booted** is a separate question. Do not collapse them.

## Current boot does not need Hugging Face

Alex Lab already has in-repo deterministic fixtures for:

- P01 world isolation
- P02 five Life Scripts
- UI2-06 graduation tests (Level 1 through `/v2`)
- Goose / AgentWork
- forensic debugging

Those fixtures must stay **resettable and reproducible**. They are the constitutional boot path. Do **not** download the Hugging Face Alex corpus to boot the product tonight, and do **not** replace them with a dataset dump.

FinePersonas (D08b–e) is **background density around an authored spine**, not this Level 2 world. See [demo-corpus.md](./demo-corpus.md).

## Three levels

```text
LEVEL 1 — Life Scripts
small, deterministic, constitutional
"Does the system behave correctly?"
= current P02 / UI2-06

LEVEL 2 — Full Alex corpus (Hugging Face messy synthetic life)
messy email / WhatsApp / calendar / history
"Does it behave correctly when life is noisy?"
= P04 Alex Full-Life Reprime — NOT UI2-06

LEVEL 3 — My Enigma
Oscar's actual governed sources
"Does it genuinely help?"
= P03+ dogfood
```

| Level | Question | World | Data | Ticket |
| --- | --- | --- | --- | --- |
| **1** | Does the system behave correctly? | Alex Lab | Small in-repo Life Scripts | [P02](../../tickets/pilot/P02-alex-life-scripts-as-product-tests.md) · UI2-06 (Level 1 only; not this corpus) |
| **2** | Does it behave correctly when life is noisy? | Alex Lab (stress-test world) | Hugging Face messy synthetic life | [P04](../../tickets/pilot/P04-alex-full-life-reprime.md) |
| **3** | Does it genuinely help? | My Enigma | Oscar's governed sources | [P03](../../tickets/pilot/P03-calendar-read-support.md)+ |

Level 2 is **not** a UI2 ticket. Do not fold the HF corpus into UI2-06.

## Hard rule for Level 2

The HF corpus is a **stress-test world**. It must go through normal machinery:

```text
Alex HF raw synthetic sources
        ↓
normal source ingestion (synthetic adapters under packages/simulation)
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

That bypasses the system we want to test. A precomputed memory dump is not the primary path.

Storage is Demo only ([ADR-005](../adr/005-demo-private-storage-roots.md)). Never Private / My Enigma. HMAC and the demo root must stay resettable.

## What Level 2 is for

Unscripted questions after reprime, for example:

- "What am I doing this weekend?"
- "Did I ever reply to Elena?"
- "What did I actually book?"
- "Anything I've forgotten?"

These expose subject contamination, false memory, over-retention, bad retrieval, and duplicated work — failures Level 1 scripts are too small and too clean to catch.
