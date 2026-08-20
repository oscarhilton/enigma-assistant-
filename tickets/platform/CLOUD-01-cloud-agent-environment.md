# CLOUD-01 — Cloud agent environment + conductor

| Field | Value |
| --- | --- |
| Status | `done` |
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

- [x] `.cursor/environment.json` + `.cursor/Dockerfile` — Node 22, pnpm 10.3, uv **0.12.5** (pinned), Python 3.12 via `uv python install` (not apt); install prefixed with `uv python install 3.12` then sync + pnpm frozen lockfile
- [x] `docs/cloud-agents.md` — dashboard setup, verify commands, hooks as defence-in-depth, Phase 2 relay note
- [x] `docs/cloud-agents/conductor-contract.md` — single conductor mandate
- [x] `docs/cloud-agents/handoff-schema.json` — JSON handoff shape
- [x] `.cursor/hooks.json` — sessionStart, beforeShellExecution guards (`failClosed: false`), stop verify reminder
- [x] `AGENTS.md` — cloud agents row in Testing table
- [x] Local Docker build + version smoke (`enigma-cloud-test`) — see evidence below
- [x] Manual Cloud Agent pilot (read-only conductor + schema-shaped handoff) — evidenced on [PR #129](https://github.com/oscarhilton/enigma-assistant-/pull/129); CLOUD-02 soft prerequisite satisfied
- [ ] Oscar: create/bind saved Cloud environment in Cursor dashboard (`enigma-assistant-`, repo `oscarhilton/enigma-assistant-`) — **UI-only**; repo config committed and build-validated; dashboard create still required once if not already bound

## Docker fix evidence (merge-blocking)

- **Fault:** Bookworm apt has Python 3.11; prior Dockerfile wrongly apt-installed python3.12.
- **Fix:** Node 22 base; apt installs git/sudo/curl/ca-certificates/jq only; multi-stage FROM uv pin 0.12.5; `UV_PYTHON_INSTALL_DIR=/opt/uv-python` + `uv python install 3.12`; `UV_PYTHON=3.12`; `COREPACK_HOME=/opt/corepack` + pnpm 10.3.0 via corepack; chown toolchain dirs to `ubuntu`.
- **Local build:** `docker build -f .cursor/Dockerfile -t enigma-cloud-test .` — success
- **Version smoke (USER ubuntu):** Python 3.12.14; node v22.23.2; pnpm 10.3.0; uv 0.12.5; `UV_PYTHON=3.12`
- **In-image install smoke:** `uv sync --all-packages --group dev` + `pnpm install --frozen-lockfile` as `ubuntu`; `uv run pytest apps/api/tests/test_health.py` (1 passed); focused web vitest `readApiJson.test.ts` (3 passed)

## Hook probe results (synthetic stdin)

| Probe | Expect | Result |
| --- | --- | --- |
| ordinary (`uv run pytest`) | allow | PASS |
| direct default-branch push | deny | PASS |
| force push | deny | PASS |
| storage path (home Enigma dir) | deny | PASS |
| secret-name reference (HMAC env var) | deny | PASS |
| Swift lane | deny | PASS |
| `sessionStart` JSON | valid | PASS |
| `stop` reminder JSON | valid | PASS |

`failClosed` left **false** for pilot (documented in `docs/cloud-agents.md`).

## Canonical verify (host)

| Command | Result |
| --- | --- |
| `uv run pytest` | 846 passed, 2 skipped |
| `uv run ruff check .` | All checks passed |
| `pnpm --dir apps/web test` | 58 files / 204 tests passed |

## Test plan

- [x] `jq empty .cursor/environment.json .cursor/hooks.json docs/cloud-agents/handoff-schema.json`
- [x] Hook scripts executable; `bash -n` on shell hooks
- [x] Hook synthetic probes (table above)
- [x] Local Docker build + version smoke
- [x] Manual Cloud Agent pilot — read-only conductor against current `main` / filing branch; schema-shaped handoff emitted per [handoff-schema.json](../../docs/cloud-agents/handoff-schema.json). Evidence: [PR #129](https://github.com/oscarhilton/enigma-assistant-/pull/129) (CLOUD-02 / ROUTE-01 filing + conductor handoffs on that run). CLOUD-02’s soft prerequisite “first manual conductor run transcript” is **satisfied**.

## Phase 2

See [CLOUD-02 — Cursor relay MCP](./CLOUD-02-cursor-relay-mcp.md): authenticated MCP relay (`dispatch`, `status`, `follow_up`, `request_review`, `cancel`); `CURSOR_API_KEY` server-side only; no ChatGPT credentials to Cursor; no agent-driven account login.
