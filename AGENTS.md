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
- Stay inside the ticket’s **package boundary** (exact file globs in each ticket).
- Respect **hard** vs **soft (~)** dependencies — soft deps must not block start ([tickets/README.md](tickets/README.md)).
- Ingestion ownership is pinned: one `sources/*.py` file per source ticket; M10 owns `packages/identity`, not `packages/domain`.
- Safe parallel examples: `apple-bridge/M08` ∥ `M09` ∥ `M10` after M07; `google/M11` ∥ Apple sources after M04.
- Unsafe: two agents editing `packages/domain`, the same `sources/*.py`, or the same Swift module.

## Testing

| Stack | Command |
| --- | --- |
| Python | `uv run pytest` · `uv run ruff check .` · `uv run basedpyright` |
| Web | `pnpm test` · `pnpm lint` · `pnpm typecheck` · `pnpm build` |
| Apple Bridge | `cd apps/apple-bridge && swift test` (macOS) |

Behavioural changes without tests are not done.

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
| Local embeddings | `packages/embeddings` |
| Fixtures | `packages/fixtures` |
| Core HTTP | `apps/api` |
| Jobs | `apps/worker` |
| UI | `apps/web` |
| macOS bridge | `apps/apple-bridge` |

Provider-specific types stop at the ingestion boundary. Core reasons about domain concepts, not `EKEvent` or Google payload shapes.

## Documentation expectations

- Update the ticket checklist when acceptance criteria land.
- If you make an architectural choice, add or amend an ADR.
- Keep README / architecture docs accurate when layout changes.
