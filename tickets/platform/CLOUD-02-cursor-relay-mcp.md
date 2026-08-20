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
ChatGPT (existing authenticated session)
  → authenticated MCP relay
  → Cursor Cloud Agents API (@cursor/sdk)
  → named environment + ticket branch (+ optional stacked base)
  → conductor / worker evidence (handoff JSON, PR, tests)
```

ChatGPT continues using its own session. The relay alone holds `CURSOR_API_KEY` in a **server-side secret store outside the repo and outside Cloud Agent environments**. Cursor never receives ChatGPT credentials. **No agent automates ChatGPT or Cursor account login.**

## Hard depends

- [CLOUD-01](./CLOUD-01-cloud-agent-environment.md) `done` — reproducible environment, conductor contract, handoff schema

## Soft depends (~)

- First manual conductor run transcript (topology + handoff shape) to calibrate dispatch payloads
- KERNEL / ticket work can proceed via dashboard until the relay lands

## Package boundary (hard)

When claimed, may edit:

- New relay package / app path (exact location chosen at claim time; document in PR)
- `docs/cloud-agents.md`, `docs/cloud-agents/**` (trust chain, MCP surface, approval policy)
- Tickets under `tickets/platform/CLOUD-02*`

Must not edit:

- Application conversation / routing code (`apps/api` turn kernel, semantic bootstrap, intent router)
- Agent environments’ secret injection of `CURSOR_API_KEY`
- Any design that stores or requests ChatGPT login credentials

## Non-goals

- Automating ChatGPT or Cursor browser login / human-verification loops
- Putting `CURSOR_API_KEY` in `.cursor/`, agent env secrets, or git
- Ticket-boundary file-edit hooks (optional later)
- Merging PRs from the relay without an explicit approval policy pass

## MCP surface

| Tool | Role |
| --- | --- |
| `dispatch` | Launch a cloud agent against a named environment, repo, branch, and optional **explicit stacked base** |
| `status` | Poll run lifecycle / setup / PR linkage |
| `follow_up` | Resume the same agent id with a follow-up brief |
| `request_review` | Request structured review (e.g. Codex / security lane) without merging |
| `cancel` | Cancel an in-flight run (approval-gated) |

## Acceptance criteria

- [ ] Trust chain documented: ChatGPT → MCP relay → Cursor Cloud Agents API; no ChatGPT credentials to Cursor; no agent-driven account login
- [ ] `CURSOR_API_KEY` lives only in the relay’s server-side secret store (outside repo and agent VMs)
- [ ] Dispatch accepts: named Cursor environment, repository, head branch, optional stacked `base` branch, ticket path / job brief
- [ ] Approval policy for `dispatch` / write-capable follow-ups / `cancel` (who may invoke; dry-run vs commit; no silent main merges)
- [ ] Worker/conductor jobs emit structured handoff conforming to [handoff-schema.json](../../docs/cloud-agents/handoff-schema.json)
- [ ] Conductor jobs remain read-only unless the job brief explicitly authorizes push/PR/merge
- [ ] Smoke: dispatch a read-only conductor against `main` (or a ticket branch) and retrieve a schema-valid handoff

## Test plan

- Unit: MCP tool schema validation; approval-policy deny/allow matrix
- Integration (relay staging): dispatch → status → cancel against a throwaway agent; no production secrets in agent env
- Contract: handoff JSON validates against `docs/cloud-agents/handoff-schema.json`
- Negative: assert ChatGPT credentials are never accepted as relay config keys

## Product order (cloud lane)

1. CLOUD-01 environment + conductor contract — `done`
2. **CLOUD-02 relay MCP** — this ticket
3. First production job through Oscar → relay → Cursor → evidence (prefer KERNEL completion slice once KERNEL-01 hard gates allow)
