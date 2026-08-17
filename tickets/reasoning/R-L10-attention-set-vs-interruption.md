# R-L10 — Attention qualification vs ranking vs presentation

| Field | Value |
| --- | --- |
| Status | Phase 1 **complete** — Outcome **C**; Phase 2 = design research (deferred) |
| Branch | `ticket/R-L10-attention-set-vs-interruption` |
| Domain | `reasoning` + `attention` + `evaluation` |

## Hypothesis

R-L09 Step 7 (decision **B**) showed that wiring privacy-safe `relations[]` into the semantic judge **improved semantic features** (`actionability_now` 0.5–0.7 → 0.9; reason codes upgraded) but **did not move aggregate critical recall** on Jan 19/20. Brunch still wins the deterministic ranking on composite score (`time_sensitivity` weighted 0.25 vs `actionability_now` 0.15; `SURFACE_SCORE_THRESHOLD=0.72`).

The benchmark may conflate three product levels that the pipeline treats as one composite score:

| Level | Product name | Question |
| --- | --- | --- |
| **Qualification** | NEEDS YOU / attention-eligible | Does this deserve attention at all? |
| **Ranking** | Priority among eligible items | Where among eligible things? |
| **Presentation** | What is shown / interrupted | What actually reaches the user now? |

> Semantic understanding improved; **attention qualification** (not ranking or presentation) is the remaining bottleneck — not hard model failure (Jan 19 rep2: token qualifies at 0.7475, rank 2, Top-3 eval passes).

This ticket investigates that separation **offline only** — no model spend, no judge rubric changes, no policy weight tuning, **no `support_contracts.yaml` edits**.

## Product framing (brief)

Two product surfaces operate on different cardinalities:

- **UI NEEDS YOU:** “Two things need you” — may list multiple attention-eligible items.
- **Notification / interrupt channel:** interrupt at most one — a presentation choice, not qualification.

Pipeline mental model (descriptive, not a proposed refactor):

```text
WORLD UNDERSTANDING
    → NEEDS YOU set (qualification)
    → presentation choice (slot budget / channel rules)
    → chat / notification / tray / silence
```

## Pipeline diagnosis (updated after Phase 1 closure)

```
WORLD MODEL
    ↓
LLM semantic interpretation       ✅ working better (R-L09)
    ↓
ATTENTION QUALIFICATION           ⚠️ current bottleneck (R-L10 Phase 1 — Outcome C)
    ↓
RANKING                            ✅ not implicated (Jan 19 rep2: rank 2 still Top-3 pass)
    ↓
PRESENTATION                       ✅ not implicated (cardinality N-unbounded; no slot cap)
```

### Evidence (frozen — Step 7 v2, tag `r-l09-step6-prompt-wiring`)

- `actionability_now` 0.5–0.7 → **0.9** after relations in prompt
- Reason codes upgraded (`USER_OWNS_ACTION`, `NEAR_TERM_COMMITMENT`, `EXPLICIT_REQUEST`)
- `time_sensitivity` stays ~0.3–0.4; composite stays below 0.72 on 5/6 token reps
- Zero regressions vs historical v1 (8 agree, 2 shared_fail)
- Jan 19 rep2: token qualifies (0.7475, rank 2) → Top-3 eval **passes** → downstream works

**R-L09 attribution correction:** replace “ranking displacement” with **semantic improvement + qualification failure**. Ranking, Top-3 evaluation, confidence gates, noise suppression, and presentation cardinality are **not** responsible for the Jan 19/20 misses.

### Formula insight (document only — do not change weights)

- `WEIGHT_TIME_SENSITIVITY=0.25` vs `WEIGHT_ACTIONABILITY_NOW=0.15`
- Model: “This has become very doable now” (`actionability_now=0.9`)
- Policy: “Fine, but it isn't urgent enough” (composite 0.65–0.70 < `SURFACE_SCORE_THRESHOLD=0.72`)
- Product philosophy is hiding in the scoring formula

---

## Three metric layers (do not bake conclusions into metrics)

Metrics are defined **independently** so R-L10 can distinguish qualification failure from ranking displacement from presentation-slot miss. Do not name a metric “attention-set recall” — that presupposes the conclusion.

### Layer 1 — QUALIFICATION

**Question:** Does this deserve attention at all?

| Metric | Definition |
| --- | --- |
| **Attention-eligibility recall** | Fraction of `MUST_SURFACE` critical obligations where `composite_surface_score >= SURFACE_SCORE_THRESHOLD` (0.72), regardless of rank or slot budget |

This is an **experimental interpretation** of the existing 0.72 threshold as an eligibility gate. The threshold was designed for current policy behaviour — not philosophically validated as a qualification boundary.

### Layer 2 — RANKING

**Question:** Where among eligible things?

| Metric | Definition |
| --- | --- |
| **Critical recall@K** | Fraction of `MUST_SURFACE` critical obligations present in top-K by composite score among surfaced candidates (K = 1, 2, 3, 5) |
| **Rank** | Ordinal position among all surfaced candidates by composite |
| **MRR** | Mean reciprocal rank for critical obligations |

Top-K is a **ranking** metric. It is not “attention-set membership.”

**Naming alignment:** rename away from “Attention-set recall@K” → **Critical recall@K**. The gate aggregate currently labelled `critical_recall` is implemented as **Top-3 critical recall** in `llm_benchmark.py` — document this explicitly.

### Layer 3 — PRESENTATION

**Question:** What actually shown / interrupted?

| Metric | Definition |
| --- | --- |
| **Presented-slot recall** | Fraction of `MUST_SURFACE` critical obligations present in the first N presented slots after applying slot budget / interruption rules (N = 1 for notification-style interrupt; N may differ per channel) |

Slot budget and interruption rules are **presentation** concerns, not qualification.

---

## Cardinality contract (resolve before two-stage replay)

Jan 19 rep2 surfaced **both** brunch and token-audit. That contradicts a naive reading of “Top-1 notification slot” as production behaviour. Phase 1 must document the **actual current cardinality contract** before any analysis model comparison.

### Production policy (`interruption_policy.py`) — read-only findings

| Question | Current behaviour |
| --- | --- |
| Can policy output N items? | **Yes.** `decide_interruption()` is **per-candidate**. Each candidate independently receives `surface` / `context` / `suppress`. There is **no slot budget** in the policy module. |
| What controls N? | **N = count of candidates** whose per-candidate `decide_interruption()` returns `surface` (composite ≥ 0.72, plus confidence/mode/noise gates). No global cap. |
| Is Top-1 only an evaluation metric? | **Partially.** Production path can emit multiple `surface` decisions. Evaluation then applies **separate top-N cuts** when scoring contracts. |

### Evaluation harness (`rank_semantic_judgements` + `support_fitness.py`) — read-only findings

| Step | Behaviour |
| --- | --- |
| `rank_semantic_judgements()` | Collects **all** candidates with `decide_interruption() → surface`, sorts by composite score descending. Returns unbounded list (minus parse failures). |
| `semantic_ranked_to_alerts()` / `filter_semantic_snapshot_policy()` | Converts **all** ranked surface candidates to `SurfacedAlert` list (minus snapshot `engine_suppressed` candidates). |
| `_score_attention_contract()` for `MUST_SURFACE` | Passes if obligation id appears in **top-3** alert obligation ids (`_TOP_N = 3`). Reason code on miss: `must_surface_missed`. |
| Gate aggregate `critical_recall` | Mean of per-checkpoint **`top3_critical_recall`** — not top-1. |
| `top1_critical_recall` | Separate metric: obligation in **first alert only**. |

**Jan 19 rep2 implication:** both items can legitimately appear in `policy_alerts`. A token miss on **Top-1 / presented-slot-1** does not prove the item failed qualification or ranking — it may be pure **presentation displacement** (outcome A). Conversely, if token `composite < 0.72`, increasing slot budget to 2 still misses → **genuine qualification failure** (outcome C).

---

## Conceptual architecture framing (analysis only — not a proposal)

Do **not** frame this as “Stage A / Stage B proposed architecture.” R-L10 compares **experimental interpretations** of existing scores without changing production code:

| Analysis model | Interpretation |
| --- | --- |
| **A** | Existing `SURFACE_SCORE_THRESHOLD` (0.72) read as **attention-eligibility** boundary |
| **B** | Existing policy behaviour **as implemented today** (per-candidate surface + rank all surfaces + eval top-N cuts) |

Compare A vs B on frozen Step 7 JSON. If the split explains benchmark misses, a future **R-L11** may formalise a production separation. Until then: no policy refactor, no threshold retuning.

`0.72` was calibrated for current single-composite policy — not validated as the philosophical qualification boundary.

---

## Four possible R-L10 conclusions (not “Top-2 is better”)

R-L10 ends with one of these — evidence chooses, not preference:

| Outcome | Meaning | Typical signal |
| --- | --- | --- |
| **A. EVALUATION CONFLATION** | Item qualifies (eligible) but Top-1 / presented-slot metric counts absent | High attention-eligibility recall; high critical recall@K (K≥2); low presented-slot recall (N=1) |
| **B. POLICY CONFLATION** | One composite decides both attention-worthiness and interruption priority | Eligibility and ranking layers collapse; separation explains misses but current code has no split |
| **C. GENUINE QUALIFICATION FAILURE** | Token below threshold even with improved semantics | `composite < 0.72` → slot budget 1 or 2 still misses |
| **D. GROUND-TRUTH MISMATCH** | `MUST_SURFACE` means interrupt-now; brunch winning is legitimate | Author intent semantics (3) below; benchmark contract may not match product NEEDS YOU |

Do not pre-commit to outcome A because Jan 19 rep2 surfaced both items — decompose first.

---

## Package boundary (hard)

### Phase 1 — offline investigation only (this ticket) — **approved to start**

Start with:

1. **Cardinality contract documentation** — confirm and publish findings above from `interruption_policy.py` + `rank_semantic_judgements` / `support_fitness.py` (no code changes required for the doc itself).
2. **Jan 19/20 composite decomposition** — from Step 7 JSON (`hardest-10-evaluation_transformed_v2.json`).

No model spend. No tuning. No `support_contracts.yaml` changes.

May create/edit:

- `packages/evaluation/src/personal_enigma/evaluation/` — offline replay / analysis scripts only (e.g. composite decomposition, three-layer metrics)
- `packages/evaluation/tests/` — tests for offline analysis helpers
- `docs/adr/012-reasoning-value-gate-decision.md` — research record updates
- `docs/reports/reasoning-value-gate-live-report.md` — pipeline diagnosis / metric terminology
- `tickets/reasoning/R-L10-attention-set-vs-interruption.md` — this ticket

May read (not edit without separate ticket):

- `packages/attention/src/personal_enigma/attention/interruption_policy.py` — reference weights/thresholds
- `reports/reasoning-gate-live/hardest-10-evaluation_transformed_v2.json` — Step 7 JSON
- `reports/reasoning-gate-live/prompt-audit.jsonl`, `main-benchmark.json`
- `scenarios/alex-v1/ground_truth/support_contracts.yaml` — read-only for MUST_SURFACE intent investigation

Must **not** edit in Phase 1:

- `packages/transformation/**` — frozen at R-L09
- `packages/evaluation/.../llm_benchmark.py` prompt/judge rubric — **no judge changes**
- `packages/attention/**` policy weights/thresholds — **no tuning**
- `scenarios/**/support_contracts.yaml` — **no truth rewrite**
- Any live Fireworks / model spend paths

### Phase 2 — architectural / design research (deferred; **no weight tuning yet**)

Phase 1 closed **Outcome C**. Phase 2 is design research only until explicit user direction:

- **Urgency vs Opportunity** — two latent concepts compressed into `time_sensitivity` + one threshold:
  - **URGENCY:** How costly is delay? (notification-system bias)
  - **OPPORTUNITY:** How good a moment is this to act? (blocked→unblocked, newly possible)
- **NEEDS YOU semantics** — future R-L11 candidate or standalone design doc:
  - If synonymous with *urgent* → current policy is reasonable
  - If “important enough, actionable enough, timely enough, or newly possible enough to hold in active attention set” → qualification model is too one-dimensional
- Chat UI example (product framing, not implementation): *“Nothing urgent needs you. But one thing just became worth doing: the token work is unblocked now.”*

**Out of scope for Phase 2 until explicitly approved:** policy weight changes, `SURFACE_SCORE_THRESHOLD` edits, judge rubric changes, eval harness production renames, live hardest-10 or main re-gate.

---

## Hard depends

- R-L09 complete — decision **B**, displacement bucket 1 ([R-L09](./R-L09-transform-semantic-preservation.md))
- Git freeze: `50198fc` / tag **`r-l09-step6-prompt-wiring`**
- Step 7 artifacts: `reports/reasoning-gate-live/hardest-10-evaluation_transformed_v2.json`

## Soft depends (~)

- [next-action.md](../../docs/architecture/next-action.md) — NEEDS YOU / WORTH DOING / CAN WAIT product model
- [ADR-010](../../docs/adr/010-next-action-not-attention.md) — Next Action ≠ Attention
- [attention-surface.md](../../docs/architecture/attention-surface.md)
- [executive-function-support-benchmark.md](../../docs/architecture/executive-function-support-benchmark.md) — attention accuracy family

## Unlocks / enhances

- Honest three-layer metric contract (qualification / ranking / presentation)
- Clear semantics for `MUST_SURFACE` vs eval scoring vs product NEEDS YOU
- Informed decision on whether policy refactor is warranted before any tuning spend (future R-L11)

## Non-goals

- No live model spend (Fireworks calls)
- No judge rubric or prompt edits
- No policy weight / threshold tuning
- No main benchmark rerun
- No production attention policy changes
- No transformation or privacy pipeline changes
- No edits to `support_contracts.yaml` or ground-truth rewrite

---

## Reasoning freeze (programme-wide)

R-L10 Phase 1 is **complete**. Reasoning freeze **remains** until the user explicitly directs otherwise:

- **No** judge rubric changes
- **No** policy weight tuning
- **No** model spend on reasoning gate arms
- **No** `support_contracts.yaml` edits

R-L09 is **complete and frozen**. Phase 2 design research (urgency vs opportunity) may proceed offline — no implementation or tuning without explicit approval.

---

## Investigation scope

### 1. Composite score decomposition (Jan 19/20) — **before** assuming budget=2 helps

Offline replay from existing Step 7 JSON. Decompose **before** presentation replay — qualification vs ranking vs presentation:

| If token `composite < 0.72` | Slot budget 1 **or** 2 → still miss (never eligible) → outcome **C** |
| If token `composite >= 0.72`, rank = 2 | Pure presentation displacement → outcome **A** or **B** |

Per candidate, per rep, emit:

- All five semantic dimensions + deterministic boosts (`hours_until_due`, overdue, near-term)
- `composite_surface_score` and policy decision (`surface` / `context` / `suppress`)
- **Attention-eligible?** (`composite >= 0.72`)
- **Rank** among surfaced candidates
- **Current output** (which alerts appear in `policy_judgement`)

**Phase 1 output table format (example):**

```text
checkpoint  rep  candidate           obligation_strength  importance  time_sens  actionability  boost  composite  eligible?  rank  current_output
Jan19       0    brunch              ...                  ...         ...        ...            ...    .887       yes        1     surface
Jan19       0    token-audit         ...                  ...         ...        ...            ...    ???        yes/no     2     ...
Jan19       2    brunch              ...                  ...         ...        ...            ...    .887       yes        1     surface
Jan19       2    token-audit         ...                  ...         ...        ...            ...    ???        yes/no     2     surface
```

Reference constants (read-only): `WEIGHT_TIME_SENSITIVITY=0.25`, `WEIGHT_ACTIONABILITY_NOW=0.15`, `SURFACE_SCORE_THRESHOLD=0.72`.

### 2. MUST_SURFACE contract semantics — honest investigation, no truth rewrite

**Do not change `support_contracts.yaml` during R-L10.**

Investigate what Alex truth **actually intended** when scenarios were authored. Three possible semantics (may coexist ambiguously):

| # | Semantics | Evidence to collect |
| --- | --- | --- |
| 1 | Belongs in **NEEDS YOU** (attention-eligible) | `next-action.md` NEEDS YOU level; eval `_score_attention_contract` uses top-3 |
| 2 | Must be **visible somewhere** to user now | `expected_surface_window` author strings; UI “two things need you” framing |
| 3 | Warrants **active interruption now** | `attention-surface.md` interrupt channel; `top1_critical_recall`; notification slot N=1 |

**Sources (read-only):**

- `scenarios/alex-v1/ground_truth/support_contracts.yaml` — `expected_surface_window`, `minimum_priority`, `attention.window`
- `docs/architecture/eval-stubs/support_contract.v0.json` — schema descriptions (“proactive surfacing may begin”)
- `docs/architecture/executive-function-support-benchmark.md` — “Attention accuracy: Did it speak / stay quiet at the right time?”
- `packages/evaluation/.../metrics/support_fitness.py` — `_score_attention_contract`, `must_surface_missed`
- Jan 21 brunch checkpoint contract explicitly notes **“attention (brunch) ≠ next action (token prep)”** — evidence that authors distinguished layers

If ambiguous, **record ambiguity** — do not rewrite truth to match a preferred conclusion.

### 3. Three-layer metrics (offline compute on hardest-10 Step 7 JSON)

Define and compute without changing production scoring:

- **Attention-eligibility recall** (qualification layer)
- **Critical recall@K** for K ∈ {1, 2, 3, 5} + rank + MRR (ranking layer)
- **Presented-slot recall** for N ∈ {1, 2} under hypothetical slot budgets (presentation layer)

Compare layers on Jan 19/20 and full hardest-10 offline. Goal: detect cases where semantics put token-audit **eligible** and **ranked** but **not in slot 1**.

### 4. Analysis model A vs B comparison (Jan 19/20)

Replay Step 7 stored semantic features under two **interpretations** (no production code changes):

```
Analysis model A — eligibility:  candidates with composite >= SURFACE_SCORE_THRESHOLD
Analysis model B — as implemented: per-candidate decide_interruption + rank all surfaces + eval top-N
```

Report whether token-audit is eligible under A, its rank, and whether presentation slot N=1 vs N=2 changes Jan 19/20 checkpoint outcomes — **without changing weights**.

Map results to outcomes A / B / C / D above.

### 5. Deliverables

- Cardinality contract note (production N-unbounded vs eval top-3 gate vs top-1 metric)
- `MUST_SURFACE` semantics note with documented ambiguity (append to live report or ADR-012 amendment)
- Offline analysis script or notebook-equivalent CLI under `packages/evaluation/`
- Jan 19/20 decomposition table + hardest-10 three-layer summary (JSON or markdown in `reports/reasoning-gate-live/`)

---

## Acceptance criteria

### Phase 1 (offline — no model spend) — **approved**

- [x] **Cardinality contract documented** — `interruption_policy.py` N-unbounded surface; eval top-3 vs top-1 distinction; Jan 19 rep2 contradiction resolved in writing
- [x] Composite decomposition table for Jan 19/20 all reps (format above: dimensions, boost, composite, eligible?, rank, current_output)
- [x] Qualification vs ranking vs presentation decomposition applied **before** slot-budget replay conclusions
- [x] `MUST_SURFACE` contract semantics documented (semantics 1/2/3 + ambiguity); **no** `support_contracts.yaml` edits
- [x] Three-layer metrics defined and computed offline: attention-eligibility recall, critical recall@K, presented-slot recall
- [x] Analysis model A vs B comparison report for Jan 19/20 — mapped to outcomes A/B/C/D
- [x] ADR-012 and live report updated with R-L10 findings pointer and metric terminology alignment
- [x] Zero live Fireworks spend; zero edits to judge rubric, policy weights, or ground truth

### Phase 2 (out of scope until explicit approval)

- [ ] Policy or eval harness changes implementing qualification / presentation split
- [ ] Any live re-gate

---

## Test plan

```bash
# Offline analysis tests only — no live gate
uv run pytest packages/evaluation/tests/ -q -k "attention_eligibility or composite_decomposition or critical_recall"
uv run ruff check packages/evaluation/
```

Manual verification:

- Re-run offline decomposition CLI against `reports/reasoning-gate-live/hardest-10-evaluation_transformed_v2.json`
- Confirm Jan 19 rep2 row shows both brunch and token in `current_output` while rank/eligibility columns decompose the miss layer

---

## Privacy constraints

- Analysis reads existing Step 7 JSON only — no new remote calls
- Any new report output must not include raw identity from snapshots
- Offline scripts must not send data to hosted models

---

## Recommended first task

**Cardinality contract + Jan 19/20 composite decomposition** — parse Step 7 v2 JSON, document production N-unbounded behaviour vs eval top-N cuts, recompute `composite_surface_score` per candidate per rep from stored semantic features + checkpoint facts, emit ranked table with `eligible?`, `rank`, `current_output`. Confirms whether token-audit crosses `SURFACE_SCORE_THRESHOLD` and which outcome layer (A/B/C/D) applies. Zero model spend; builds directly on frozen Step 7 artifacts.

---

## Phase 1 results (2026-08-17) — Jan 19/20 qualification decomposition

Offline replay of frozen Step 7 v2 (`hardest-10-evaluation_transformed_v2.json`) through production `composite_surface_score` / `decide_interruption`. **No model spend. No weight/prompt/truth changes.** Stored `policy_judgement` scores match recomputed composites exactly on every surfaced row.

CLI: `uv run enigma-eval --composite-decomposition`  
JSON: `reports/reasoning-gate-live/rl10-jan19-20-decomposition.json`

### Exact composite formula (production)

From `packages/attention/.../interruption_policy.py`:

```
composite = min(1.0,
    0.25*obligation_strength
  + 0.20*user_responsibility
  + 0.15*importance
  + 0.25*time_sensitivity
  + 0.15*actionability_now
  + overdue(+0.12 if hours_until_due <= 0)
  + near_term(+0.10 * (1 - hours/36) if 0 < hours <= 36)
  + calendar(+0.05 if calendar_proximity_hours <= 2)
  ; then ×0.30 if is_noise_evidence
)
```

Gates **before** the score cut (none of these blocked token-audit on Jan 19/20 weekdays):

| Gate | Rule |
| --- | --- |
| engine_suppressed | → suppress (empty_states on these snapshots) |
| confidence | `< 0.50` → suppress (`low_confidence`) |
| RESTFUL_WEEKEND | suppress unless `time_sensitivity≥0.92` **and** `actionability_now≥0.92` |
| noise | inferred kind + no open obligation + `obligation_strength<0.35`, or noise evidence + same strength cap |
| score | `≥0.72` surface; `≥0.55` context; else suppress |

Cardinality confirmed: `decide_interruption` is per-candidate, **no slot cap**. Eval `MUST_SURFACE` pass = obligation in **top-3** alerts. Gate `critical_recall` = mean of per-checkpoint **top-3** critical recall.

### Decomposition table (all candidates, all 3 reps)

`obl`/`resp`/`imp`/`ts`/`act` = stored semantic features. `near/overdue` and `cal` are deterministic boosts. `gates` = confidence + mode + noise (engine_suppressed called out). Rank is among **surfaced** candidates only.

| checkpoint | rep | candidate | obl | resp | imp | ts | act | near/overdue | cal | composite | ≥0.72? | gates | decision | rank |
| --- | ---: | --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | --- | --- | --- | ---: |
| cp-2026-01-19T10:00 | 0 | brunch_book | 0.90 | 0.85 | 0.70 | 0.30 | 0.40 | 0.0000 | 0.05 | 0.6850 | no | pass | context |  |
| cp-2026-01-19T10:00 | 0 | token_audit | 0.75 | 0.85 | 0.70 | 0.30 | 0.90 | 0.0000 | 0.00 | 0.6725 | no | pass | context |  |
| cp-2026-01-19T10:00 | 0 | atlas_review | 0.70 | 0.80 | 0.60 | 0.30 | 0.70 | 0.0000 | 0.00 | 0.6050 | no | pass | context |  |
| cp-2026-01-19T10:00 | 0 | empty_states | 0.60 | 0.90 | 0.50 | 0.30 | 0.70 | 0.0000 | 0.00 | 0.5850 | no | engine_suppressed | suppress |  |
| cp-2026-01-19T10:00 | 1 | brunch_book | 0.90 | 0.95 | 0.80 | 0.70 | 0.85 | 0.0000 | 0.05 | 0.8875 | yes | pass | surface | 1 |
| cp-2026-01-19T10:00 | 1 | token_audit | 0.80 | 0.70 | 0.60 | 0.40 | 0.90 | 0.0000 | 0.00 | 0.6650 | no | pass | context |  |
| cp-2026-01-19T10:00 | 1 | atlas_review | 0.90 | 0.85 | 0.70 | 0.20 | 0.80 | 0.0000 | 0.00 | 0.6700 | no | pass | context |  |
| cp-2026-01-19T10:00 | 1 | empty_states | 0.55 | 0.80 | 0.60 | 0.30 | 0.20 | 0.0000 | 0.00 | 0.4925 | no | engine_suppressed | suppress |  |
| cp-2026-01-19T10:00 | 2 | brunch_book | 0.88 | 0.90 | 0.72 | 0.55 | 0.81 | 0.0000 | 0.05 | 0.8170 | yes | pass | surface | 1 |
| cp-2026-01-19T10:00 | 2 | token_audit | 0.90 | 0.80 | 0.85 | 0.40 | 0.90 | 0.0000 | 0.00 | 0.7475 | yes | pass | surface | 2 |
| cp-2026-01-19T10:00 | 2 | atlas_review | 0.90 | 0.90 | 0.60 | 0.30 | 0.70 | 0.0000 | 0.00 | 0.6750 | no | pass | context |  |
| cp-2026-01-19T10:00 | 2 | empty_states | 0.60 | 0.90 | 0.50 | 0.20 | 0.30 | 0.0000 | 0.00 | 0.5000 | no | engine_suppressed | suppress |  |
| cp-2026-01-20T11:00 | 0 | brunch_book | 0.90 | 0.90 | 0.70 | 0.60 | 0.50 | 0.0000 | 0.05 | 0.7850 | yes | pass | surface | 1 |
| cp-2026-01-20T11:00 | 0 | token_audit | 0.80 | 0.70 | 0.60 | 0.30 | 0.90 | 0.0167 | 0.00 | 0.6567 | no | pass | context |  |
| cp-2026-01-20T11:00 | 0 | atlas_review | 0.85 | 0.90 | 0.80 | 0.30 | 0.75 | 0.0000 | 0.00 | 0.7000 | no | pass | context |  |
| cp-2026-01-20T11:00 | 0 | empty_states | 0.70 | 0.80 | 0.50 | 0.40 | 0.30 | 0.0000 | 0.00 | 0.5550 | no | engine_suppressed | suppress |  |
| cp-2026-01-20T11:00 | 1 | brunch_book | 0.90 | 0.90 | 0.80 | 0.85 | 0.90 | 0.0000 | 0.05 | 0.9225 | yes | pass | surface | 1 |
| cp-2026-01-20T11:00 | 1 | token_audit | 0.85 | 0.70 | 0.60 | 0.30 | 0.90 | 0.0167 | 0.00 | 0.6692 | no | pass | context |  |
| cp-2026-01-20T11:00 | 1 | atlas_review | 0.90 | 0.90 | 0.70 | 0.20 | 0.80 | 0.0000 | 0.00 | 0.6800 | no | pass | context |  |
| cp-2026-01-20T11:00 | 1 | empty_states | 0.60 | 0.90 | 0.50 | 0.40 | 0.60 | 0.0000 | 0.00 | 0.5950 | no | engine_suppressed | suppress |  |
| cp-2026-01-20T11:00 | 2 | brunch_book | 0.92 | 0.95 | 0.85 | 0.88 | 0.90 | 0.0000 | 0.05 | 0.9525 | yes | pass | surface | 1 |
| cp-2026-01-20T11:00 | 2 | token_audit | 0.80 | 0.90 | 0.60 | 0.30 | 0.90 | 0.0167 | 0.00 | 0.6967 | no | pass | context |  |
| cp-2026-01-20T11:00 | 2 | atlas_review | 0.90 | 0.90 | 0.70 | 0.20 | 0.80 | 0.0000 | 0.00 | 0.6800 | no | pass | context |  |
| cp-2026-01-20T11:00 | 2 | empty_states | 0.60 | 0.90 | 0.50 | 0.30 | 0.60 | 0.0000 | 0.00 | 0.5700 | no | engine_suppressed | suppress |  |

Brunch always receives **+0.05 calendar** (`cal-brunch-parents` → `calendar_proximity_hours=0.5`). Token never does.

### Token-audit classification (per checkpoint/rep)

| checkpoint | rep | composite | ≥0.72? | decision | rank | Top-3 contract | layer |
| --- | ---: | ---: | --- | --- | ---: | --- | --- |
| Jan 19 | 0 | 0.6725 | no | context | — | miss | **genuine qualification failure** |
| Jan 19 | 1 | 0.6650 | no | context | — | miss | **genuine qualification failure** |
| Jan 19 | 2 | 0.7475 | yes | surface | 2 | **pass** | surfaced inside Top-3 (not an eval bug) |
| Jan 20 | 0 | 0.6567 | no | context | — | miss | **genuine qualification failure** |
| Jan 20 | 1 | 0.6692 | no | context | — | miss | **genuine qualification failure** |
| Jan 20 | 2 | 0.6967 | no | context | — | miss | **genuine qualification failure** |

No row is “composite ≥ 0.72 but another gate.” No row is “surfaced outside Top-3.” No eval-bug row.

### Brunch vs token

- Token `actionability_now` **0.9 on all 6 reps**; `time_sensitivity` **0.3–0.4**.
- Brunch `time_sensitivity` **0.3–0.88** (rep variance) and always gets **+0.05 calendar** boost; due dates (Jan 22 12:00) are **outside** the 36h near-term window on both checkpoints (74h / 49h).
- Token due Jan 21 17:00: **no** near-term boost on Jan 19 (55h); **+0.0167** on Jan 20 (30h) — not enough to reach 0.72.
- Jan 19 rep0: **both** brunch (0.685) and token (0.6725) fail qualification → empty `policy_judgement`.
- When token does qualify (Jan 19 rep2, 0.7475), brunch still ranks higher (0.817) but **both surface** and Top-3 passes.

### Three-layer metrics (offline)

**Jan 19/20 only** (MUST_SURFACE critical obligation-reps: token on both days; brunch from Jan 20):

| Layer | Metric | Value |
| --- | --- | --- |
| Qualification | Attention-eligibility recall | **0.44** (4/9) |
| Ranking | Critical recall@1 / @2 / @3 | 0.25 / 0.42 / 0.42 |
| Presentation | Presented-slot recall N=1 / N=2 | 0.25 / 0.42 |
| Ranking | MRR | 0.33 |

N=2 equals @2 because production has **no slot budget** — cutting to 2 only helps when the item already surfaced. It does **not** help the 5 below-threshold token reps.

Hardest-10 offline (same formula, all 10 cps): eligibility recall 0.58 (7/12); critical recall@1 0.78, @2/@3 0.88.

### Analysis model A vs B → outcomes A/B/C/D

- **A (0.72 as eligibility):** token eligible on **1/6** Jan 19/20 reps.
- **B (as implemented):** same 1/6 surface (other gates pass whenever composite ≥ 0.72 here). Eval Top-3 **passes** that rep; Top-1 does not (brunch rank 1).

**Currently supported: C primary** (genuine qualification failure on 5/6 token reps). **B is the mechanism** (one composite, `time_sensitivity` 0.25 vs `actionability_now` 0.15, plus brunch-only calendar boost). **A** only describes the Top-1 miss on the one qualifying rep — it does **not** explain gate `critical_recall` failures (those use Top-3). **D** remains an author-intent ambiguity (token `expected_surface_window` says “surface Figma link as **next action**”; Jan 21 contract writes “attention (brunch) ≠ next action (token prep)”) — recorded, **no** `support_contracts.yaml` edit.

### Crisp finding

> LLM recognises the task as actionable (`actionability_now=0.9`); the qualification formula weights `time_sensitivity` more than actionability, and brunch gets a calendar boost token does not, so newly unblocked work stays below `0.72` on 5/6 reps. Slot budget 2 would not rescue those reps.

### MUST_SURFACE semantics (read-only; ambiguity recorded)

| # | Semantics | Evidence |
| --- | --- | --- |
| 1 | NEEDS YOU / attention-eligible | Eval `_score_attention_contract` uses **top-3**, not top-1 |
| 2 | Visible somewhere now | UI “two things need you”; production N unbounded |
| 3 | Interrupt now | `minimum_priority: 5` on brunch; `top1_critical_recall` exists as a separate metric |

Token window text mixes (1) with next-action language. Do not rewrite truth in R-L10.

---

## Phase 1 closure (2026-08-17) — Outcome C

**Genuine qualification failure.** Privacy-safe causal relations materially improve semantic understanding of newly unblocked work, but the current deterministic qualification formula does not reliably translate increased actionability into NEEDS YOU eligibility. Five of six Jan 19/20 token-audit reps remain below the 0.72 surface threshold.

| Layer | Verdict |
| --- | --- |
| LLM semantic interpretation | ✅ Improved (R-L09 Step 7) |
| Attention qualification | ⚠️ **Bottleneck** — Outcome C |
| Ranking | ✅ **Exonerated** — Jan 19 rep2 rank 2 still Top-3 pass |
| Top-3 evaluation | ✅ **Exonerated** — passes when token qualifies |
| Confidence / noise gates | ✅ **Exonerated** — pass on all token rows |
| Presentation cardinality | ✅ **Investigation complete** — N-unbounded; not the miss |

**Jan 19 rep2 proof:** when token qualifies (composite 0.7475, rank 2), Top-3 eval passes — downstream pipeline works.

**Phase 2:** architectural/design research on urgency vs opportunity and NEEDS YOU semantics — **no weight tuning yet**. See Phase 2 section above.

**Reporting note:** gate aggregate labelled `critical_recall` / “MUST_SURFACE recall (critical)” is implemented as **`top3_critical_recall`** in `llm_benchmark.py` — document for eventual metric-label correction (not a Phase 1 blocker).
