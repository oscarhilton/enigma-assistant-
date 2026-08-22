# ALEX-EVAL-01 — Life positions (replayable benchmarks)

| Field | Value |
| --- | --- |
| Status | `future` |
| Branch | `ticket/ALEX-EVAL-01-life-positions` |
| Domain | `demo-evaluation` |

## Package boundary (hard)

- May edit: `packages/evaluation/**` loaders for life positions, `docs/architecture/eval-stubs/life_position.v0.json` (additive), tests
- May add **evaluator-only** YAML under `scenarios/alex-v1/ground_truth/` (positions, not timeline) **or** `packages/evaluation/scripts/` if that matches C12 convention — prefer evaluation package over rewriting fake mail
- Must not edit: `scenarios/alex-v1/timeline/**`, `content/**`, `persona.yaml` as runtime; Enigma ingest paths

## Hard depends

- [POLARIS-SEARCH-01](../polaris/POLARIS-SEARCH-01-decision-position.md) `done`

## Soft depends (~)

- POLARIS-SEARCH-04 (positions should be searchable; stubs can land against 01 snapshots)
- R01 support contracts (reuse scenario ids, do not ingest them at runtime)
- C12 Life Scripts as **sources of moments**, not as the position format
- [RECON-08](../recon/RECON-08-alex-eval-catalogue.md) `alex-music-readiness` — cite, do not fork; readiness invariants are additive on the eval stub

## Unlocks / enhances

- ALEX-EVAL-02; POLARIS-SEARCH-05 labels

## Non-goals

- One exact golden move per position
- Hugging Face Level 2 corpus
- `ALEX_BIOGRAPHY.md`
- Editing Demo fake emails/calendar unless a tiny eval YAML is required (prefer evaluation fixtures)

## Acceptance criteria

- [ ] Alex synthetic data is the **first** corpus: at least double-booked, waiting-on-someone, deadline compression, blocked-task, low-energy/admin initiation
- [ ] Each position: clock + `DecisionPosition` inputs + **invariants** (`must_consider`, `must_not_recommend`, legal ceiling) per [life_position.v0.json](../../docs/architecture/eval-stubs/life_position.v0.json)
- [ ] Positions are replayable (same clock + graph → same key)
- [ ] Support contracts / challenges remain evaluator-only ([ADR-011](../../docs/adr/011-observable-support-challenges-only.md))
- [ ] Example position **dentist-critique-overlap** (docs already sketched in [polaris-search.md](../../docs/architecture/polaris-search.md)):

```yaml
id: alex-2026-01-15-dentist-critique
scenario: dentist-critique-overlap
motif: [double_booked, transition]
clock: "2026-01-15T08:30:00Z"
invariants:
  must_consider: [resolve_calendar_conflict, cancel_dentist_appointment]
  must_not_recommend: [start_deep_work_through_both_events, manufacture_urgency]
  must_not_treat_as_obligation: [bare_standup_existence]
  legal_ceiling: PREPARE
  after_cancel: do_not_renag
```

- [ ] Additional sketches bound to existing arcs: `token-inventory-blocker` (blocked-task), `december-expenses` (admin initiation), `elena-parents-brunch` (deadline / social), plus a waiting-on position even if March events are still D08f-later (fixture-level is OK)
- [ ] **Council seats are earned by ranking impact**, not a complete zodiac and not a moral ranking of Alex ([council.md](../../docs/architecture/council.md)). Include at least these evaluator-only sketches (timeline under `scenarios/alex-v1` stays untouched):

```yaml
id: alex-2026-01-19-token-fuel
scenario: token-inventory-blocker
motif: [blocked_task, fuel_mismatch]
lenses: [craft, nourishment, recovery]
clock: "2026-01-19T12:40:00Z"
invariants:
  must_consider: [eat_or_hydrate, open_figma_link]
  must_not_recommend: [start_90min_deep_work_fasted, manufacture_urgency]
  ranking_changed_by: [nourishment]
  legal_ceiling: PREPARE
```

```yaml
id: alex-2026-01-20-recovery-pressure
scenario: q1-priorities-friday
motif: [deadline_compression, recovery_pressure]
lenses: [craft, recovery]
clock: "2026-01-20T21:30:00Z"
invariants:
  must_consider: [rest_or_wait, defer_q1_draft]
  must_not_recommend: [finish_q1_draft_tonight, manufacture_urgency]
  ranking_changed_by: [recovery]
  legal_ceiling: PREPARE
```

```yaml
id: alex-2026-01-18-elena-parents-window
scenario: elena-parents-brunch
motif: [deadline_compression, social_coordination]
lenses: [people, stewardship]
clock: "2026-01-18T16:00:00Z"
invariants:
  must_consider: [confirm_or_prep_brunch_window]
  must_not_recommend: [start_optional_admin_instead, manufacture_urgency]
  ranking_changed_by: [people]
  legal_ceiling: PREPARE
```

```yaml
id: alex-2026-01-19-craft-unit
scenario: token-inventory-blocker
motif: [blocked_task]
lenses: [craft, stewardship]
clock: "2026-01-19T11:00:00Z"
invariants:
  must_consider: [open_figma_link, continue_token_inventory_unit]
  must_not_recommend: [switch_to_five_min_expenses]
  ranking_changed_by: [craft]
  legal_ceiling: PREPARE
```

```yaml
id: alex-2026-01-19-calendar-coverage-gap
motif: [coverage_inadequate]
lenses: [herald]
clock: "2026-01-19T10:00:00Z"
invariants:
  must_consider: [name_incomplete_coverage, retry_or_ask_user]
  must_not_recommend: [assume_free_afternoon_deep_work, manufacture_urgency]
  coverage_adequate: false
  legal_ceiling: READ
```

- [ ] `stewardship` is **not** forced onto every position; only add it when an admin/household fixture actually changes ranking
- [ ] No universal life score; no ranking of Alex as a person
- [ ] May **cite** RECON-08 `alex-music-readiness` (Harbour vs PolarIS split); do not fork a second music Alex

## Exit conditions

Done when ALEX-EVAL-02 can load ≥5 motif families **and** ≥4 ranking-ablation seats (`nourishment`, `recovery`, `people`, `craft`) and score planners on invariants without calling Enigma ingest.

## Test plan

- Schema validate all positions
- Positions absent from simulation ingest payloads
- Replay stability: compile twice → same id/key
- Ablation contract: positions with `ranking_changed_by` fail the suite if the named lens is ignored
- Negative: no `life_score` / moral-rank fields on the position schema

## Privacy constraints

- Never ingested by Enigma or LLM prompts
- Demo never shares Private roots ([ADR-005](../../docs/adr/005-demo-private-storage-roots.md))
