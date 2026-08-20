# AGENTS.md — personal-enigma

Operating manual for humans and coding agents working in this monorepo.

## Product rule

> Apple services enrich Enigma’s private model of the user’s world; they do not enlarge the remote model’s view of it.

**Select first → transform second → transmit last.**

## Before you write code

1. Read [docs/architecture/overview.md](docs/architecture/overview.md).
2. Read ADRs under [docs/adr/](docs/adr/).
3. Claim a ticket under [tickets/](tickets/) per [tickets/README.md](tickets/README.md).

## Parallelism

- Prefer **one ticket per agent / branch**.
- **Isolated worktrees:** claim `ticket/<prefix>-<slug>` and `git worktree add ../enigma-wt-<ticket> -b ticket/<prefix>-<slug>`. One ticket per worktree. Uncommitted work stays in the primary checkout — do not split dirty files. Full convention: [tickets/README.md](tickets/README.md#isolated-worktrees-parallel-agents).
- Stay inside the ticket’s **package boundary** (exact file globs in each ticket).
- Respect **hard** vs **soft (~)** dependencies — soft deps must not block start ([tickets/README.md](tickets/README.md)).
- Ingestion ownership is pinned: one `sources/*.py` file per source ticket; M10 owns `packages/identity`, not `packages/domain`.
- Synthetic Demo sources are pinned under `packages/simulation/.../sources/` (D4); do not edit real `packages/ingestion/.../sources/*` from Demo tickets.
- Safe parallel examples: `apple-bridge/M08` ∥ `M09` ∥ `M10` after M07; Phase 2 `D2` ∥ `D3` after D1; D4 source files in parallel after D1.
- Unsafe: two agents editing `packages/domain`, the same `sources/*.py`, or the same Swift module.
- Demo Mode never shares Private storage roots or HMAC keys ([ADR-005](docs/adr/005-demo-private-storage-roots.md)). Worktrees must not share Private/Demo/Shadow storage roots either.

## Testing

| Stack | Command |
| --- | --- |
| Python | `uv run pytest` · `uv run ruff check .` · `uv run basedpyright` |
| Web | `pnpm test` · `pnpm lint` · `pnpm typecheck` · `pnpm build` |
| Apple Bridge | `cd apps/apple-bridge && swift test` (macOS) |
| Cloud agents | See [docs/cloud-agents.md](docs/cloud-agents.md) — Linux VM; mocks only, no real Private storage |

Behavioural changes without tests are not done.


## Merging PRs

- **Merge gate:** CI green + agent self code-review before merge; do not block on Copilot when credits unavailable.

## Privacy

- Never send `PrivatePerson`, wholesale Notes, or raw attendee emails to a hosted model.
- Notes default **HIGH**; no SQLite scraping ([ADR-004](docs/adr/004-notes-best-effort-no-sqlite.md)).
- Bridge is localhost / Unix socket only ([ADR-002](docs/adr/002-bridge-local-transport-auth.md)).
- Remote inference must be disable-able; Apple ingestion must still work.

## Modular boundaries

| Concern | Home |
| --- | --- |
| Canonical models | `packages/domain` |
| `DataSource` protocol + adapters | `packages/ingestion` (+ pinned `sources/*.py`) |
| Entity resolution / PERSON_* | `packages/identity` |
| Calendar dedupe | `packages/dedupe` |
| Privacy levels / invariants | `packages/privacy` |
| Transformer | `packages/transformation` |
| Attention | `packages/attention` |
| NextAction schemas | `packages/domain` ([next-action.md](docs/architecture/next-action.md), ADR-010) |
| Local embeddings | `packages/embeddings` |
| Fixtures | `packages/fixtures` |
| Demo simulation / clock / env | `packages/simulation` |
| Demo evaluation | `packages/evaluation` |
| Scenario packages | `scenarios/` |
| Core HTTP | `apps/api` |
| Jobs | `apps/worker` |
| UI | `apps/web` |
| macOS bridge | `apps/apple-bridge` |

Provider-specific types stop at the ingestion boundary. Core reasons about domain concepts, not `EKEvent` or Google payload shapes.

## Documentation expectations

- Update the ticket checklist when acceptance criteria land.
- If you make an architectural choice, add or amend an ADR.
- Keep README / architecture docs accurate when layout changes.
