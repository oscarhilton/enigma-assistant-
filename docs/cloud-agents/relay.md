# Cursor relay MCP (CLOUD-02)

## Trust chain

```
ChatGPT (existing authenticated session + caller identity)
  → authenticated MCP relay (apps/cursor-relay)
       • AuthN: Bearer token on every tool (including status)
       • AuthZ: roles + approval policy
       • Allowlists: repository, named environment, branch prefixes, models
       • Idempotency + concurrency/spend limits
       • Audit: caller, agent id, run id, prompt hash, usage
  → Cursor Cloud Agents API (HTTP; equivalent to @cursor/sdk cloud surface)
  → named environment + ticket/cursor/agent branch
  → structured handoff JSON (handoff-schema.json) — not raw transcripts
```

**Invariants**

- Cursor never receives ChatGPT credentials.
- ChatGPT credentials must not be used as `CURSOR_API_KEY`.
- No agent automates ChatGPT or Cursor account login.
- `CURSOR_API_KEY` lives only in the relay’s server-side secret store / process env at deploy time — never in git, `.cursor/`, Cloud Agent env secrets, handoffs, or test fixtures as real keys.
- Default MCP responses are schema-valid structured handoffs — never raw transcripts or secrets.

## Named environment (defaults)

| Field | Value |
| --- | --- |
| Environment id | `1baeb513-9c77-11f1-ba66-0e7d0216e441` |
| Display name | `enigma-assistant-` |
| Repository | `oscarhilton/enigma-assistant-` |

## MCP tools

| Tool | AuthZ | Notes |
| --- | --- | --- |
| `dispatch` | `dispatcher`+ | Requires `idempotency_key`; create-path quotas |
| `status` | `reader`+ | Authenticated; read-only authorization |
| `follow_up` | `dispatcher`+ | Write-capable; requires `idempotency_key` |
| `request_review` | `approver`+ | No merge; idempotency when creating a run |
| `cancel` | `approver`+ | Approval-gated |

Every tool argument object includes `authorization` (Bearer token). Anonymous invocation is denied by construction.

## Approval policy

- Roles: `reader`, `dispatcher`, `approver`, `admin`.
- `merge` / `allow_merge` is always denied by the relay (no silent main merges).
- `auto_create_pr` requires `job_brief.authorization.allow_open_pr=true`.
- Conductor jobs remain read-only unless the job brief explicitly authorizes push/PR (merge still forbidden via relay).

## Allowlists & limits

Configured via env (defaults match the named environment above):

- `RELAY_ALLOWED_REPOS`
- `RELAY_ALLOWED_ENVIRONMENTS`
- `RELAY_ALLOWED_BRANCH_PREFIXES` (default `ticket/,cursor/,agent/`)
- `RELAY_ALLOWED_MODELS`
- `RELAY_MAX_IN_FLIGHT` / `RELAY_MAX_SPEND_UNITS`

Head branches `main` / `master` are forbidden. Denials are audited.

## Local / staging runbook (verify independently)

1. Sync deps: `uv sync --all-packages --group dev`
2. Unit + contract (mock Cursor API — **no** live key):

   ```bash
   uv run pytest apps/cursor-relay/tests -q
   uv run ruff check apps/cursor-relay
   ```

3. Confirm handoff schema contract tests pass (`test_handoff_schema.py`).
4. Optional stdio MCP probe against mock (tests cover `tools/list` + `tools/call`).
5. Only after green: consider production deploy with `CURSOR_API_KEY` in the relay secret store.

**Do not** inject `CURSOR_API_KEY` into Cloud Agent environments. **Do not** dispatch KERNEL-01 through the relay until this verify is green and a later job brief authorizes it.

## Package boundary

Implementation lives in `apps/cursor-relay/**`. Product conversation/routing code under `apps/api` is out of scope for CLOUD-02.
