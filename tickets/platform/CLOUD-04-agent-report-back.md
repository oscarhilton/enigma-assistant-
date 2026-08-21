# CLOUD-04 — Agent report-back

| Field | Value |
| --- | --- |
| Status | `in_progress` |
| Branch | `cursor/cloud-04-agent-report-back-1a4e` |
| Domain | `platform` |

## Intent

Improve the Cursor relay so finished Cloud Agent runs can return their **actual terminal result** to ChatGPT without spawning extra review runs (`request_review`).

ChatGPT calls a read-only MCP tool (`result`) with a known `agent_id` + `run_id` and receives a schema-valid handoff containing:

- run status (terminal lifecycle)
- final result text (agent terminal reply — not a raw transcript dump)
- `durationMs`
- git branch(es) and PR URL(s) when present
- `agent_id`, `run_id`, `ticket_ids`

Resolution order:

1. In-memory terminal cache (process-local; same single-instance constraint as idempotency/quota stores)
2. Cursor v1 **Stream Run** (`GET /v1/agents/{agentId}/runs/{runId}/stream`) when the run is terminal
3. **Get Run** fallback (`GET /v1/agents/{agentId}/runs/{runId}`) when SSE retention expired (`410 stream_expired`)

No webhooks, background push, polling loops, or conductor/kernel changes.

## Hard depends

- [CLOUD-02](./CLOUD-02-cursor-relay-mcp.md) `done`
- [CLOUD-03](./CLOUD-03-cursor-relay-create-contract.md) `in_progress` (create-contract; orthogonal read path)

## Package boundary (hard)

May edit:

- `apps/cursor-relay/**`
- `docs/cloud-agents.md`, `docs/cloud-agents/**` (report-back / `result` tool notes only)
- `tickets/platform/CLOUD-04*`

Must not edit:

- KERNEL-01 / ROUTE-01 / RESPOND-01 / BRIEF-01 code or tickets (documentation cross-links only if strictly necessary)
- Product conversation / routing (`apps/api`, `apps/web` product paths)

## MCP contract — `result`

| Field | Required | Notes |
| --- | --- | --- |
| `agent_id` | yes | Cursor cloud agent id (`bc-…`) |
| `run_id` | yes | Run id for the dispatch/follow-up |
| `ticket_ids` | no | Echoed in handoff; defaults from ticket path convention |
| `head_branch` | no | Requested head for correlation only |

**AuthZ:** `reader`+ (same as `status`). Anonymous denial unchanged.

**Response (`observed_state` extensions):**

| Field | When |
| --- | --- |
| `terminal` | `true` when run reached `FINISHED` / `ERROR` / `CANCELLED` / `EXPIRED` |
| `run_status` | Cursor run status |
| `final_result` | Terminal assistant reply text (secret-scrubbed) |
| `duration_ms` | Wall-clock ms for terminal runs |
| `git_branches` | Branch names from `Run.git` |
| `pr_urls` | PR URLs when present |
| `result_source` | `cache` \| `stream` \| `get_run` |
| `stream_error` | `{code, message}` when terminal `ERROR` and stream/GET expose it |
| `agent_id`, `run_id`, `ticket_ids` | Always when authenticated allow |

Non-terminal runs return `terminal=false` with `final_result=null` — callers should retry later or use `status` for lifecycle polling.

## Acceptance criteria

- [x] Read-only MCP tool `result` registered (schema + dispatch + role matrix)
- [x] Terminal runs expose `final_result`, `duration_ms`, branches, PR URLs, ids, ticket_ids
- [x] Stream Run attempted for terminal runs; Get Run fallback on `stream_expired`
- [x] Terminal snapshots cached in-memory keyed by `agent_id:run_id`
- [x] Secret redaction preserved on result text and all handoff fields
- [x] Anonymous / role auth boundaries unchanged (`reader`+ for `result`)
- [x] No webhooks, background push, polling loops, or KERNEL/conductor code changes
- [x] Comprehensive unit tests: stream parse, GET fallback, cache, non-terminal, ERROR, outage, MCP surface
- [x] Docs updated in `docs/cloud-agents/relay.md`

## Test plan

```bash
uv run pytest apps/cursor-relay/tests -q
uv run ruff check apps/cursor-relay
```

## Non-goals

- Raw transcript export (only terminal reply text)
- Durable cross-replica result store (future shared-store hook only)
- Replacing `status` lifecycle polling
- Spawning `request_review` for report-back
- PR open/merge automation
