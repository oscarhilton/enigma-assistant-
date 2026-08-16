# personal-enigma

Private personal context assistant. Applications (Calendar, Reminders, Contacts, Notes, Email) are evidence sources. The centre of the product is an **obligation / attention** model that answers: *what actually matters?*

This repository is a **polyglot Turborepo** (TypeScript + Python + Swift) with work split into **domain ticket folders** so agents can branch in parallel without tangling.

## Quick start

```bash
# JS / web
pnpm install
pnpm test
pnpm build

# Python (Core, worker, packages)
uv sync --all-packages --group dev
uv run pytest
uv run ruff check .
uv run basedpyright

# Apple Bridge (macOS)
cd apps/apple-bridge && swift test
```

API health (after `uv sync`):

```bash
uv run enigma-api
# GET http://127.0.0.1:8000/health
```

Web:

```bash
pnpm --filter @personal-enigma/web dev
```

## Monorepo layout

```text
apps/api            FastAPI — Enigma Core
apps/worker         Ingestion / attention jobs
apps/web            Settings / privacy UI
apps/apple-bridge   Swift macOS companion (local only)
packages/domain     Canonical private models
packages/ingestion  DataSource protocol + per-source adapters
packages/identity   PERSON_* entity resolution (M10)
packages/dedupe     Calendar dedupe (M12)
packages/privacy    Privacy levels / invariants
packages/transformation
packages/attention
packages/embeddings
packages/fixtures
tickets/            Milestone tickets by domain
docs/architecture/  Durable architecture
docs/adr/           Architecture decisions
```

## Tickets (parallel work)

See [tickets/README.md](tickets/README.md) and [AGENTS.md](AGENTS.md).

Milestone map: [docs/architecture/milestone-map.md](docs/architecture/milestone-map.md).

## Architecture highlights

- Provider-agnostic ingestion (`SourceType` vs `Provider`)
- Apple Bridge via EventKit / Contacts / Notes automation — no undocumented DB scraping
- Local embeddings for private corpora; remote models see transformed passages only
- Calendar dedupe across Google∪Apple; cross-source obligation merging

## License

Private / unpublished unless otherwise stated.
