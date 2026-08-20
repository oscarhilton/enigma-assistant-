# CLOUD-03 — Cursor relay create-contract correction

| Field | Value |
| --- | --- |
| Status | `in_progress` |
| Branch | `cursor/cloud-03-create-contract-47cd` |
| Domain | `platform` |

**Claimed.** Fix create-agent contract in `apps/cursor-relay/` only.

## Intent

Correct the Cursor Cloud Agents create payload and dry-run semantics so the Secure MCP Tunnel relay:

1. Sends `env.name` as the Cursor environment **name** (`enigma-assistant-`), never the UUID, after allowlist accept of either form.
2. For named cloud environments: **never** sends `repos`, **never** defaults `workOnCurrentBranch=true`; rely on Cursor-generated feature-branch semantics; do not claim the requested head as actual until `status` returns it.
3. Makes `job_brief.authorization.dry_run` genuinely non-mutating (validate + redacted request plan; no `POST /v1/agents`).
4. Surfaces only allowlisted, truncated Cursor validation fields (`code` / `message` / `field`) — never headers, raw requests, credentials, or arbitrary bodies.

## Hard depends

- [CLOUD-02](./CLOUD-02-cursor-relay-mcp.md) `done`

## Package boundary (hard)

May edit:

- `apps/cursor-relay/**`
- `docs/cloud-agents.md`, `docs/cloud-agents/**` (create-contract notes only)
- `tickets/platform/CLOUD-03*`

Must not edit:

- KERNEL-01 / ROUTE-01 / RESPOND-01 / BRIEF-01 code or tickets
- Product conversation / routing (`apps/api`, `apps/web` product paths)

## Acceptance criteria

- [x] Allowlisted UUID `1baeb513-9c77-11f1-ba66-0e7d0216e441` canonicalizes to `enigma-assistant-` in `env.name`
- [x] Named-env create payload omits `repos` and does not set `workOnCurrentBranch=true`
- [x] Dispatch handoff does not claim requested head as actual branch until status returns it
- [x] `dry_run=true` never calls `POST /v1/agents`; returns redacted request plan
- [x] HTTP 400 validation errors expose only truncated `code`/`message`/`field`
- [x] Contract tests cover exact request body, UUID→name, branch safety, dry-run, redacted 400s

## Test plan

```bash
uv run pytest apps/cursor-relay/tests -q
uv run ruff check apps/cursor-relay
```

## Non-goals

- Live KERNEL-01 dispatch
- Multi-user MCP OAuth
- Product behaviour changes
