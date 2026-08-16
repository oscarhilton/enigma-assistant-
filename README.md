# personal-enigma

Private personal context assistant. Applications (Calendar, Reminders, Contacts, Notes, Email) are evidence sources. The centre of the product is an **obligation / attention** model that answers: *what actually matters?*

This repository is a **polyglot Turborepo** (TypeScript + Python + Swift) with work split into **domain ticket folders** so agents can branch in parallel without tangling.

## Status

**MVP (M00a–M19) is complete** and merged to `main`: private persistence, settings, domain schemas, Apple Bridge (Calendar / Reminders / Contacts / Notes), Gmail & Google Calendar, transformation, privacy invariants, attention, obligations, local embeddings, privacy inspector, sanitised API, and optional ChatGPT reasoning.

**Phase 2 — Demo Mode** is next: run the real pipeline against fictional lives with known ground truth (starting with Alex Morgan / `scenarios/alex-v1/`). Spec: [docs/architecture/demo-mode.md](docs/architecture/demo-mode.md).

Governing rule: **select first → transform second → transmit last.** Remote inference is disable-able; Apple ingestion still works.

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
apps/web            Settings / privacy / chat UI
apps/apple-bridge   Swift macOS companion (local only)
packages/domain     Canonical private models
packages/ingestion  DataSource protocol + per-source adapters
packages/identity   PERSON_* entity resolution
packages/dedupe     Calendar dedupe
packages/privacy    Privacy levels / invariants
packages/transformation
packages/attention
packages/obligations
packages/embeddings
packages/reasoning
packages/fixtures
packages/simulation Phase 2 demo environment (scaffold)
packages/evaluation Phase 2 eval harness (scaffold)
scenarios/          Immutable demo personas (alex-v1, …)
tickets/            Milestone tickets by domain (MVP + demo-*)
docs/architecture/  Durable architecture
docs/adr/           Architecture decisions
```

## Tickets

MVP tickets live under `tickets/<domain>/` (all `done`). Phase 2 work lands under `tickets/demo-*`.

See [tickets/README.md](tickets/README.md) and [AGENTS.md](AGENTS.md).

Milestone map: [docs/architecture/milestone-map.md](docs/architecture/milestone-map.md).

## Architecture highlights

- Provider-agnostic ingestion (`SourceType` vs `Provider`)
- Apple Bridge via EventKit / Contacts / Notes automation — no undocumented DB scraping
- Local embeddings for private corpora; remote models see transformed passages only
- Calendar dedupe across Google∪Apple; cross-source obligation merging
- Demo and Private modes must never share DB, vectors, credentials, or PERSON_* keys

## License

Private / unpublished unless otherwise stated.
