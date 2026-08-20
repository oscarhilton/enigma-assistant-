# Cursor relay MCP (CLOUD-02)

Authenticated MCP relay:

```
ChatGPT (caller identity via bearer token)
  → apps/cursor-relay (allowlists, quotas, approval, audit)
  → Cursor Cloud Agents API (HTTP; same surface as @cursor/sdk)
```

## Layout

| Path | Role |
| --- | --- |
| `apps/cursor-relay/` | Relay package (this app) |
| `docs/cloud-agents/relay.md` | Trust chain, auth, allowlists, runbook |
| `docs/cloud-agents/handoff-schema.json` | Default response schema |

## Security invariants

- `CURSOR_API_KEY` only in relay process env / secret store — never git, `.cursor/`, agent VM secrets, handoffs, or test fixtures as real keys.
- Every MCP tool including `status` requires `authorization: Bearer …`.
- Tests use `MockCursorClient` only.

## Local verify

```bash
uv sync --all-packages --group dev
uv run pytest apps/cursor-relay/tests -q
uv run ruff check apps/cursor-relay
```

## Staging smoke (mock)

```bash
export RELAY_AUTH_TOKENS='{"dev-token":{"caller_id":"local-dev","roles":["admin"]}}'
# Do NOT set CURSOR_API_KEY for mock-mode unit smoke; inject MockCursorClient in tests.
uv run pytest apps/cursor-relay/tests/test_smoke.py -q
```

## Production

Set at deploy time (server-side only):

- `CURSOR_API_KEY`
- `RELAY_AUTH_TOKENS` (JSON map of bearer token → `{caller_id, roles}`)
- Optional: `RELAY_ALLOWED_REPOS`, `RELAY_ALLOWED_ENVIRONMENTS`, `RELAY_MAX_IN_FLIGHT`, `RELAY_MAX_SPEND_UNITS`, `RELAY_AUDIT_PATH`

Run MCP stdio:

```bash
uv run enigma-cursor-relay
```
