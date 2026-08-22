# CLOUD-05 — Cursor relay dry-run default contract

| Field | Value |
| --- | --- |
| Status | `in_progress` |
| Branch | `cursor/relay-dry-run-default-contract-401e` |
| Domain | `platform` |
| PR | [#150](https://github.com/oscarhilton/enigma-assistant-/pull/150) (draft) |

## Intent

Stop omitting `job_brief.authorization.dry_run` from silently converting normal `dispatch` / `request_review` creates into plan-only dry runs.

## Hard depends

- [CLOUD-03](./CLOUD-03-cursor-relay-create-contract.md) `done`

## Package boundary (hard)

May edit:

- `apps/cursor-relay/**`
- `docs/cloud-agents.md`, `docs/cloud-agents/**` (dry-run contract notes only)
- `tickets/platform/CLOUD-05*`

Must not edit:

- Unrelated relay features (follow-up, PR targeting, model pass-through)
- Product conversation / routing (`apps/api`, `apps/web` product paths)

## Contract

| `dry_run` | Behaviour |
| --- | --- |
| explicit `true` | Genuine no-POST dry run (redacted plan) |
| explicit `false` | Live create, subject to existing authorization |
| omitted + live write auth (`allow_push` or `allow_open_pr`) | Live create (do **not** downgrade to dry-run) |
| omitted without live write auth | Fail clearly (`live_not_authorized`) — do **not** pretend success as a dry run |

Preserve: fail-safe (no silent POST without write flags when omitted), idempotency, no-secrets, PR targeting, model-default pass-through (PR #146). Merge remains relay-forbidden.

## Acceptance criteria

- [x] Explicit `dry_run=true` never `POST /v1/agents`
- [x] Explicit `dry_run=false` remains live subject to authorization
- [x] Omitted `dry_run` with sufficient auth proceeds live
- [x] Omitted `dry_run` without sufficient auth fails clearly (not a successful dry-run)
- [x] Focused dispatch + `request_review` regression tests for the four cases
- [x] Prompt injection does not claim `dry_run=True` when the flag was omitted
