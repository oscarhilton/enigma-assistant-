# Tickets

Executable work units for **personal-enigma**, grouped by architecture domain so parallel agents can own one concern without tangling branches.

## Status legend

| Status | Meaning |
| --- | --- |
| `todo` | Unclaimed |
| `in_progress` | Claimed; branch open |
| `blocked` | Waiting on dependency or decision |
| `done` | Merged; acceptance criteria met |

## Claiming rules

1. **One agent → one ticket** (or one entire domain folder if tickets are tightly coupled and you state that in the PR).
2. Set the ticket `Status` to `in_progress` when you claim it.
3. Open branch: `ticket/Mxx-slug` (see each ticket’s Branch field).
4. Edit **only** paths listed under that ticket’s package boundary.
5. Do not implement sibling domains “while you are here.”
6. Every behavioural change needs tests.
7. When merging, set Status to `done` and reference the PR.

## Domains

| Domain | Folder | Typical packages |
| --- | --- | --- |
| domain-model | [domain-model/](./domain-model/) | `packages/domain` |
| fixtures | [fixtures/](./fixtures/) | `packages/fixtures` |
| transformation | [transformation/](./transformation/) | `packages/transformation` |
| privacy | [privacy/](./privacy/) | `packages/privacy`, `apps/web` (inspector) |
| reasoning | [reasoning/](./reasoning/) | future `packages/reasoning` |
| attention | [attention/](./attention/) | `packages/attention` |
| apple-bridge | [apple-bridge/](./apple-bridge/) | `apps/apple-bridge` |
| google | [google/](./google/) | ingestion google sources |
| retrieval | [retrieval/](./retrieval/) | `packages/embeddings` |
| obligations | [obligations/](./obligations/) | attention / obligations |
| api-surface | [api-surface/](./api-surface/) | `apps/api`, web |

Milestone order and links: [docs/architecture/milestone-map.md](../docs/architecture/milestone-map.md).

## Ticket template fields

Every ticket includes: Status, Branch, Domain, Package boundary, Depends on, Unlocks, Non-goals, Acceptance criteria, Test plan, Privacy constraints.
