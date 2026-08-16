# ADR-001: Polyglot Turborepo + uv

## Status

Accepted

## Context

Enigma needs TypeScript (web), Python (Core / worker), and Swift (Apple Bridge) in one repository so agents can own domains without splitting product context.

## Decision

- **pnpm + Turborepo** orchestrate JS/TS packages (`apps/web`, `packages/tsconfig`).
- **uv workspace** manages Python packages/apps under the same root.
- **SwiftPM** owns `apps/apple-bridge` (macOS-only).
- Root scripts expose `pnpm test|build|lint|typecheck` for TS and `uv run pytest|ruff|basedpyright` for Python.

## Consequences

- Single checkout for the product.
- CI has separate jobs for Python, web, and macOS Swift.
- Agents must respect package boundaries defined on tickets — Turborepo does not enforce Python boundaries.
