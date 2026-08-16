# Tickets

Executable work units for **personal-enigma**, grouped by architecture domain so parallel agents can own one concern without tangling branches.

## Status legend

| Status | Meaning |
| --- | --- |
| `todo` | Unclaimed |
| `in_progress` | Claimed; branch open |
| `blocked` | Waiting on dependency or decision |
| `done` | Merged; acceptance criteria met |

## Dependency legend

| Marker | Meaning |
| --- | --- |
| **Hard** | Must be `done` (or equivalent landed) before starting |
| **Soft (~)** | Recommended; improves quality but must not block start |

Do not treat soft deps as blockers. Do not treat “unlocks / enhances” of an *earlier* milestone as a reason to wait on a later ticket.

## Claiming rules

1. **One agent → one ticket** (or one entire domain folder if tickets are tightly coupled and you state that in the PR).
2. Set the ticket `Status` to `in_progress` when you claim it.
3. Open branch: `ticket/Mxx-slug` (see each ticket’s Branch field).
4. Edit **only** paths listed under that ticket’s package boundary (exact globs).
5. Do not implement sibling domains “while you are here.”
6. Every behavioural change needs tests.
7. When merging, set Status to `done` and reference the PR.

## Domains

| Domain | Folder | Typical packages |
| --- | --- | --- |
| platform | [platform/](./platform/) | `apps/api` storage, `apps/web` settings |
| domain-model | [domain-model/](./domain-model/) | `packages/domain` |
| fixtures | [fixtures/](./fixtures/) | `packages/fixtures` |
| transformation | [transformation/](./transformation/) | `packages/transformation` |
| privacy | [privacy/](./privacy/) | `packages/privacy`, `apps/web` inspector |
| reasoning | [reasoning/](./reasoning/) | `packages/reasoning` |
| attention | [attention/](./attention/) | `packages/attention` |
| apple-bridge | [apple-bridge/](./apple-bridge/) | `apps/apple-bridge` + pinned ingestion sources |
| google | [google/](./google/) | pinned gmail / google_calendar sources |
| retrieval | [retrieval/](./retrieval/) | `packages/embeddings` |
| obligations | [obligations/](./obligations/) | `packages/attention` / future obligations |
| api-surface | [api-surface/](./api-surface/) | `apps/api` external routes |

## Ingestion file ownership (do not cross)

| Ticket | Owned path |
| --- | --- |
| M07 | `packages/ingestion/src/personal_enigma/ingestion/bridge_client.py` |
| M08 | `.../sources/apple_calendar.py` |
| M09 | `.../sources/apple_reminders.py` |
| M10 | `.../sources/apple_contacts.py` + `packages/identity/**` |
| M11 | `.../sources/gmail.py` |
| M12 | `.../sources/google_calendar.py` + `packages/dedupe/**` |
| M13 | `.../sources/apple_notes.py` |

Shared protocol types (`protocol.py`) are owned by M01-era scaffold; later tickets may only *import* them unless a dedicated ticket claims a protocol change.

Milestone map: [docs/architecture/milestone-map.md](../docs/architecture/milestone-map.md).

## Ticket template fields

Every ticket includes: Status, Branch, Domain, Package boundary, Hard depends, Soft depends, Unlocks / enhances, Non-goals, Acceptance criteria, Test plan, Privacy constraints.
