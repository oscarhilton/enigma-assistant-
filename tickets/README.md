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
3. Open branch: `ticket/Mxx-slug` (MVP), `ticket/Dxx-slug` (Phase 2 Demo Mode), or `ticket/Sxx-slug` / `ticket/SExx-slug` (Phase 3 Shadow) — see each ticket’s Branch field.
4. Edit **only** paths listed under that ticket’s package boundary (exact globs).
5. Do not implement sibling domains “while you are here.”
6. Every behavioural change needs tests.
7. When merging, set Status to `done` and reference the PR.
8. **Merge gate:** CI green + agent self code-review before merge; do not block on Copilot when credits unavailable.
9. **Demo Mode never shares Private storage roots or HMAC / PERSON_\* keys** ([ADR-005](../docs/adr/005-demo-private-storage-roots.md)). Do not point `ENIGMA_DATABASE_URL` for Demo at the Private DB.
10. **Shadow Mode never shares Demo or Private roots** ([ADR-008](../docs/adr/008-shadow-storage-roots.md)). Demo→Shadow migration is impossible. Demo Mode is frozen for polish — prefer `tickets/shadow/` over new F-*/Demo UI work.

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
| obligations | [obligations/](./obligations/) | `packages/obligations` |
| api-surface | [api-surface/](./api-surface/) | `apps/api` external routes |
| demo-environment | [demo-environment/](./demo-environment/) | `packages/simulation` env + clock |
| demo-scenario | [demo-scenario/](./demo-scenario/) | `scenarios/**` |
| demo-simulation | [demo-simulation/](./demo-simulation/) | `packages/simulation` sources + engine |
| demo-evaluation | [demo-evaluation/](./demo-evaluation/) | `packages/evaluation` |
| demo-ui | [demo-ui/](./demo-ui/) | `apps/web` demo chrome ([D10](./demo-ui/D10-demo-ui.md), [D10a](./demo-ui/D10a-demo-suppression-ui.md), [D15](./demo-ui/D15-attention-card-ux.md)) — **frozen** for new polish beyond claimed tickets |
| shadow | [shadow/](./shadow/) | Phase 3 Shadow Mode (S01–S06) + eval artefacts ([SE01](./shadow/SE01-action-vs-attention.md)–[SE03](./shadow/SE03-weekly-shadow-review.md)); [shadow-mode.md](../docs/architecture/shadow-mode.md) · [shadow-evaluation.md](../docs/architecture/shadow-evaluation.md). SE* must not edit `EnvironmentMode`. |

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

## Synthetic source file ownership (Phase 2 — do not cross)

| Ticket | Owned path |
| --- | --- |
| D04 | `packages/simulation/src/personal_enigma/simulation/sources/{mail,calendar,reminders,notes,contacts}.py` |

Shared protocol types (`packages/ingestion/.../protocol.py`) are owned by M01-era scaffold; later tickets may only *import* them unless a dedicated ticket claims a protocol change.

Milestone map: [docs/architecture/milestone-map.md](../docs/architecture/milestone-map.md).  
Demo Mode architecture: [docs/architecture/demo-mode.md](../docs/architecture/demo-mode.md).  
Background corpus: [docs/architecture/demo-corpus.md](../docs/architecture/demo-corpus.md) (D08a–e; do not invent a top-level D13 for corpus).  
Shadow Mode: [docs/architecture/shadow-mode.md](../docs/architecture/shadow-mode.md) (S01–S06 after `v0.2.0-demo`).  
Shadow evaluation rubric: [docs/architecture/shadow-evaluation.md](../docs/architecture/shadow-evaluation.md) (seven post-Alex questions · SE01–SE03).  
MVP baseline tag: `v0.1.0-mvp` (`6253f96`).  
Demo freeze tag: `v0.2.0-demo` (Phase 2.5 PASS).
## Phase 2 corpus extension (D08 subtasks)

| Ticket | Status | Notes |
| --- | --- | --- |
| [D08a](./demo-scenario/D08a-canonical-spine.md) | `done` | Spine landed with `scenarios/alex-v1/` |
| [D08b](./demo-scenario/D08b-corpus-pipeline.md) | `done` | FinePersonas adapter, sanitiser, derived cache, 100-conv replay |
| [D08c](./demo-scenario/D08c-background-integration.md) | `done` | Canonical+background merge; A/B recall hook |
| [D08d](./demo-scenario/D08d-noise-layer.md) | `done` | Machine sludge + quiet-day (≠ D08c) |
| [D08e](./demo-scenario/D08e-canonical-scale.md) | `done` | Scale ladder + curve shapes → Phase 2.5 |

Architecture freeze preferred at `f404597` unless D08c proves a structural failure.

D03–D12 tickets carry **amendments** for background schema, multi-stream mail, `ScenarioSignalClass`, suppression metrics, UI stats, scale replay, and the compression demo sequence.

### F-* claim order (after D08c green)

Do not invent speculative F-* work during D08c. Once the merge gate is green, claim in this order:

1. Correctness: `F-background-basic` → `F-background-threading` → `F-background-identity` → `F-background-canonical-isolation` → `F-background-no-alert`
2. Quality: `F-background-volume-vs-importance` → `F-retrieval-keyword-pollution`
3. Import boundary: `F-corpus-real-domain-rewrite` → `F-corpus-live-url` → `F-corpus-secret-like-string` → `F-corpus-unexpected-real-entity`

## Ticket template fields

Every ticket includes: Status, Branch, Domain, Package boundary, Hard depends, Soft depends, Unlocks / enhances, Non-goals, Acceptance criteria, Test plan, Privacy constraints.
