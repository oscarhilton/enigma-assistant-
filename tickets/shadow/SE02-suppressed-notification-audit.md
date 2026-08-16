# SE02 — Suppressed notifications audit

| Field | Value |
| --- | --- |
| Status | `todo` |
| Branch | `ticket/SE02-suppressed-notification-audit` |
| Domain | `shadow` |
| Baseline | [shadow-evaluation.md](../../docs/architecture/shadow-evaluation.md) (Q3 overestimate; delivery honesty) |

## Package boundary (hard)

- May edit: notification / delivery gateways under `apps/api/**`, `apps/worker/**`, desktop notify hooks if present
- May edit: `packages/evaluation/**` (or `packages/shadow_eval/**`) for `shadow.suppressed_notification/v0` + audit append API
- May edit: tests with an exploding / counting notifier stub
- Must not edit: `EnvironmentMode` / env enum (S01)
- Must not edit: attention ranking algorithms; Demo UI chrome

## Hard depends

- None for audit schema stubs
- Live suppress path: S02 notification suppression (when claimed)

## Soft depends (~)

- S01 (Shadow mode flag)
- S02 (structural suppress-all policy)
- SE01 (candidate_id / subject_ref alignment)
- E04 tray notifications (channel vocabulary only)

## Unlocks / enhances

- Honest Q3 (“would have notified” vs user ignore)
- Proof that Shadow never delivers
- Weekly review excerpt of suppress volume ([SE03](./SE03-weekly-shadow-review.md))

## Non-goals

- Enabling user-visible notifications in Shadow
- Marketing / push infrastructure
- Full notification preference UI

## Acceptance criteria

- [ ] Stub schema `shadow.suppressed_notification/v0` documented and fixture-validated
- [ ] Audit writer interface (append-only) with tests against tmp Shadow root
- [ ] Contract test: under Shadow policy, notifier invoke count == 0 while audit rows increase
- [ ] Redacted preview fields only (no raw mail bodies in audit)
- [ ] Docs cross-link from [shadow-evaluation.md](../../docs/architecture/shadow-evaluation.md)

## Test plan

- Exploding notifier: generating a would-notify candidate must not call it
- Audit row references `candidate_id` from attention stub

## Privacy constraints

- Suppression is structural; audit stays local
- Do not ship notification contents to hosted models
