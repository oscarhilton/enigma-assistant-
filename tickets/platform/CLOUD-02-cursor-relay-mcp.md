# CLOUD-02 — Cursor relay MCP

| Field | Value |
| --- | --- |
| Status | `todo` |
| Branch | `ticket/cloud-02-cursor-relay-mcp` |
| Domain | `platform` |

**Design only until claimed.** No relay implementation in the filing PR.

## Intent

Replace Oscar-as-village-telephone with a thin, authenticated MCP relay:

```
ChatGPT (existing authenticated session + caller identity)
  → authenticated MCP relay (allowlists, quotas, audit)
  → Cursor Cloud Agents API (@cursor/sdk)
  → named environment + ticket branch (+ optional stacked base)
  → conductor / worker evidence (structured handoff JSON by default)
```

ChatGPT continues using its own session. The relay alone holds `CURSOR_API_KEY` in a **server-side secret store outside the repo and outside Cloud Agent environments**. Cursor never receives ChatGPT credentials. **No agent automates ChatGPT or Cursor account login.**

## Hard depends

- [CLOUD-01](./CLOUD-01-cloud-agent-environment.md) `done` — reproducible environment, conductor contract, handoff schema
- **Operator prerequisite:** a saved **named** Cursor Cloud environment bound in the dashboard (`enigma-assistant-`, repo `oscarhilton/enigma-assistant-`) — **satisfied** 2026-08-20. Environment `1baeb513-9c77-11f1-ba66-0e7d0216e441`; recurring build `bld-20260820-e34aab5b-78af-452d-960b-480aa87b26e5` SUCCEEDED. Claim/implementation of CLOUD-02 may proceed.

## Soft depends (~)

- First manual conductor run transcript (topology + handoff shape) to calibrate dispatch payloads — **satisfied** by the CLOUD-01 pilot evidenced on [PR #129](https://github.com/oscarhilton/enigma-assistant-/pull/129) (schema-shaped conductor handoffs)
- KERNEL / ticket work can proceed via dashboard until the relay lands

## Package boundary (hard)

When claimed, may edit:

- New relay package / app path (exact location chosen at claim time; document in PR)
- `docs/cloud-agents.md`, `docs/cloud-agents/**` (trust chain, MCP surface, approval policy, allowlists)
- Tickets under `tickets/platform/CLOUD-02*`

Must not edit:

- Application conversation / routing code (`apps/api` turn kernel, semantic bootstrap, intent router)
- Agent environments’ secret injection of `CURSOR_API_KEY`
- Any design that stores or requests ChatGPT login credentials

## Non-goals

- Automating ChatGPT or Cursor browser login / human-verification loops
- Putting `CURSOR_API_KEY` in `.cursor/`, agent env secrets, or git
- Anonymous or unauthenticated MCP access (including `status`)
- Returning raw agent transcripts or secrets to ChatGPT by default
- Ticket-boundary file-edit hooks (optional later)
- Merging PRs from the relay without an explicit approval policy pass

## AuthN / AuthZ

- Every MCP call — **including `status`** — MUST carry an **authenticated caller identity** from the ChatGPT → relay hop (session / OAuth / equivalent — chosen at claim time). `status` may be authorised read-only; it must **never** be anonymous.
- **Forbid anonymous** invocation of every MCP tool (`dispatch`, `status`, `follow_up`, `request_review`, `cancel`).
- Approval policy gates who may `dispatch`, `request_review`, write-capable `follow_up`, and `cancel` (dry-run vs commit; no silent main merges).

## Allowlists & limits

`dispatch`, `request_review` (when it creates a run), and other write tools MUST enforce allowlists for:

| Dimension | Intent |
| --- | --- |
| Repository | Only permitted GitHub repos (e.g. `oscarhilton/enigma-assistant-`) |
| Named environment | Only saved Cursor Cloud environments bound to this product (operator bind prerequisite above) |
| Branch prefixes | e.g. `ticket/`, `cursor/`, `agent/` — never bare `main`/`master` as head without explicit policy |
| Models | Only approved model ids for cloud agents |

Also required:

- **Correlation / idempotency keys** on `dispatch` and on `request_review` when it creates a run (and on follow-ups that create work) so retries do not spawn duplicate agents
- **Concurrency and spend limits** applied to `dispatch` and `request_review` (and other create paths): max in-flight agents; budget / rate caps; hard deny when exceeded

## Responses & audit

- Default MCP responses: **structured conductor/worker handoffs** conforming to [handoff-schema.json](../../docs/cloud-agents/handoff-schema.json) — not raw transcripts, not secrets, not `CURSOR_API_KEY` material
- Audit log (relay-side, retained per ops policy): caller identity, agent id, run id, prompt hash, usage/spend counters, tool name, allowlist decision, correlation/idempotency key
- `CURSOR_API_KEY` remains **relay-side only** (never in repo, agent VM env, ChatGPT, or handoff payloads)

## MCP surface

| Tool | Role |
| --- | --- |
| `dispatch` | Launch a cloud agent against a named environment, repo, branch, and optional **explicit stacked base** |
| `status` | Poll run lifecycle / setup / PR linkage |
| `follow_up` | Resume the same agent id with a follow-up brief |
| `request_review` | Request structured review (e.g. Codex / security lane) without merging |
| `cancel` | Cancel an in-flight run (approval-gated) |

## Acceptance criteria

- [ ] Trust chain documented: ChatGPT → MCP relay → Cursor Cloud Agents API; authenticated caller identity on **every** MCP tool (including `status`); no ChatGPT credentials to Cursor; no agent-driven account login
- [ ] Anonymous MCP access is impossible by construction (including read-only `status`)
- [x] Operator named-environment dashboard bind confirmed (CLOUD-01 UI item); env `1baeb513-9c77-11f1-ba66-0e7d0216e441`; build `bld-20260820-e34aab5b-78af-452d-960b-480aa87b26e5` SUCCEEDED
- [ ] Allowlists: repository, named environment, branch prefixes, models
- [ ] Correlation / idempotency keys on `dispatch` and on `request_review` when it creates a run (and equivalent create paths)
- [ ] Concurrency and spend limits enforced for `dispatch` and `request_review` (and other create paths), with audited denials
- [ ] Default responses are schema-valid structured handoffs — not raw transcripts or secrets
- [ ] Audit records caller, agent id, run id, prompt hash, and usage
- [ ] `CURSOR_API_KEY` lives only in the relay’s server-side secret store
- [ ] Dispatch accepts: named Cursor environment, repository, head branch, optional stacked `base` branch, ticket path / job brief
- [ ] Approval policy for `dispatch`, `request_review`, write-capable follow-ups, and `cancel`
- [ ] Conductor jobs remain read-only unless the job brief explicitly authorizes push/PR/merge
- [ ] Smoke: dispatch a read-only conductor against an allowlisted branch and retrieve a schema-valid handoff

## Test plan

- Unit: MCP tool schema validation; approval-policy deny/allow matrix (including `dispatch` and `request_review`); allowlist / idempotency / quota denials
- Integration (relay staging): dispatch → status → cancel against a throwaway agent; no production secrets in agent env
- Contract: handoff JSON validates against `docs/cloud-agents/handoff-schema.json`
- Negative: anonymous invocation denied for **every** tool including `status`, `dispatch`, and `request_review`; ChatGPT credentials never accepted as relay config keys; transcripts/secrets absent from default responses

## Product order (cloud lane)

1. CLOUD-01 environment + conductor contract — `done` (manual pilot evidenced on PR #129)
2. **CLOUD-02 relay MCP** — this ticket
3. First production job through Oscar → relay → Cursor → evidence (prefer KERNEL completion slice once KERNEL-01 hard gates allow)
