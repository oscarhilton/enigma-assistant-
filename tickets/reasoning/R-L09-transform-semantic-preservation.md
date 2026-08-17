# R-L09 — Transform semantic preservation sprint

| Field | Value |
| --- | --- |
| Status | `in_progress` (Step 6 — prompt wiring) |
| Branch | `ticket/R-L09-transform-semantic-preservation` |
| Domain | `reasoning` + `transformation` + `evaluation` |

## Hypothesis

The live reasoning gate (`no_win`) used **`evaluation_transformed_v1`**, not `DefaultEnigmaTransformer`.
Recall regressions on token-inventory checkpoints suggest **lost task-relevant semantics** under
privacy transformation — not model incapacity (full_synthetic oracle recall 1.00 on hardest 10).

> Enigma should forget *who* and *what* it can, while preserving *why things matter*.

## Scientific record (frozen chronology)

| Phase | Result |
| --- | --- |
| **R-L09.1** | Offline transform lacked causal semantics → fixed (`relations[]`, BLOCKED_BY resolution). |
| **R-L09.2** | Offline causal-preservation gate passed (Jan 19/20). Production parity wired as `evaluation_transformed_v2`. |
| **R-L09.3** | Live hardest-10: **NO MOVEMENT** — v2 critical recall **0.85** vs historical v1 **0.85**. Investigation: `relations[]` never entered the semantic judge prompt. Classified as **integration/wiring negative**, not hypothesis falsification. |
| **R-L09.4** | **Next (Step 6):** Route privacy-gated `TransformedContext` directly into semantic judge prompt. Then re-run hardest-10 only (~$0.05). |

### R-L09.3 detail (2026-08-17 live run)

| Column | Critical recall | Notes |
| --- | --- | --- |
| v1 (this run) | 1.00 | **Invalid** — prompt-build failures fell back to Arm A scoring |
| v2 | **0.85** | Valid — real model calls |
| full_synthetic | 1.00 | Valid but **byte-identical prompt to v2** (confound) |

Jan 19/20 v2 semantics unchanged: `time_sensitivity` ~0.3, `LOW_URGENCY` / `CONTEXT_ONLY`.

**Conclusion:** `evaluation_transformed_v2` preserved causal relations offline and passed privacy checks, but those relations were **not included in the semantic judge prompt**. This run falsifies the assumption that the current live judge path consumes `TransformedContext` — not the semantic-preservation hypothesis itself.

---

## Package boundary (hard)

### Steps 1–5 (done / frozen)

- `packages/transformation/...` — **FROZEN** after Step 5. Do not edit relations, thresholds, or transformer logic in Step 6.
- `evaluation_transformed_v1_frozen.py` — **FROZEN**
- `snapshot_to_production_transformed()` / `evaluation_transformed_v2` — **FROZEN**

### Step 6 (prompt wiring — this ticket)

- May create/edit:
  - `packages/evaluation/src/personal_enigma/evaluation/llm_benchmark.py` (serialisation + prompt builder only)
  - `packages/evaluation/src/personal_enigma/evaluation/live_benchmark.py` (invalid-arm handling)
  - `packages/evaluation/src/personal_enigma/evaluation/v2_hardest_10.py` (harness hard-fail)
  - `packages/evaluation/tests/test_transformed_context_prompt.py` (new)
  - `packages/evaluation/tests/test_{llm_benchmark,live_gate}.py` (adjust as needed)
- May edit: `docs/adr/012-reasoning-value-gate-decision.md`, `docs/reports/reasoning-value-gate-live-report.md`
- Must not edit: `packages/transformation/**` (v2 frozen), `packages/attention/**` (policy frozen until Step 7 inspect), ingestion, apple-bridge

## Hard depends

- R-L08 live exit report (`done`)
- R-L09 Steps 1–5 (`done`)

---

## Steps 1–5 — completed

### Phase 1 — Diagnose (offline) ✅

- [x] Transform diff + loss taxonomy
- [x] Offline gate checklist (dependency / resolution / causality)

### Phase 2 — Preserve (deterministic) ✅

- [x] `SemanticRelation` + `TransformedContext.relations[]`
- [x] `DefaultEnigmaTransformer.build_remote_attention_context()` — production parity
- [x] Hard title pseudonymisation + privacy gate

### Phase 3 — Live hardest-10 (Step 5) ✅

- [x] Triple-column harness (v1 frozen / v2 / full_synthetic)
- [x] Predeclared decision rules
- [x] Result: **NO MOVEMENT** under current wiring (see scientific record)

---

## Step 6 — Transformed-context prompt wiring

**Type:** Evaluator / integration change only. **`evaluation_transformed_v2` stays completely frozen.**

### Problem

Two parallel paths diverged at the model-input boundary:

```
TransformedContext ──────────────┐
  summary, entities, relations[]   │  passed assert_remote_safe()
                                   │  NOT sent to Fireworks
snapshot_to_context_dict() ──────┴→ build_semantic_judge_prompt() → Fireworks
```

Fireworks transport sends **only the prompt string** — not the `TransformedContext` object. The Step 5 experiment therefore never exposed the new semantic representation to the model.

### Goal

Single pipeline — no conceptual fork:

```
DefaultEnigmaTransformer
        ↓
TransformedContext  (summary, entities, relations[], metadata)
        ↓
assert_remote_safe(ctx)
        ↓
serialise_transformed_context_for_judge(ctx, …)
        ↓
build_semantic_judge_prompt(ctx, candidate, …)
        ↓
Fireworks
```

### Hard invariant

> Model input must be derivable from the object that passed `assert_remote_safe(transformed_context)`.

No second private-ish snapshot representation may be assembled for the prompt after privacy transformation.

```
PRIVATE SNAPSHOT → TRANSFORM ONCE → PRIVACY GATE → SERIALISE FOR MODEL → REMOTE CALL
```

Forbidden shape:

```
PRIVATE SNAPSHOT → transformed context → privacy gate
                └→ separate snapshot prompt builder → model   ← this confound
```

### API shape (proposed)

Replace snapshot-derived context in B2 prompts:

```python
def serialise_transformed_context_for_judge(
    ctx: TransformedContext,
    *,
    candidate: AttentionCandidateObservation,
    checkpoint_at: datetime,
    privacy: Literal["legacy_v1", "remote_safe"],
) -> dict[str, Any]:
    """Privacy-gated wire shape for semantic judge — sole source for prompt context_json."""
```

```python
def build_semantic_judge_prompt(
    ctx: TransformedContext,
    candidate: AttentionCandidateObservation,
    *,
    checkpoint_at: datetime,
    attention_only: bool = False,
    privacy: Literal["legacy_v1", "remote_safe"] = "remote_safe",
) -> str:
```

- `score_arm_b` / `_judge_candidate_semantic` pass the same `ctx` used for `assert_remote_safe`.
- `snapshot_to_context_dict()` remains for **offline diagnostics only** (transform diff labels) — not for live judge prompts.
- Evaluation and production share one serialisation path (evaluation calls the same function on its `TransformedContext`).

### Prompt payload (structured JSON)

Embed as `context_json` in the semantic judge prompt — not prose dump:

```json
{
  "checkpoint": {
    "now": "2026-01-19T10:00:00Z",
    "day_of_week": "Monday",
    "is_weekend": false
  },
  "summary": "Four open tasks are under consideration.",
  "candidate": {
    "id": "item-obligation_token_audit",
    "title": "Draft colour + spacing token inventory",
    "obligation_ids": ["obligation_token_audit"],
    "evidence_ids": ["mail-…", "rem-…"],
    "score": 0.82
  },
  "entities": ["OBLIGATION_TOKEN_AUDIT", "TASK_TOKEN_AUDIT"],
  "relations": [
    {
      "type": "BLOCKED_BY",
      "subject": "TASK_TOKEN_AUDIT",
      "object": "RESOURCE_FIGMA_LINK",
      "state": "resolved",
      "resolved_by": "PERSON_B",
      "resolved_at": "2026-01-18T…",
      "causal": "RESOURCE_FIGMA_LINK arrival made TASK_TOKEN_AUDIT actionable"
    }
  ],
  "memory": { "open_obligation_ids": ["…"] },
  "retrieval": []
}
```

Notes:

- **Candidate** is the item under judgement (pseudonymised title when `privacy=remote_safe`; raw title when `legacy_v1` for frozen v1 column only).
- **Relations** come from `ctx.relations` — not re-inferred from snapshot.
- Temporal facts from `checkpoint_at` (same helper as today: `checkpoint_temporal_facts`).
- Optional `memory` / `retrieval` from snapshot observation — these are already in the judge contract; keep them if still needed for scoring, but do not rebuild candidate lists from snapshot.

### Relations authoritative over summary

Add explicit judge instruction (append to `_SEMANTIC_JUDGE_PROMPT` system/user block):

> When `summary` and `relations[]` disagree, treat **`relations[]` as authoritative** for dependency, blocker resolution, and actionability transitions. The summary may compress or lag; structured relation facts override prose.

This prevents summary compression from undoing graph benefit.

### Forbidden in serialised prompt

Must never appear:

- `MUST_SURFACE`, `MUST_SUPPRESS`, `MUST_STAY_QUIET`
- `expected_surface_window`, `attention_pass`
- Arm A surfaced alerts, ground-truth labels, evaluator markers

Existing `FORBIDDEN_PROMPT_MARKERS` + `assert_prompt_safe` apply to full prompt text.

### Historical v1 isolation — hard fail (harness fix)

**Remove** the scientific danger of Arm A fallback when all parses fail:

```python
# score_arm_b — today (dangerous for ablation):
if all_judgements_failed:
    metrics = compute_support_fitness_metrics(..., alerts=snapshot.alerts)  # Arm A fallback

# Step 6 — ablation / live gate arms:
if prompt_build_failed or all_judgements_failed:
    return CheckpointArmResult(..., experiment_invalid=True, parse_error=…)
```

Triple-column harness:

```python
if expected_arm == "evaluation_transformed_v1" and prompt_build_failed:
    decision = "invalid_experiment"  # not a scored column
```

- v1 column: `prompt_privacy=legacy_v1` (explicit, never auto-inferred incorrectly).
- Any column with `experiment_invalid=True` excluded from aggregate recall; run marked **INVALID** for that arm.

---

## Step 6 acceptance criteria (offline — before any live spend)

### 1. Prompt-equivalence test

- [ ] `evaluation_transformed_v2` and `full_synthetic` prompts are **not** byte-identical.
- [ ] v2 prompt contains privacy-safe `relations[]` (Jan 19/20: `BLOCKED_BY`, `state=resolved`).
- [ ] full_synthetic prompt may contain additional oracle context (names in summary/entities) — ablation arm only.

### 2. Production-path test

- [ ] Evaluation and production call the **same** `serialise_transformed_context_for_judge()` on `TransformedContext`.
- [ ] No alternate `snapshot_to_context_dict()` candidate/context assembly in `build_semantic_judge_prompt`.

### 3. Privacy invariant

- [ ] `assert_remote_safe(ctx)` passes for v2 production path fixtures.
- [ ] Serialised prompt blob passes `assert_no_raw_identity_in_text` (and existing prompt privacy checks).
- [ ] Raw display names (`Elena`, `Jordan`, …) absent; pseudonyms / semantic tokens allowed.

### 4. Causal fixture (Jan 19/20)

- [ ] Prompt contains `TASK_TOKEN_AUDIT`, `BLOCKED_BY`, `state=resolved` (or equivalent token forms).
- [ ] Ideally includes causal transition string from relation `causal` field.

### 5. No evaluator truth

- [ ] Property test or grep guard: serialised payload + prompt exclude forbidden evaluator markers.

### 6. Harness hard-fail

- [ ] Unit test: simulated prompt-build failure on v1 arm → `experiment_invalid`, **not** Arm A recall.
- [ ] Triple-column report surfaces `invalid_experiment` per arm when applicable.

---

## Step 7 — Live re-gate (after Step 6 offline green)

**Scope:** Hardest-10 only. **No main.** Budget cap ~$0.05.

**Frozen:** v2 transform, policy, truth, model, evaluator (except prompt serialisation landed in Step 6).

### Comparison columns

| Column | Expected recall (anchor) |
| --- | --- |
| v1 (frozen, legacy_v1 prompt) | 0.85 historical |
| v2 + relations in prompt | **???** |
| full_synthetic | 1.00 historical |

### Predeclared outcomes

| Outcome | Criteria | Action |
| --- | --- | --- |
| **A — Hypothesis survives** | v2 recall **0.95–1.00** materially above 0.85; suppress ≥ 0.95; privacy = 0 | Eligible for **main-only** rerun |
| **B — Partial signal** | Jan 19/20 semantics move (e.g. time_sensitivity 0.3→0.7, actionability 0.5→0.85) but aggregate ~0.85 | Inspect new failures; **do not** tune thresholds yet |
| **C — Falsified** | Still ~0.85 **and** Jan 19/20 semantics unchanged, with relations actually in prompt | Stop — clean negative for GPT-OSS-120B + Alex-v1 |

CLI: `uv run enigma-eval --reasoning-gate-live --live --phase hardest-10-v2`

---

## Information-loss taxonomy

(Unchanged — see Steps 1–5.)

## Privacy constraints

- Relations use pseudonyms/tokens only — never raw attendee emails or wholesale Notes
- Serialised prompt is a second privacy check surface (after `assert_remote_safe`)
- Deterministic tests must not require live Fireworks calls for Step 6 acceptance

## Test plan (Step 6)

```bash
uv run pytest packages/evaluation/tests/test_transformed_context_prompt.py -q
uv run pytest packages/evaluation/tests/test_production_transform.py packages/evaluation/tests/test_transform_diff.py -q
uv run ruff check packages/evaluation/
```
