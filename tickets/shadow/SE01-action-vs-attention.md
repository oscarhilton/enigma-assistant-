# SE01 — User actions vs attention log

| Field | Value |
| --- | --- |
| Status | `todo` |
| Branch | `ticket/SE01-action-vs-attention` |
| Domain | `shadow` |
| Baseline | [shadow-evaluation.md](../../docs/architecture/shadow-evaluation.md) |

## Package boundary (hard)

- May edit: Shadow eval stubs under `packages/evaluation/**` (preferred) **or** a thin `packages/shadow_eval/**` if evaluation package ownership conflicts — declare in PR
- May edit: `apps/api/**` / `apps/worker/**` only for append-only local action / candidate log hooks
- May edit: docs cross-links under `docs/architecture/shadow-evaluation.md`
- Must **not** edit: `packages/simulation/**/environment.py` / `EnvironmentMode` (S01)
- Must **not** edit: Demo ground-truth evaluators for Alex scenarios
- Must **not** ship a full Shadow UI

## Hard depends

- None (design + stubs may land first)

## Soft depends (~)

- S01 `done` (Shadow mode / storage identity)
- S04 (Shadow attention log) — reuse candidate rows if present; otherwise stub both sides
- S05 (comparison stub interfaces for the seven goals)
- SE02 (shared subject refs with suppress audit)
## Unlocks / enhances

- Rubric questions 1, 2, 3, 6 (act-on, nearly-forgot, overestimate, timing)
- Feeds SE03 weekly review scores

## Non-goals

- Full product analytics dashboard
- Training / fine-tuning on action logs
- Changing attention ranking (measure only)
- Reading Demo `ground_truth/*.yaml` as real-user labels

## Acceptance criteria

- [ ] Typed stub (or Pydantic/dataclass) for `UserAction` and join key to attention candidates
- [ ] Comparator stub returns structured metrics (`act_on_hit`, `act_on_miss`, `late_hit`, `overestimate`, `timing_error_hours`) — empty/zero OK in tests
- [ ] Documented window / top-K config fields snapshotted with results
- [ ] Tests: API shape stable; comparator does not import Demo scenario ground truth by default
- [ ] Ticket checklist updated when stubs land

## Test plan

- Unit: construct actions + candidates; join produces expected hit/miss fixture
- Guard: importing comparator does not load `scenarios/**/ground_truth`

## Privacy constraints

- Actions and joins stay on Shadow/Private storage roots
- Prefer transformed `subject_ref` / PERSON_* over raw emails
- No remote scoring of action logs without an ADR
