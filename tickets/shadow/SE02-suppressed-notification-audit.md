# SE02 — Suppressed notifications audit

| Field | Value |
| --- | --- |
| Status | `todo` |
| Branch | `ticket/SE02-suppressed-notification-audit` |
| Domain | `shadow` |
| Baseline | [shadow-evaluation.md](../../docs/architecture/shadow-evaluation.md) |

## Package boundary (hard)

- May edit: audit model + writer under `packages/evaluation/**` (or agreed shadow-eval package)
- May edit: thin hooks beside notification delivery code **only** to record would-notify rows — prefer coordinating interface with S02 rather than owning the gateway
- May edit: tests that an exploding notifier is never called while audit rows accumulate
- Must **not** edit: `EnvironmentMode` enum / env parsing (S01)
- Must **not** enable real user-visible notifications in Shadow
- Must **not** build a full audit UI

## Hard depends

- None for schema + fixture tests

## Soft depends (~)

- S01 (mode identity)
- S02 (structural notification suppression) — SE02 measures/audits; S02 enforces silence
- SE01 (candidate ids / ranks for join)

## Unlocks / enhances

- Rubric question 3 (importance overestimate) with a clean “would have bothered you” denominator
- SE03 weekly suppression summary

## Non-goals

- Designing Private Mode notification UX
- Push/email/SMS product infrastructure
- Changing what attention selects — only recording what delivery would have done

## Acceptance criteria

- [ ] `SuppressedNotificationAudit` schema (id, timestamp, candidate_id, channel, suppression_reason, rank/score, subject_ref)
- [ ] Writer path callable when would-notify is true under Shadow policy (stub OK if S02 not merged)
- [ ] Tests: audit rows written; notifier invoke count == 0 with hostile/exploding notifier stub
- [ ] Docs link from [shadow-evaluation.md](../../docs/architecture/shadow-evaluation.md)

## Test plan

- Unit: serialize/deserialize audit row
- Hostile: generate would-notify candidates → N audit rows, 0 notifier calls

## Privacy constraints

- Audit bodies must not include raw mail/Notes content
- Suppression reason is structural (`shadow_mode`), not a forgettable UI toggle in this track
- Artefacts stay local to Shadow storage
