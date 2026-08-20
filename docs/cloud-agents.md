# Cloud agents (Cursor Pro)

Cloud-first automation for Enigma ticket work. One agent, one ticket, one branch/PR — orchestrated by a **release conductor** when jobs span branches or PR stacks.

## Why cloud-first

- Agents run on Cursor VMs with repo clones — no Mac daemon required.
- Work continues after your laptop disconnects.
- Same `@cursor/sdk` surface can route a job to local later if needed (Phase 2 — see [CLOUD-01](../tickets/platform/CLOUD-01-cloud-agent-environment.md)).

**Caveats:** usage is metered at model API rates; set a spend cap before scaling. Apple Bridge / real Private storage cannot run in the Linux VM — use mocks here, verify Swift locally.

## Cursor dashboard — saved environment

Create **one** saved Cloud Agent environment in [Cursor → Cloud Agents](https://cursor.com/agents) (Settings → Cloud):

| Setting | Recommendation |
| --- | --- |
| **Environment name** | `enigma-assistant-` (suffix distinguishes prod vs experiments) |
| **Repository** | `oscarhilton/enigma-assistant-` (default; confirm org/repo spelling in GitHub) |
| **Base branch** | Leave **blank** for ordinary ticket work off `main`. For **stacked PRs** (e.g. KERNEL on top of P03), the relay or job brief must pass an explicit base branch (example: `ticket/p03-forensic-calendar-gravity`). |
| **Branch prefix** | `cursor/` or `agent/` — keeps agent branches distinct from human `ticket/*` branches |
| **Auto PR creation** | **Off** initially — conductor/worker opens PRs deliberately with test plans |
| **Network** | Start with Cursor defaults; allowlist only what install/verify needs (PyPI, npm registry, GitHub). Deny broad egress unless a ticket requires it. Document exceptions in the job brief. |
| **Secrets** | **No production secrets** — no real HMAC keys, connector tokens, or Private/Demo DB URLs. Use mocks and workspace-local temp dirs ([ADR-005](../docs/adr/005-demo-private-storage-roots.md)). |

Config-as-code in the repo (preferred source of truth for install/build):

| File | Purpose |
| --- | --- |
| `.cursor/environment.json` | Cloud VM build + install command |
| `.cursor/Dockerfile` | Node 22, pnpm 10.3, uv, Python 3.12 |
| `.cursor/hooks.json` | Session context, shell guards, stop verify reminder |

**Install** (mirrors CI):

```bash
uv sync --all-packages --group dev && pnpm install --frozen-lockfile
```

**Verify — cloud lane** (run before claiming done; scope to ticket when possible):

```bash
uv run pytest
uv run ruff check .
uv run basedpyright
pnpm --dir apps/web test
pnpm --dir apps/web lint
pnpm --dir apps/web typecheck
```

Focused smoke (fast):

```bash
uv run pytest apps/api/tests/test_turn_kernel.py
pnpm --dir apps/web test
uv run ruff check .
```

**Verify — local-only** (macOS): run Apple Bridge tests from `apps/apple-bridge` (see [AGENTS.md](../AGENTS.md) Testing table).

## Release conductor (one agent, not a worker swarm)

For merge/release decisions, branch topology, or stacked PRs, dispatch **one conductor** whose mandate is defined in [conductor-contract.md](./cloud-agents/conductor-contract.md). The conductor emits machine-shaped JSON per [handoff-schema.json](./cloud-agents/handoff-schema.json).

Workers implement tickets; conductors read evidence and recommend branch/commit/PR actions **without** pushing or opening PRs unless the job explicitly authorizes it.

## Hooks (`.cursor/hooks.json`)

| Hook | Script | Behaviour |
| --- | --- | --- |
| `sessionStart` | `cloud-session-context.sh` | Injects cloud lane + conductor pointers |
| `beforeShellExecution` | `guard-cloud-shell.sh` | Deny real storage roots and connector secrets; deny default-branch pushes and force-push; deny macOS Swift test invocations in cloud |
| `stop` | `cloud-verify-reminder.sh` | Reminds agent to run canonical verify + JSON handoff for conductor jobs |

**Future (not implemented):** ticket package-boundary parsing on file edits — document globs in tickets/ and enforce via review until a dedicated hook exists.

## Manual pilot (do this first)

Before building `@cursor/sdk` relay (Phase 2):

1. Pick a **todo** ticket with narrow package globs ([tickets/README.md](../tickets/README.md)).
2. Launch one Cloud Agent from the dashboard against branch `ticket/<prefix>-<slug>`.
3. Paste the ticket path as the task brief; require PR + test plan, no merge.
4. Note auth gaps, build time, and hook behaviour — then automate.

Suggested first pilots: small test/doc tickets, or follow-on API work with globs confined to `apps/api/**`.

## Planned relay (Phase 2)

```
Oscar task contract
  → @cursor/sdk (cloud mode)
  → isolated VM + ticket branch (+ optional stacked base branch)
  → implement + test
  → PR / structured handoff
  → Codex review
  → follow-up via Agent.resume(same id)
  → only decisions reach Oscar
```

MCP surface (later): `dispatch`, `status`, `follow_up`, `request_review`.

Ticket markdown files remain the source of truth for scope; branches/PRs are durable handoffs.

## Privacy invariants (cloud)

- Never point database URLs at real Private/Demo/Shadow roots ([ADR-005](../docs/adr/005-demo-private-storage-roots.md), [ADR-008](../docs/adr/008-shadow-storage-roots.md)).
- Never load HMAC or connector tokens in cloud shells.
- Hooks in `.cursor/hooks/guard-cloud-shell.sh` enforce the above at shell execution time.
