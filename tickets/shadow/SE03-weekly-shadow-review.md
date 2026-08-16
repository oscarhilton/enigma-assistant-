# SE03 — Weekly Shadow review artefact

| Field | Value |
| --- | --- |
| Status | `todo` |
| Branch | `ticket/SE03-weekly-shadow-review` |
| Domain | `shadow` |
| Baseline | [shadow-evaluation.md](../../docs/architecture/shadow-evaluation.md) |

## Package boundary (hard)

- May edit: review builder under `packages/evaluation/**` (or agreed shadow-eval package) + CLI entrypoint declared in PR
- May edit: schema examples under `docs/` or package fixtures
- May write review files only under the Shadow storage root (when S01/S06 root exists; tmp_path in tests otherwise)
- Must **not** edit: `EnvironmentMode` / simulation environment module (S01)
- Must **not** ship a full weekly-review UI (CLI / file artefact only)
- Must **not** mix Demo scenario data into the review scores

## Hard depends

- None for schema + empty-report fixture

## Soft depends (~)

- SE01 (action vs attention metrics)
- SE02 (suppression summary)
- S01 `done` / S02 (Shadow root path)
- S04 (attention log volume)
- S05 (comparison stub interfaces)
- S06 (exit criteria inputs)
## Unlocks / enhances

- Rubric questions 4, 5, 7 (relationships sample, memory improvement curves, novel misses)
- Honest Phase 3 exit discussion inputs

## Non-goals

- Emailing or uploading weekly reviews
- Statistical significance claims
- Auto-filing Demo corpus PRs from novel misses (human triage only)

## Acceptance criteria

- [ ] Weekly artefact schema: config snapshot, rubric scores, relationship sample slot, novel-miss log, suppression summary, privacy note
- [ ] Builder produces JSON (optional Markdown) for a given ISO week from stub/empty inputs without crashing
- [ ] Path convention documented (`reviews/YYYY-Www.json` under Shadow root)
- [ ] Tests: golden/empty fixture; assert Demo ground truth not consulted
- [ ] Cross-link from [shadow-mode-questions.md](../../docs/architecture/shadow-mode-questions.md) / evaluation doc

## Test plan

- Build review from empty SE01/SE02 stubs → valid schema
- Reject / ignore attempts to pass Demo scenario paths as score sources

## Privacy constraints

- Relationship sample stays local; no raw contact dumps in shareable exports
- Prefer PERSON_* and coarse reason codes
- Remote model must not receive wholesale weekly logs without an ADR
