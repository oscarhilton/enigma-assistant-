# Demo Mode — Background email corpus

**Status:** D08b–D08d landed (pipeline + background + machine noise); scale is D08e  
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
| `alex-v1/spine` | 0 | 0 | **A — control** for D08c gate |
| `alex-v1/background` | mini→canonical | 0 | **B — spine + human background** (D08c) |
| `alex-v1/demo` | mini | mini (16 CI) | interactive + false-alert headline |
| `quiet_day` / `background-no-alert` | 0 | **183** | D08d hard gate: attention empty |
| `canonical` | ~5k | ~1.5k | Phase 2.5 benchmark (D08e) |
| `stress` | 25k–100k+ | as needed | performance / cost (manual) |

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
- **Background false alerts / 1k** — incorrect attention caused by background/noise (**D08d headline**; ceiling ≤1.0; quiet-day hard-gates at 0)
- **Attention compression ratio** — signals considered : items surfaced
- **Storyline recall under noise** — critical recall with vs without background (≤1 pp degradation target)
- **Quiet-day false attention** — must be **0** when no genuine obligations exist (D08d)

## D08c scientific gate (A/B)

Integration merged (#46). **Gate hardening** (immutable comparison artefact, displacement, rich pollution traces) lives in `personal_enigma.evaluation.ab_eval` — see [D08c](../../tickets/demo-scenario/D08c-background-integration.md).

Architecture freeze preferred at **`f404597`**. New abstractions must earn existence by explaining a **measured** failure — improve the experiment, not the laboratory for its own sake.

Run **A — SPINE ONLY** (`alex-v1/spine`) vs **B — SPINE + BACKGROUND** (`alex-v1/background`) with the **same** command. Emit a **single immutable comparison artefact** via `build_ab_comparison` / `write_ab_comparison` with `baseline` / `treatment` / `delta_pp` (and siblings) plus `git_commit`, `corpus_revision`, `sanitiser_version`, `seed`. CI asserts gate pass/fail from that file (`assert_ab_gate`).

Metrics in the artefact: Critical recall · Precision · Duplicate rate · Stale alert rate · Canonical Recall@K · Retrieval Precision@K · Attention count · Remote calls · Input tokens · Estimated cost · Processing time · **Canonical attention rank / mean rank delta / critical displacement below surface threshold**.

Pollution traces: rank, source, similarity, entity/project overlap, temporal relevance, canonical/background (**evaluator-only**).

Identical recall with collapsed retrieval quality, token blow-up, or **critical displacement > 0** is still a failure.

## D08d vs D08c vs D08e

| Ticket | Asks |
| --- | --- |
| D08c | Plausible **human** conversational noise? |
| D08d | **Machine** sludge + quiet-day `attention_items == 0`? |
| D08e | **Scale curves** — understood behaviour, not premature SLOs |

## Implementation tickets

Top-level milestones stay D01–D12. Corpus work is D08 subtasks (**no D08f–z**):

| Ticket | Focus |
| --- | --- |
| [D08a](../../tickets/demo-scenario/D08a-canonical-spine.md) | Canonical Alex story spine |
| [D08b](../../tickets/demo-scenario/D08b-corpus-pipeline.md) | Corpus infrastructure |
| [D08c](../../tickets/demo-scenario/D08c-background-integration.md) | Human background + scientific gate hardening |
| [D08d](../../tickets/demo-scenario/D08d-noise-layer.md) | Machine noise + quiet-day |
| [D08e](../../tickets/demo-scenario/D08e-canonical-scale.md) | Scale ladder + curve shapes |

Related amendments: D03–D07, D09–D12 as before. F-* tickets = regression hardening around D08c–e.

## Phase 2.5 exit → Phase 3 Shadow Mode

**Release gate** (not a planning note). Stop expanding Demo Mode when:

| Gate | Target |
| --- | --- |
| Core Demo (D01–D12) + continuity + eval + explainability + adversarial | ✓ |
| ~5k plausible background + realistic noise | D08c–e |
| Critical recall | ≥ 95% |
| Recall regression (vs spine) | ≤ 1 pp |
| **Critical displacement** | **= 0** |
| Known privacy leaks | = 0 |
| Quiet-day false attention | **= 0** (exactly) |
| Background false-alert rate | ≤ 1.0 / 1k (measured; quiet-day = 0) |
| Cost / month (demo) | measured |
| 5k-scale behaviour | **understood** (≠ necessarily “fast”) |

```text
SYNTHETIC (Phase 2 / 2.5)          REAL SHADOW MODE (Phase 3)
─────────────────────────          ─────────────────────────
We know the truth.                 We do not know the truth in advance.
Can Enigma recover it?             Do Enigma's predictions line up
                                   with what the user actually does?
```

Shadow Mode is supervised-simulation → behavioural observation. It deserves its **own Phase 3 design**, not smuggling into further D08 tickets.
