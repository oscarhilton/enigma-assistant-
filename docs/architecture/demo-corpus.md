# Demo Mode — Background email corpus

**Status:** D08b–D08e landed (pipeline + background + noise + scale curves)  
**Plan:** Enigma Demo Mode — Background Email Corpus Integration  
**Governing rule:** Story creates meaning. Corpus creates noise. Enigma must discover the difference.  
**ADR:** [007-demo-corpus-provenance.md](../adr/007-demo-corpus-provenance.md)  
**Scale curves:** [demo-scale-curves.md](./demo-scale-curves.md)

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

**Not Level 2 full-life reprime.** FinePersonas-around-spine is Demo Mode background density. Booting Alex Lab from a Hugging Face *messy full life* (email / WhatsApp / calendar / history through normal ingest) is [P04](../../tickets/pilot/P04-alex-full-life-reprime.md) — see [data-boot.md](./data-boot.md). Do not download HF to run Level 1 Life Scripts. Do not treat a corpus dump as a prebuilt Alex brain.

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

Core architecture freeze preferred at **`f404597`** unless D08c exposes a structural failure. Favour evaluation depth over cleverness.

Run **A — SPINE ONLY** (`alex-v1/spine`) vs **B — SPINE + BACKGROUND** (`alex-v1/background`) with the **same** command. Preserve run artefacts. Report side-by-side:

Critical recall · Precision · Duplicate rate · Stale alert rate · Canonical Recall@K · Retrieval Precision@K · Attention count · Remote calls · Input tokens · Estimated cost · Processing time

Identical recall with collapsed retrieval precision or tripled tokens is still a failure to explain. Require retrieval-pollution traces for every canonical miss / changed decision. Invariants: one mailbox / identical ingestion; no Enigma-visible evaluator fields; disjoint identity namespaces; deterministic seeded reset; background stays non-meaningful.

See [D08c](../../tickets/demo-scenario/D08c-background-integration.md).

## D08d vs D08c

| Ticket | Asks |
| --- | --- |
| D08c | Can Enigma cope with lots of **plausible human conversation**? |
| D08d | Can Enigma ruthlessly ignore **machine-generated sludge**? |

## Implementation tickets

Top-level milestones stay D01–D12. Corpus work is D08 subtasks:

| Ticket | Focus |
| --- | --- |
| [D08a](../../tickets/demo-scenario/D08a-canonical-spine.md) | Canonical Alex story spine |
| [D08b](../../tickets/demo-scenario/D08b-corpus-pipeline.md) | Corpus infrastructure |
| [D08c](../../tickets/demo-scenario/D08c-background-integration.md) | Scientific gate: merge + A/B artefacts |
| [D08d](../../tickets/demo-scenario/D08d-noise-layer.md) | Machine noise + quiet-day |
| [D08e](../../tickets/demo-scenario/D08e-canonical-scale.md) | Scale ladder + curve shapes |
| [D08f](../../tickets/demo-scenario/D08f-alex-six-month.md) | Six-month ordinary life (version bump of alex-v1, not a fork) |

Related amendments: D03 (background/profile schema), D04 (multi-stream mail), D05 (timeline merge), D06 (`ScenarioSignalClass`), D07 (noise metrics), D09–D12 (developer corpora, UI suppression stats, scale replay, compression demo).

## Six-month ordinary life (D08f)

**Status:** layout + tickets (this slice) — do not author six months of content here  
**Home:** [`scenarios/alex-v1/`](../../scenarios/alex-v1/) — same package id; version bump. **Do not** create `scenarios/alex-v2/` as a second Alex.  
**Tickets:** [D08f](../../tickets/demo-scenario/D08f-alex-six-month.md) · [V2-EF-02](../../tickets/demo-scenario/V2-EF-02-ef-arc-authoring.md) amended (EF threads inside this life, not a third corpus)

January 0.2.1 is currently both the **demo week** and Alex’s **entire existence**. That overload is the problem. Six months gives change over time — memory, obligations, relationships, tone, tasks, retention, attention — without turning Demo Mode into a novel.

### Governing rule

> **Don’t write six months of biography. Write six months of ordinary events.**

Discover Alex the same way as now: only as much as the next episode requires. No `ALEX_BIOGRAPHY.md`. No dramatic breakup, medical crisis, promotion, or secret project just to make a synthetic character interesting. Mostly boring is good. [ADR-023](../adr/023-persistent-shadow-abstract-state-not-biography.md) / [north-star.md](./north-star.md): Enigma indexes what still matters; it does not compile a life.

D08 already named this as a **future version bump** of alex-v1 (not a new package). V2-EF-02’s planned `scenarios/alex-v2/` 3–6 month arcs are **revived here**, not forked: the three EF patterns (recurring admin, long-running work, social commitment) are **threads inside** Jan–Jun ordinary events. Support-contract overlay stays [V2-EF-02](../../tickets/demo-scenario/V2-EF-02-ef-arc-authoring.md) after R07 — evaluator truth, not a second mailbox.

### Layout

Episodic months, not one monster fixture:

```text
scenarios/alex-v1/timeline/
  week-01.yaml … week-03.yaml   # 0.2.1 January (immutable until 0.3.0)
  2026-01/                      # pointer README — do not duplicate week files
  2026-02/ … 2026-06/           # source events only; not loaded until 0.3.0
```

Each month folder holds **source events only** (calendar, email, notes/reminders, contacts). Chat-shaped evidence uses existing types (`email.receive` from a personal contact, or `note.upsert`) until a synthetic message source is ticketed under D04 — do **not** invent WhatsApp ingestion from Demo tickets. Synthetic Demo sources stay under `packages/simulation/.../sources/`; do not edit `packages/ingestion/.../sources/*`.

The 0.2.1 loader globs `timeline/*.yaml` only (non-recursive). Nested month YAML is scaffold — **not** part of the released January benchmark. 0.3.0 (D08f-02) recurses `timeline/YYYY-MM/**/*.yaml` and bumps `scenario.yaml`.

### Month shape (ordinary, not cinematic)

These are density targets, not a plot outline. Author only the next month’s events.

| Month | Ordinary change |
| --- | --- |
| **JAN** | Establish the world (brunch, token, Atlas, expenses, dentist, social). **Exists** as 0.2.1. |
| **FEB** | Some Jan threads resolve; a new work dependency; mundane messages; one forget; a recurring preference starts to be visible |
| **MAR** | Busier; a calendar conflict; waiting-on; something rescheduled twice; a weak intention must **not** become a task |
| **APR** | Quiet; old info decaying; a dormant project is relevant again |
| **MAY** | A new commitment intersects old relationship/context; enough history to help without replaying history |
| **JUN** | [SEC-06](../../tickets/security/SEC-06-retention-memory-decay-forget.md) / [SEC-07](../../tickets/security/SEC-07-shadow-reconstruction-benchmark.md) payoff: what Enigma still knows / has disappeared / remaining shadow is useful / can an attacker reconstruct six months? |

### Life Scripts (vertical + horizontal)

[C12](../../tickets/conversational-ui/C12-life-scripts.md) episodes dip into significant days. They do **not** live in the timeline folders — they live under `packages/evaluation/scripts/`. Timeline = source events; scripts = Alex speaking.

| Episode | Role |
| --- | --- |
| `alex_jan19_morning` | Exists — messy Monday (vertical depth) |
| `alex_feb12_running_late` | [D08f-scripts](../../tickets/demo-scenario/D08f-scripts.md) |
| `alex_mar03_waiting_on_reply` | D08f-scripts |
| `alex_apr18_quiet_day` | D08f-scripts |
| `alex_may07_old_thread_returns` | D08f-scripts |
| `alex_jun30_what_do_you_remember` | D08f-scripts — SEC-06/07 inspect |

`alex_week_03.yaml` (an entire fictional week) remains a later C12 episode, not this layout slice.

### Tone memory (corpus test, not C11 runtime)

The six months are the **fixture** for [ADR-025](../adr/025-tone-memory-how-to-speak-not-who-you-are.md) / [C11](../../tickets/conversational-ui/C11-tone-memory.md): Jan signal → Feb repeat → Mar stable → Apr used → May/Jun decay. **Do not implement the tone store from D08f.** C11 stays parked on C09 LLM proof.

### SEC-06 / SEC-07 payoff

June 30 is the reconstructability question with enough time depth:

1. Live Jan–Jun ordinary events through ingest + [SEC-06](../../tickets/security/SEC-06-retention-memory-decay-forget.md) decay.
2. Steal the June 30 shadow snapshot (keys / mappings / PRIVATE_RAW stripped).
3. Attacker reconstructs vs Enigma still useful on June 30.

Thesis: **biography decays faster than utility** ([data-retention.md](./data-retention.md#shadow-alex-vs-source-alex) · [ADR-023](../adr/023-persistent-shadow-abstract-state-not-biography.md)). D08f authors the source events. SEC-07 owns the attacker/runner — do not implement it from this track.

### What this slice is not

- Six months of authored content
- C11 tone store / learner / C09 payload
- SEC-07 attacker or reconstruction scorer
- Expanding `intent_router`
- A second Alex under `scenarios/alex-v2/` or `packages/fixtures/alex/`

## Phase 2.5 exit → Shadow Mode

Stop expanding Demo Mode when:

| Gate | Target |
| --- | --- |
| Core Demo (D01–D12) | ✓ |
| Synthetic continuity + ground-truth eval + explainability + adversarial | ✓ |
| ~5k plausible background + realistic noise | D08c–e |
| Critical recall | ≥ 95% |
| Recall regression (vs spine) | ≤ 1 pp |
| Known privacy leaks | = 0 |
| Quiet-day false attention | = 0 |
| Background false-alert rate | ≤ 1.0 / 1k (measured; quiet-day = 0) |
| Cost / month (demo profile) | known |

Then the open question is no longer “does the simulator work?” but **Shadow Mode**: does a real human life’s distribution behave like the synthetic one?

Phase 2.5 exit at tag **`v0.2.0-demo`** is **PASS**. Shadow bootstrap: [shadow-mode.md](./shadow-mode.md) · tickets S01–S06.  
Evaluation rubric for the seven post-Alex questions: [shadow-evaluation.md](./shadow-evaluation.md).