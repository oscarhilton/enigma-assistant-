# Demo Mode — Background email corpus

**Status:** D08b pipeline complete; full Alex+corpus merge is D08c–D08e  
**Plan:** Enigma Demo Mode — Background Email Corpus Integration  
**Governing rule:** Story creates meaning. Corpus creates noise. Enigma must discover the difference.  
**ADR:** [007-demo-corpus-provenance.md](../adr/007-demo-corpus-provenance.md)

## Why

Demo Mode has two jobs: model a coherent fictional person over time, and prove Enigma can extract a tiny amount of useful attention from a much larger stream of irrelevant information. Authored scenarios excel at the first. External **synthetic** corpora supply density for the second — without telling Enigma what Alex is supposed to care about.

## Three classes of synthetic information

```text
                    ALEX'S DEMO WORLD

        1. CANONICAL STORY     — authored; known ground truth; defines Alex's life
        2. BACKGROUND LIFE     — synthetic corpus conversations; realistic, unimportant
        3. NOISE               — newsletters, notifications, marketing, spam templates
                       │
                       ▼
                  SyntheticMailSource  (one chronological mailbox)
                       │
                       ▼
                  ENIGMA CORE → ATTENTION → 1–3 useful things
```

Canonical remains authoritative. Corpus provides **density**, not meaning. Ground truth stays evaluator-only.

## FinePersonas role

Primary synthetic background correspondence: Argilla
`FinePersonas-Synthetic-Email-Conversations` (~115k conversations on Hugging Face,
licence currently `llama3.1`). Use for ordinary professional mail, acquaintances,
dead-end threads, and inbox density.

**Keep:** parsed email objects only.  
**Drop:** persona metadata, generation prompts, model reasoning/context, pipeline metadata.

Do **not** download the full dataset in PR CI. Use the checked-in
`packages/simulation/tests/fixtures/corpus/finepersonas-mini/` stub (original
synthetic mini conversations, not an HF snapshot).

## Public-demo bans

| Corpus | Public demo / screenshots | Developer / stress |
| --- | --- | --- |
| FinePersonas (synthetic-confirmed) | ✓ after sanitiser | ✓ |
| Enron (real correspondence) | ❌ | optional stress only |
| SpamAssassin / TREC | ❌ | developer noise benchmarks only |

Public Demo accepts only `CorpusProvenance.SYNTHETIC_CONFIRMED` ([ADR-007](../adr/007-demo-corpus-provenance.md)).

## Pipeline

```text
External dataset
      │
      ▼
CorpusAdapter (finepersonas / mbox / maildir)
      │
      ▼
CorpusConversation[]  (no Enigma obligation fields)
      │
      ▼
Sanitiser (identity/domain/URL rewrite, secret scan, entity filter)
      │
      ▼
Seeded selector + timeline placement
      │
      ▼
CorpusBackgroundStream | GeneratedNoiseStream | CanonicalScenarioStream
      │
      ▼
SyntheticMailSource  (merged by timestamp; no signal_class)
```

Dataset-specific behaviour stays in adapters under
`packages/simulation/.../corpus/`. `SyntheticMailSource` only sees ordinary mail shapes.

## Profiles

| Profile | Background | Noise | Purpose |
| --- | --- | --- | --- |
| `feature` | 0 | 0 | surgical tests |
| `demo` | ~1k | ~250 | interactive product demo |
| `canonical` | ~5k | ~1.5k | Phase 2 benchmark |
| `stress` | 25k–100k+ | as needed | performance / cost |

Pin Hugging Face revisions in corpus manifests. Raw downloads live under
`~/.cache/enigma/datasets/<id>/<revision>/` (override with `ENIGMA_CORPUS_CACHE`).
Derived demo-safe indexes live under
`~/.cache/enigma/datasets-derived/<id>/<revision>/sanitiser-<ver>/seed-<seed>/<profile>/`
(override with `ENIGMA_CORPUS_DERIVED`). Scenario packages reference corpus ids and
seeds; they do not vendor bulk third-party mail.

### CLI

```bash
enigma corpus list
enigma corpus verify finepersonas-mini --public-demo
enigma corpus fetch finepersonas-mini --from-path packages/simulation/tests/fixtures/corpus/finepersonas-mini
enigma corpus sanitise finepersonas-mini
enigma corpus sample finepersonas-mini --count 2 --seed test
enigma corpus build finepersonas-mini --count 100 --expand-to 100 --public-demo
# Optional local HF fetch (never in PR CI):
enigma corpus fetch finepersonas-email --force-network --revision <pinned> --max-conversations 1000
```

PR CI uses checked-in `finepersonas-mini` plus deterministic `--expand-to` so
100-conversation replay acceptance does not download ~115k rows.

## Metrics (D07 extensions)

- **Background suppression rate** — background items correctly ignored / all background
- **Background false alerts / 1k** — incorrect attention caused by background
- **Attention compression ratio** — signals considered : items surfaced
- **Storyline recall under noise** — critical recall with vs without background (≤1 pp degradation target)

## Implementation tickets

Top-level milestones stay D01–D12. Corpus work is D08 subtasks:

| Ticket | Focus |
| --- | --- |
| [D08a](../../tickets/demo-scenario/D08a-canonical-spine.md) | Canonical Alex story spine |
| [D08b](../../tickets/demo-scenario/D08b-corpus-pipeline.md) | Corpus infrastructure |
| [D08c](../../tickets/demo-scenario/D08c-background-integration.md) | Merge canonical + background |
| [D08d](../../tickets/demo-scenario/D08d-noise-layer.md) | Generated noise layer |
| [D08e](../../tickets/demo-scenario/D08e-canonical-scale.md) | Canonical / stress scale |

Related amendments: D03 (background/profile schema), D04 (multi-stream mail), D05 (timeline merge), D06 (`ScenarioSignalClass`), D07 (noise metrics), D09–D12 (developer corpora, UI suppression stats, scale replay, compression demo).
