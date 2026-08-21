# CLOUD-04 — Cursor env.name resolution (dashboard vs repo file)

| Field | Value |
| --- | --- |
| Status | `in_progress` |
| Branch | `cursor/cloud-04-env-name-resolution-47cd` |
| Domain | `platform` |
| PR | [#136](https://github.com/oscarhilton/enigma-assistant-/pull/136) (draft) |

## Intent

Fix the live KERNEL-01 create blocker: Cursor returned

`No cloud environment named "enigma-assistant-" was found`

after the relay correctly applied the CLOUD-03 UUID→name mapping. Root cause: **`.cursor/environment.json` `name` is not the Cursor Cloud Agents API registry name**. Live `environment-info` for UUID `1baeb513-9c77-11f1-ba66-0e7d0216e441` reports `name: null`. API `env.name` must match the **dashboard-registered** environment name.

## Hard depends

- [CLOUD-03](./CLOUD-03-cursor-relay-create-contract.md) `done`

## Package boundary (hard)

May edit:

- `apps/cursor-relay/**`
- `docs/cloud-agents.md`, `docs/cloud-agents/**`
- `tickets/platform/CLOUD-04*`

Must not edit:

- KERNEL-01 / ROUTE-01 / RESPOND-01 / BRIEF-01 product code
- `apps/api`, `apps/web` product paths

## Acceptance criteria

- [x] Document that API `env.name` = dashboard registry name (not UUID; not assumed equal to `.cursor/environment.json` name until dashboard matches)
- [x] UUID→name map is overridable via `RELAY_ENV_UUID_TO_NAME` JSON on the relay host
- [x] HTTP 400 “No cloud environment named …” maps to distinct `cursor_env_not_found` code with allowlisted validation fields
- [x] Contract tests cover override + env-not-found classification
- [ ] Operator: Environments **list Name** for UUID `1baeb513-…` is exactly `enigma-assistant-` (or `RELAY_ENV_UUID_TO_NAME` matches the real list Name). Note: marking setup actions complete while live `environment-info.name` stays `null` / list Name blank does **not** satisfy this. Then merge/redeploy this PR; dry-run `kernel-01-dry-run-after-cloud-04-v1`; live `kernel-01-first-dispatch-v2`

## Test plan

```bash
uv run pytest apps/cursor-relay/tests -q
uv run ruff check apps/cursor-relay
```

## Non-goals

- Beginning RESPOND-01 / BRIEF-01
- Merging PRs
- Putting `CURSOR_API_KEY` in worker env
