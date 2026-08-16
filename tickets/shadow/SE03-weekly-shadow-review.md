# SE03 — Weekly shadow review artefact

| Field | Value |
| --- | --- |
| Status | `todo` |
| Branch | `ticket/SE03-weekly-shadow-review` |
| Domain | `shadow` |
| Baseline | [shadow-evaluation.md](../../docs/architecture/shadow-evaluation.md) (Q1–Q7 packaging) |

## Package boundary (hard)

- May edit: `packages/evaluation/**` (or `packages/shadow_eval/**`) CLI / report builder stubs
- May add: Markdown + JSON templates under `docs/` or package `templates/`
- May edit: tests that render an empty / fixture week report
- Must not edit: `EnvironmentMode` (S01); full web dashboard / product UI
- Must not edit: Demo Alex ground-truth reports as if they were Shadow reviews

## Hard depends

- None for template + empty `metrics.json` stub

## Soft depends (~)

- [SE01](./SE01-action-vs-attention.md) (joins for Q1/Q2/Q5/Q6)
- [SE02](./SE02-suppressed-notification-audit.md) (suppress volume for Q3)
- S01/S03 (live logs when available)

## Unlocks / enhances

- Single artefact answering “did real life behave like Alex?” week by week
- Human labelling slot for Q4 relationships + Q7 novel misses

## Non-goals

- Polished product UI or email digests
- Automated statistical significance claims
- Remote upload of weekly reviews

## Acceptance criteria

- [ ] Layout `reports/shadow/<week_id>/{review.md,metrics.json,novel_misses.json}` documented
- [ ] `review.md` template with sections Q1–Q7 matching the architecture rubric
- [ ] CLI stub (e.g. `enigma-shadow-review`) writes the skeleton from fixtures; metrics may be `null` / `unknown`
- [ ] Fixture test: golden skeleton snapshot (no Private/Demo paths mixed in)
- [ ] Explicit note: Demo ground truth ≠ Shadow behaviour labels

## Test plan

- Run stub on tiny fixture → files exist; Q sections present
- Refuse output path under `~/.enigma/demo/` when Shadow root helpers exist (soft if S01 not merged)

## Privacy constraints

- Reports local-only under Shadow root / developer `reports/shadow/`
- Novel-miss catalogue stores ids + short labels — not raw mail
