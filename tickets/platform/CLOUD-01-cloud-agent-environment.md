# CLOUD-01 — Cloud agent environment + conductor

| Field | Value |
| --- | --- |
| Status | `in_progress` |
| Branch | `ticket/cloud-01-agent-environment` |
| Domain | `platform` |

## Package boundary (hard)

- May edit: `.cursor/**`, `docs/cloud-agents.md`, `docs/cloud-agents/**`, `AGENTS.md` (Testing table row + link only)
- Must not edit: application code under `apps/`, `packages/` except as required by future CLOUD follow-ups
- Must not implement KERNEL, RESPOND, or P03 forensics scope here

## Hard depends

- None

## Soft depends (~)

- KERNEL / P03 stacks may reference cloud verify commands in docs only

## Non-goals

- Full `@cursor/sdk` relay / MCP dispatch (Phase 2)
- Ticket-boundary hook parsing on every file edit
- RESPOND-01 or KERNEL completion

## Acceptance criteria

- [x] `.cursor/environment.json` + `.cursor/Dockerfile` — Node 22, pnpm 10.3, uv 0.12.5 (pinned), Python 3.12 via `uv python install` (not apt); install `uv python install 3.12 && uv sync --all-packages --group dev && pnpm install --frozen-lockfile`
- [x] `docs/cloud-agents.md` — dashboard setup, verify commands, hooks, Phase 2 relay note
- [x] `docs/cloud-agents/conductor-contract.md` — single conductor mandate
- [x] `docs/cloud-agents/handoff-schema.json` — JSON handoff shape
- [x] `.cursor/hooks.json` — sessionStart, beforeShellExecution guards, stop verify reminder
- [x] `AGENTS.md` — cloud agents row in Testing table
- [ ] Oscar: create saved Cloud environment in Cursor dashboard (`enigma-assistant-`, repo `oscarhilton/enigma-assistant-`)

## Test plan

- `jq empty .cursor/environment.json .cursor/hooks.json docs/cloud-agents/handoff-schema.json`
- Hook scripts executable; `bash -n` on shell hooks
- `docker build -f .cursor/Dockerfile -t enigma-cloud-test .cursor` — Python 3.12 via uv (not apt)
- Manual: launch cloud agent against this branch; confirm install + smoke pytest

## Phase 2 (future ticket)

- `@cursor/sdk` relay with explicit base branch for stacked PRs
- MCP: dispatch, status, follow_up, request_review
- Optional `beforeReadFile` / write hooks for ticket glob enforcement
