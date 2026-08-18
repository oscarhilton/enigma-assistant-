# Tickets

Executable work units for **personal-enigma**, grouped by architecture domain so parallel agents can own one concern without tangling branches.

## Status legend

| Status | Meaning |
| --- | --- |
| `todo` | Unclaimed |
| `in_progress` | Claimed; branch open |
| `blocked` | Waiting on dependency or decision |
| `done` | Merged; acceptance criteria met |
| `future` | Design captured; **do not claim** until hard deps in the ticket are met |

## Dependency legend

| Marker | Meaning |
| --- | --- |
| **Hard** | Must be `done` (or equivalent landed) before starting |
| **Soft (~)** | Recommended; improves quality but must not block start |

Do not treat soft deps as blockers. Do not treat “unlocks / enhances” of an *earlier* milestone as a reason to wait on a later ticket.

## Claiming rules

1. **One agent → one ticket** (or one entire domain folder if tickets are tightly coupled and you state that in the PR).
2. Set the ticket `Status` to `in_progress` when you claim it.
3. Open branch: `ticket/Mxx-slug` (MVP), `ticket/Dxx-slug` (Phase 2 Demo Mode), `ticket/Rxx-slug` (Reasoning Value Gate), `ticket/Cxx-slug` (Conversational UI), `ticket/Pxx-slug` (PILOT-01 / My Enigma), or `ticket/Sxx-slug` / `ticket/SExx-slug` (Phase 3 Shadow) — see each ticket’s Branch field. Do not claim `future` tickets.
4. Edit **only** paths listed under that ticket’s package boundary (exact globs).
5. Do not implement sibling domains “while you are here.”
6. Every behavioural change needs tests.
7. When merging, set Status to `done` and reference the PR.
8. **Merge gate:** CI green + agent self code-review before merge; do not block on Copilot when credits unavailable.
9. **Demo Mode never shares Private storage roots or HMAC / PERSON_\* keys** ([ADR-005](../docs/adr/005-demo-private-storage-roots.md)). Do not point `ENIGMA_DATABASE_URL` for Demo at the Private DB.
10. **Shadow Mode never shares Demo or Private roots** ([ADR-008](../docs/adr/008-shadow-storage-roots.md)). Demo→Shadow migration is impossible. Demo Mode is frozen for polish — prefer `tickets/shadow/` over new F-*/Demo UI work.


## Isolated worktrees (parallel agents)

One ticket → one branch → one worktree. Do not run a second agent in the primary checkout while uncommitted programme work is sitting there.

From the primary clone (`adhd-personal-assistant`):

```bash
git worktree add ../enigma-wt-<ticket> -b ticket/<prefix>-<slug>
```

Examples: `ticket/C09-llm-conversational-boundary`, `ticket/C14-conversation-activity-stream`. Directory name is `enigma-wt-<ticket>` as a sibling of the primary clone (not inside it). A dirty index is fine — `git worktree add -b` checks out **HEAD only**; uncommitted files stay in the primary working tree. Do **not** copy, stash-pop, or split dirty files into the new worktree automatically.

| Rule | Detail |
| --- | --- |
| One ticket per worktree | Do not reuse a worktree for a second ticket. |
| Storage roots | Each worktree uses its own Private/Demo/Shadow data dirs. Never share `ENIGMA_DATABASE_URL`, HMAC keys, or vault paths across worktrees ([ADR-005](../docs/adr/005-demo-private-storage-roots.md), [ADR-008](../docs/adr/008-shadow-storage-roots.md)). |
| Launch | Point the agent (Cursor workspace / CLI cwd) at the worktree path, not the primary clone. |
| Remove when done | `git worktree remove ../enigma-wt-<ticket>` after the PR is submitted (or abandon). |

Existing in-repo `.worktrees/` checkouts are legacy; prefer sibling `../enigma-wt-*` going forward.

## Domains

| Domain | Folder | Typical packages |
| --- | --- | --- |
| platform | [platform/](./platform/) | `apps/api` storage, `apps/web` settings |
| domain-model | [domain-model/](./domain-model/) | `packages/domain` |
| fixtures | [fixtures/](./fixtures/) | `packages/fixtures` |
| transformation | [transformation/](./transformation/) | `packages/transformation` |
| privacy | [privacy/](./privacy/) | `packages/privacy`, `apps/web` inspector |
| reasoning | [reasoning/](./reasoning/) | `packages/reasoning`, `packages/evaluation` (R01–R07 gate) |
| attention | [attention/](./attention/) | `packages/attention` |
| next-action | [next-action/](./next-action/) | NextAction scorer / Something-else / preference ([N01](./next-action/N01-scorer-stub.md)–[N03](./next-action/N03-preference-learning.md)); schemas [M20](./domain-model/M20-next-action-schemas.md) · [next-action.md](../docs/architecture/next-action.md) |
| apple-bridge | [apple-bridge/](./apple-bridge/) | `apps/apple-bridge` + pinned ingestion sources |
| google | [google/](./google/) | pinned gmail / google_calendar sources |
| retrieval | [retrieval/](./retrieval/) | `packages/embeddings` |
| obligations | [obligations/](./obligations/) | `packages/obligations` |
| api-surface | [api-surface/](./api-surface/) | `apps/api` external routes |
| demo-environment | [demo-environment/](./demo-environment/) | `packages/simulation` env + clock |
| demo-scenario | [demo-scenario/](./demo-scenario/) | `scenarios/**` |
| demo-simulation | [demo-simulation/](./demo-simulation/) | `packages/simulation` sources + engine |
| demo-evaluation | [demo-evaluation/](./demo-evaluation/) | `packages/evaluation` |
| demo-ui | [demo-ui/](./demo-ui/) | `apps/web` demo chrome ([D10](./demo-ui/D10-demo-ui.md)–[D18](./demo-ui/D18-demo-next-action.md)) — **frozen** for new polish beyond claimed tickets |
| conversational-ui | [conversational-ui/](./conversational-ui/) | Conversational home + EnigmaClient ([C00](./conversational-ui/C00-demo-attention-projection.md)–[C08](./conversational-ui/C08-live-enigma-client.md)); [C09](./conversational-ui/C09-llm-conversational-boundary.md) LLM boundary; [C11](./conversational-ui/C11-tone-memory.md) tone memory (`future`); [C12](./conversational-ui/C12-life-scripts.md) Life Scripts; [C14](./conversational-ui/C14-conversation-activity-stream.md) activity stream; [C38](./conversational-ui/C38-shared-uncertainty-collapse.md) shared uncertainty collapse (`future`); [C39](./conversational-ui/C39-handoff-working-conclusion.md) handoff working conclusion (`future`); [architecture doc](../docs/architecture/conversational-ui.md) · [ADR-020](../docs/adr/020-llm-conversational-boundary-not-truth.md) |
| pilot | [pilot/](./pilot/) | PILOT-01 My Enigma — same product, two worlds ([P01](./pilot/P01-world-isolation-pilot-shell.md) isolation + shell · [P02](./pilot/P02-alex-life-scripts-as-product-tests.md) Level 1 · [P04](./pilot/P04-alex-full-life-reprime.md) Level 2 full-life reprime · [P03](./pilot/P03-calendar-read-support.md) Level 3); [data-boot.md](../docs/architecture/data-boot.md) · [ADR-040](../docs/adr/040-product-worlds-same-enigma.md) · [ADR-042](../docs/adr/042-three-level-data-boot.md) |
| shadow | [shadow/](./shadow/) | Phase 3 Shadow Mode (S01–S06) + eval (SE01–SE03) + silence track (SE04–SE10) + open-loop dues (SE11); [shadow-mode.md](../docs/architecture/shadow-mode.md) · [shadow-evaluation.md](../docs/architecture/shadow-evaluation.md) · [shadow-silence-evaluation.md](../docs/architecture/shadow-silence-evaluation.md) · [ADR-009](../docs/adr/009-silence-as-prediction.md). SE* must not edit `EnvironmentMode`. |

## Programme state (2026-08-18)

#103: observational infrastructure, no poultry expansion.
C36: intentionally unclaimed.
**PILOT-01 started** at [P01](./pilot/P01-world-isolation-pilot-shell.md) — World Isolation + Pilot Shell. Same Enigma, two worlds, hard storage/HMAC boundary ([ADR-040](../docs/adr/040-product-worlds-same-enigma.md)). **Data boot** is three levels ([data-boot.md](../docs/architecture/data-boot.md) · [ADR-042](../docs/adr/042-three-level-data-boot.md)): Level 1 Life Scripts ([P02](./pilot/P02-alex-life-scripts-as-product-tests.md) `done` / UI2-06) — current boot, in-repo fixtures, **no Hugging Face**; Level 2 Full Alex corpus ([P04](./pilot/P04-alex-full-life-reprime.md) `todo`) — HF messy life through normal ingest, **not UI2-06**; Level 3 My Enigma ([P03](./pilot/P03-calendar-read-support.md) `in_progress`). Do not download HF to boot Alex Lab. Forbidden: dataset → prebuilt Alex brain.

Two tracks, not to contaminate:
C37 — Is THE Goose telling the truth about work?
PILOT-01 — Does Enigma actually make Oscar’s day easier?


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
Background corpus: [docs/architecture/demo-corpus.md](../docs/architecture/demo-corpus.md) (D08a–e; six-month ordinary Alex is [D08f](./demo-scenario/D08f-alex-six-month.md) — version bump of `alex-v1`, not a top-level D13 and not `alex-v2`).  
Shadow Mode: [docs/architecture/shadow-mode.md](../docs/architecture/shadow-mode.md) (S01–S06 after `v0.2.0-demo`).  
Shadow evaluation rubric: [docs/architecture/shadow-evaluation.md](../docs/architecture/shadow-evaluation.md) (seven post-Alex questions · SE01–SE03).  
Shadow silence evaluation: [docs/architecture/shadow-silence-evaluation.md](../docs/architecture/shadow-silence-evaluation.md) (SUPPRESS as prediction · SE04–SE10 · [ADR-009](../docs/adr/009-silence-as-prediction.md)).  
Open-loop commitments: [docs/architecture/open-loop-commitments.md](../docs/architecture/open-loop-commitments.md) (SE11).  
Attention surface (Phase 2.5 wind-tunnel / F-* naming): [docs/architecture/attention-surface.md](../docs/architecture/attention-surface.md).  
Next Action (NEEDS YOU / WORTH DOING / CAN WAIT): [docs/architecture/next-action.md](../docs/architecture/next-action.md) · [ADR-010](../docs/adr/010-next-action-not-attention.md) · [M20](./domain-model/M20-next-action-schemas.md) · [N01](./next-action/N01-scorer-stub.md)–[N03](./next-action/N03-preference-learning.md).  
Support fitness overlay: [executive-function-support-benchmark.md](../docs/architecture/executive-function-support-benchmark.md) ([V2-EF-02](./demo-scenario/V2-EF-02-ef-arc-authoring.md) stretch after gate — contracts on D08f threads, **not** a second Alex package).  
**Reasoning Value Gate:** [reasoning-value-gate.md](../docs/demo/reasoning-value-gate.md) (R01–R07); [ADR-012](../docs/adr/012-reasoning-value-gate-decision.md).  
**Superseded by R01–R04:** [V2-EF-01](./demo-scenario/V2-EF-01-support-contract-design.md) → R01 · [EF-01](./demo-evaluation/EF-01-support-fitness-evaluator.md) → R04 · [D14](./demo-evaluation/D14-llm-judge-benchmark.md) → R03 — do not claim separately.  
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
| [D08f](./demo-scenario/D08f-alex-six-month.md) | `todo` | Six-month **ordinary events** in `alex-v1` (version bump; not `alex-v2`). Months: [D08f-02](./demo-scenario/D08f-02-february.md)…[D08f-06](./demo-scenario/D08f-06-june.md) · scripts [D08f-scripts](./demo-scenario/D08f-scripts.md) |

Architecture freeze preferred at `f404597` unless D08c proves a structural failure.

D03–D12 tickets carry **amendments** for background schema, multi-stream mail, `ScenarioSignalClass`, suppression metrics, UI stats, scale replay, and the compression demo sequence.

### F-* claim order (after D08c green)

Do not invent speculative F-* work during D08c. Once the merge gate is green, claim in this order:

1. Correctness: `F-background-basic` → `F-background-threading` → `F-background-identity` → `F-background-canonical-isolation` → `F-background-no-alert`
2. Quality: `F-background-volume-vs-importance` → `F-retrieval-keyword-pollution`
3. Import boundary: `F-corpus-real-domain-rewrite` → `F-corpus-live-url` → `F-corpus-secret-like-string` → `F-corpus-unexpected-real-entity`

### Attention-surface F-* (from wind-tunnel dump)

Named failures from the Demo Attention “successful failure” — see [attention-surface.md](../docs/architecture/attention-surface.md):

`F-calendar-existence-is-not-attention` · `F-past-calendar-event-resolves` · `F-automated-mail-is-not-commitment` · `F-newsletter-is-not-commitment` · `F-package-notification-is-not-commitment` · `F-social-question-is-pending-reply` · `F-unrelated-machine-mail-not-merged` · `F-distinct-social-plans-not-merged` · `F-low-priority-candidate-not-surfaced`

### R* claim order (Reasoning Value Gate)

Active sprint — see [reasoning-value-gate.md](../docs/demo/reasoning-value-gate.md):

1. **R01** — Scenario truth catalogue (alex-v1 0.2.1; absorbs V2-EF-01)
2. **R02** — Freeze Arm A baselines (after R01)
3. **R03** ∥ **R04** — LLM judge (absorbs D14) ∥ Support fitness (absorbs EF-01)
4. **R05** — Failure attribution (after R03 + R04)
5. **R06** — Privacy ablation (after R03; may overlap late R05)
6. **R07** — Exit report + architecture decision (after R05 + R06)

Do not claim V2-EF-01, EF-01, or D14 — consolidated into R01–R04.

## Ticket template fields

Every ticket includes: Status, Branch, Domain, Package boundary, Hard depends, Soft depends, Unlocks / enhances, Non-goals, Acceptance criteria, Test plan, Privacy constraints.
