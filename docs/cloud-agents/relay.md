# Cursor relay MCP (CLOUD-02)

## Trust chain

```
ChatGPT (Secure MCP Tunnel — single-user pilot)
  → authenticated MCP relay (apps/cursor-relay)
       • AuthN: fixed caller from RELAY_TUNNEL_CALLER on the relay host
         (injected internally; never in MCP tool schemas or model args)
       • AuthZ: roles + approval policy
       • Allowlists: repository, named environment, head/base branches, models
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
- `CURSOR_API_KEY` lives only in the relay’s server-side secret store / process env at deploy time — never in git, `.cursor/`, Cloud Agent env secrets, handoffs, responses, logs, exception text, or test fixtures as real keys.
- **No bearer token, API key, or credential may appear in public MCP tool input schemas or model-supplied arguments.** Identity is derived server-side and injected into `RelayService`.
- Default MCP responses are schema-valid structured handoffs — never raw transcripts or secrets. Cursor timeouts/HTTP/transport failures are mapped to failure handoffs (no raw httpx exceptions to ChatGPT).
- The relay **cannot merge PRs** and **does not** implicitly dispatch KERNEL-01 (or any ticket) — callers must pass an explicit job brief; KERNEL remains a separate authorized dispatch.

## Secure MCP Tunnel pilot (single-user)

This pilot assumes a **trusted transport** (Secure MCP Tunnel) to a single relay host:

| Concern | Behaviour |
| --- | --- |
| Caller identity | Fixed via `RELAY_TUNNEL_CALLER` JSON `{caller_id, roles, display_name?}` on the relay host |
| MCP tool schemas | No `authorization` / bearer / credential properties |
| Model args | Credential-like top-level keys are **rejected** (`model_supplied_secret`) |
| Missing tunnel caller | Anonymous denial at the transport boundary (every tool, including `status`) |
| Roles / approval / audit | Unchanged — roles come from the tunnel caller record |

**Multi-user or public deployment requires MCP OAuth** (or an equivalent non-model-visible credential channel). Do not reintroduce bearer tokens into tool schemas for multi-tenant use.

`RELAY_AUTH_TOKENS` (legacy bearer map) is **retired** for this pilot; config load fails closed if it is set without migrating to `RELAY_TUNNEL_CALLER`.

## Create-agent contract (CLOUD-03)

| Rule | Behaviour |
| --- | --- |
| `env.name` | Allowlisted UUID `1baeb513-9c77-11f1-ba66-0e7d0216e441` is canonicalized to `enigma-assistant-` before serialization |
| Named cloud env | Never send `repos`; never set `workOnCurrentBranch=true` (omit field — Cursor-generated feature branch) |
| Branch claim | Dispatch/review create reports `branch=pending` + `requested_head_branch`; `actual_head_branch` only from `status` |
| `dry_run` | `job_brief.authorization.dry_run=true` validates and returns a redacted request plan — **no** `POST /v1/agents` |
| HTTP 400 | Only truncated `code` / `message` / `field` validation entries — never headers, credentials, or raw bodies |

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
| `status` | `reader`+ | Server-side authenticated; read-only authz |
| `result` | `reader`+ | Terminal report-back (final result, duration, branches, PRs); stream → GET fallback |
| `follow_up` | `dispatcher`+ | Write-capable; requires `idempotency_key` |
| `request_review` | `approver`+ | No merge; idempotency when creating a run |
| `cancel` | `approver`+ | Approval-gated |

Anonymous invocation (no tunnel caller / no injected caller) is denied by construction.

## Approval policy

- Roles: `reader`, `dispatcher`, `approver`, `admin`.
- `merge` / `allow_merge` is always denied by the relay (no silent main merges).
- `auto_create_pr` requires `job_brief.authorization.allow_open_pr=true` (policy flags inside `job_brief` — not transport credentials).
- Conductor jobs remain read-only unless the job brief explicitly authorizes push/PR (merge still forbidden via relay).

## Allowlists & limits

Configured via env (defaults match the named environment above):

- `RELAY_ALLOWED_REPOS`
- `RELAY_ALLOWED_ENVIRONMENTS`
- `RELAY_ALLOWED_BRANCH_PREFIXES` (default `ticket/,cursor/,agent/`)
- `RELAY_ALLOWED_BASE_BRANCHES` (default `main,master`; stacked bases may also use an allowed prefix)
- `RELAY_ALLOWED_MODELS`
- `RELAY_MAX_IN_FLIGHT` / `RELAY_MAX_SPEND_UNITS`

Head branches `main` / `master` are forbidden as **heads**. Base branches fail closed (exact allowlist or allowed prefix). Denials are audited.

## Single-instance pilot (in-memory stores)

Idempotency and concurrency/spend trackers are **in-memory and process-local** by default. That is intentional for a **single-instance pilot**.

| Mode | Config | Behaviour |
| --- | --- | --- |
| Default | `RELAY_SINGLE_INSTANCE=1` (default) | One relay process; in-memory stores are coherent |
| Multi-replica | `RELAY_SINGLE_INSTANCE=0` **and** `RELAY_SHARED_STORE_URL=…` | Required together — config load **fails closed** if multi without a shared store URL |

Two relay instances each with their own memory can both accept the same idempotency key — do not run that way without a shared store. The URL is a future durable backend hook; until a shared adapter is implemented, keep a single replica.

## Agent report-back (CLOUD-04)

Finished cloud-agent runs expose their terminal assistant reply via the read-only MCP tool **`result`** — no extra `request_review` run required.

| Step | Behaviour |
| --- | --- |
| Cache | Process-local `ResultStore` keyed by `agent_id:run_id` |
| Terminal check | `GET /v1/agents/{agentId}/runs/{runId}` |
| Stream | `GET /v1/agents/{agentId}/runs/{runId}/stream` for terminal runs (SSE `result` / `error` events) |
| Fallback | On `410 stream_expired`, use Get Run payload (`result`, `durationMs`, `git`) |
| Non-terminal | Returns `terminal=false` without streaming in-progress runs |

Handoff fields: `run_status`, `final_result`, `duration_ms`, `git_branches`, `pr_urls`, `agent_id`, `run_id`, `ticket_ids`, `result_source`. Secret scrubbing applies to `final_result`. This is the agent's terminal summary — not a raw transcript dump.

## Local / staging runbook (verify independently)

1. Sync deps: `uv sync --all-packages --group dev`
2. Unit + contract (mock Cursor API — **no** live key):

   ```bash
   uv run pytest apps/cursor-relay/tests -q
   uv run ruff check apps/cursor-relay
   ```

3. Confirm handoff schema contract tests pass (`test_handoff_schema.py`).
4. Confirm MCP surface never exposes/accepts secrets (`test_no_secrets_in_mcp_surface.py`).
5. Only after green: production deploy with `CURSOR_API_KEY` and `RELAY_TUNNEL_CALLER` on the **relay host only** — never in Cursor worker environments.

**Do not** inject `CURSOR_API_KEY` into Cloud Agent environments. **Do not** dispatch KERNEL-01 through the relay until this verify is green and a later job brief authorizes it.

## Package boundary

Implementation lives in `apps/cursor-relay/**`. Product conversation/routing code under `apps/api` is out of scope for CLOUD-02.
