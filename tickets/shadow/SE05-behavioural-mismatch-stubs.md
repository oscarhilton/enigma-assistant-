# SE05 — Behavioural mismatch detector stubs

| Field | Value |
| --- | --- |
| Status | `todo` |
| Branch | `ticket/SE05-behavioural-mismatch-stubs` |
| Domain | `shadow` |
| Baseline | [shadow-silence-evaluation.md](../../docs/architecture/shadow-silence-evaluation.md) |

## Package boundary (hard)

- May edit: `packages/evaluation/**` for mismatch signal types + stub detectors
- May edit: thin joins to first-party action / source-delta events already in Core (coordinate with SE01)
- May edit: tests under `packages/evaluation/tests/**`
- Must **not** implement keyloggers, clipboard monitors, or OS-wide surveillance
- Must **not** auto-label `FALSE_NEGATIVE` from signals alone
- Must **not** edit Demo attention UI or `EnvironmentMode`

## Hard depends

- None for type stubs

## Soft depends (~)

- SE04 frozen suppress snapshots
- SE01 user-action log
- S04 attention log

## Unlocks / enhances

- Suppression-review queue for SE06/SE09 adjudication
- Day-freeze “became relevant from new info” vs “should have surfaced”

## Non-goals

- Full product analytics
- Training on mismatch labels in this ticket
- Changing suppress thresholds

## Acceptance criteria

- [ ] Typed stub for `SuppressionReviewCandidate` (subject_ref, prior_decision_id, signal_kind, observed_at, auto_fail=false)
- [ ] Example signal kinds: late_reply_phrase, calendar_edit_near_event, reminder_derived_from_message, subject_engaged_soon_after
- [ ] Detector stub maps fixture events → review candidates without setting gold failure
- [ ] Docs state behavioural evidence ≠ ground truth ([ADR-009](../../docs/adr/009-silence-as-prediction.md))
- [ ] Tests: fixture pipeline; no Demo ground_truth import

## Test plan

- Unit: three signal fixtures produce review candidates with `auto_fail=false`
- Guard: module import does not touch `scenarios/**/ground_truth`

## Privacy constraints

- First-party Enigma observations only
- No raw Note bodies in signal payloads
