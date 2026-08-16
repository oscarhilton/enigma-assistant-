# SE07 — Miss-report intake

| Field | Value |
| --- | --- |
| Status | `todo` |
| Branch | `ticket/SE07-miss-report-intake` |
| Domain | `shadow` |
| Baseline | [shadow-silence-evaluation.md](../../docs/architecture/shadow-silence-evaluation.md) |

## Package boundary (hard)

- May edit: `packages/evaluation/**` for miss-report schema + reconstruction stub
- May edit: `apps/api/**` thin intake route stub under Shadow
- May edit: tests
- Must **not** edit Demo evaluation ground truth as live labels
- Must **not** ship full UI (SE09 may render intake)

## Hard depends

- None for schema + fixture reconstruction

## Soft depends (~)

- SE04 frozen snapshots (what was knowable then)
- SE08 Silent Miss Rate
- SE03 weekly novel-miss log

## Unlocks / enhances

- Gold-standard false negatives with failure stage
- S06 exit honesty inputs

## Non-goals

- Auto-filing Demo corpus PRs from misses
- Remote LLM adjudication without ADR

## Acceptance criteria

- [ ] Intake schema: pointer (email/calendar/reminder/person) and/or free-text description; reported_at
- [ ] Reconstruction stub attaches prior decision snapshot when subject was considered; else marks `not_in_candidate_set`
- [ ] Failure stage enum: `retrieval` | `entity` | `reasoning` | `surface_threshold`
- [ ] Gold label: `FALSE_NEGATIVE` only after intake (+ optional confirm), not from SE05 signals alone
- [ ] Periodic prompt copy contract: “Did anything need your attention that Enigma failed to identify?”
- [ ] Tests: reconstruct known suppress → stage `surface_threshold`; missing candidate → `retrieval`

## Test plan

- Fixture: suppressed snapshot + miss report → FN with stage
- Fixture: never-seen subject → FN with `retrieval`

## Privacy constraints

- Miss reports stay local; exports prefer PERSON_* / reason codes
- Do not upload raw mail bodies to hosted models
