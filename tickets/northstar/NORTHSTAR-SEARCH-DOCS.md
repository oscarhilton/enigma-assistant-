# NORTHSTAR-SEARCH-DOCS — Reconcile North Star and Polaris search constitution

| Field | Value |
| --- | --- |
| Status | `in_progress` (this docs PR) |
| Branch | `cursor/northstar-polaris-search-adrs-tickets-fd45` |
| Domain | `northstar` (docs / tickets only) |

## Package boundary (hard)

- May edit: `docs/adr/044-*.md` … `docs/adr/048-*.md`, `docs/architecture/polaris-search.md`, `docs/architecture/council.md`, `docs/architecture/eval-stubs/life_position.v0.json`
- May amend (pointer-only, no doctrine rewrite): `docs/architecture/north-star.md`, `overview.md`, `ethics.md`, `next-action.md`, `cortex-visualizer.md`, `milestone-map.md`, `AGENTS.md`
- May edit: `tickets/northstar/**`, `tickets/polaris/**`, `tickets/demo-evaluation/ALEX-EVAL-*.md`, `tickets/conversational-ui/BRAIN-*.md`, `tickets/README.md`, `tickets/conversational-ui/README.md`
- Must not edit: production code, tests, UI, schemas (other than the eval stub above), migrations, Python/TS dependencies, `scenarios/alex-v1/**` timeline/content, donor ADRs 030–038 wholesale
- Must not: mint ADR-049 for Council; mint a `COUNCIL-01` ticket — Council is product ontology over ADR-044–048, carried by this ticket + POLARIS-SEARCH-03 + BRAIN-* + ALEX-EVAL-01

## Hard depends

- None (docs capture on current `main`)

## Soft depends (~)

- Historical ADR-030–038 + `product-characters.md` / `enigma-interior.md` at `13ed0d3` (inspect; do not block)

## Unlocks / enhances

- All `POLARIS-SEARCH-*`, `ALEX-EVAL-*`, `BRAIN-*` tickets (`future` until this ticket is `done`; **programme gate:** do not claim PolarIS implementation until Observatory 01–02 are `done`)

## Intent

Capture Polaris receding-horizon search **against** existing constitution, not as a rival OS:

- North Star / ethics (user is subject; no life optimisation)
- Enigma / Polaris / Foundry / Stimulus / Context Graph
- Authority mapped to READ / PREVIEW / PREPARE / COMMIT **on** ADR-019 / ADR-029 (not a second ladder)
- Memory / provenance / minimisation via ADR-023 / 029 / 036 / 037
- Search ADRs 044–048 (Council is a **projection** over them, not a ninth constitution)
- Remaining ADR-030–038 review (files vs references)
- Product language: Enigma / Vault / Council / Polaris / Goose / Foundry ([council.md](../../docs/architecture/council.md)) — functional seats before star names; internals stay typed

## ADR number mapping (this wave)

Highest ADR **file** on `main` before this ticket: **043**. Numbers **030–035 and 038** are historically used (referenced; files absent after Tranche A restore `5208b8d`, which explicitly did not restore 030–038). **036 and 037 are present.** **044–048 were free** and are used here.

| Assumed (if 044–048 conflicted) | Actual | Title |
| --- | --- | --- |
| 044 | **044** | Receding-horizon action search |
| 045 | **045** | DecisionPosition, candidate moves, legality |
| 046 | **046** | Local evaluation under uncertainty |
| 047 | **047** | Executive motifs and search efficiency |
| 048 | **048** | Structured search trace and Lens |

No conflict: do not reuse 030–038.

## ADR-030–038 review (done as inspection, not restore)

| ADR | On `main`? | Notes |
| --- | --- | --- |
| 030 Conversation capsule | **No** (last at C15-era branches / `78dd67b`) | Referenced by recovered tickets; do not rewrite here |
| 031 Semantic bootstrap | **No** | C34 still hard-depends “ADR-031 on main” |
| 032 Action ledger | **No** | Stimulus/receipts analog; cited in polaris-search as historical |
| 033 Bounded subtask workers | **No** | Workers ≠ Polaris searcher |
| 034 Evidence coverage bundle | **No** | Satchel / Goose; Lens must not steal this |
| 035 Grounded assertions | **No** (linked from ADR-036) | Provenance substrate for traces |
| 036 Retention gate | **Yes** | Search must not invent a second memory |
| 037 Semantic recall index | **Yes** | Hits are not DecisionPosition truth |
| 038 Humour constitution | **No** | North Star dangling link fixed to not require the file |

Restore of missing 030–035 / 038 / `product-characters.md` / `enigma-interior.md` is an **Oscar decision**, not this ticket’s runtime. Do not resurrect donor code wholesale.

## Existing-doc conflicts reconciled

| Conflict | Resolution |
| --- | --- |
| C12 “Life Scripts” vs opening-book “Life Scripts” | C12 stays product-acceptance episodes; Polaris uses **strategy scripts** / executive motifs ([ADR-047](../../docs/adr/047-executive-motifs-and-search-efficiency.md)) |
| “Brain View” vs Cortex preferred name | Programme tickets `BRAIN-*`; product copy **Lens**; Cortex unchanged ([ADR-048](../../docs/adr/048-structured-search-trace-and-lens.md)) |
| N01 local fitness vs Polaris eval | Complementary; promotion gated; no global life score |
| READ/PREVIEW/PREPARE/COMMIT vs A0–A5 / ADR-029 speech acts | Mapping table in ADR-044; no parallel ladder |
| Missing `product-characters.md` linked from North Star | Dangling links removed; historical pointer in this ticket |
| C30 Brain / inventory (not on `main`) | Not restored; Lens is search introspection, not a memory store |
| North Star “Do not add nouns” vs Council | Council is an **inspectable projection**, not a front-page cast. Star aliases (Aldebaran / Spica / Canopus) stay off the always-visible layer. Conversational Assistant remains ADR-020 language boundary; Polaris is navigator/chair in product copy, not the hosted model |
| Foundry as eval factory vs effector | One Foundry: capabilities + legality/effects, later physical/UI externalisation. Not a second searcher |
| Dedicated COUNCIL-01 / ADR-049 | **Not created.** Seats, ranking attribution, and Goose coverage rules fit existing 044–048 + POLARIS-SEARCH-03 / BRAIN / ALEX-EVAL tickets |
| Observatory vs PolarIS as “next” | Observatory 01–02 are the first visible deliverable ([observatory.md](../../docs/architecture/observatory.md)). PolarIS internal graph is unchanged; do not claim PolarIS implementation until 01–02 are `done`. No new Council stars for the graph. |
| Harbour vs PolarIS / Foundry / Council | Harbour is CAN-begin / transition friction ([harbour.md](../../docs/architecture/harbour.md)). Not a planner, not Foundry, not a seat, no star name, **no ADR-049**. |

## Non-goals

- Production planner, UI, schemas, tests
- Restoring ADR-030–038 files
- Rewriting ADR-010 / 019 / 020 / 023 / 026 / 029
- Hugging Face / My Enigma promotion

## Acceptance criteria

- [x] ADR-044–048 accepted as docs-only on this branch
- [x] [polaris-search.md](../../docs/architecture/polaris-search.md) names Enigma / Vault / Council / Polaris / Goose / Foundry / Context Graph / Stimulus / Lens
- [x] [council.md](../../docs/architecture/council.md) records approved product cosmology without a competing ADR number
- [x] North Star gains squeeze 8 (local choice, not life optimisation) without replacing the thesis; Council stays inspectable, not a theme-park cast
- [x] Next Action + Cortex docs point at Polaris/Lens/Council without merging surfaces
- [x] Implementation tickets exist with hard/soft deps and exit conditions (no extra Council ticket)
- [x] Example Alex life positions in docs (dentist/critique overlap; nourishment ranking; calendar coverage gap) — no `scenarios/` edits
- [x] ADR-030–038 review recorded above
- [ ] Status → `done` on merge of this PR (Oscar/reviewer)

## Exit conditions

This ticket is **done** when the docs/tickets PR merges with ADRs 044–048 and the programme tickets listed in [polaris/README.md](../polaris/README.md). Missing historical ADR files are **not** a blocker.

## Test plan

- Relative markdown links from new/amended docs resolve (`council.md`, ADRs 044–048, polaris-search, tickets)
- `uv run ruff check .` (no Python changes expected)
- Canonical lightweight: `uv run pytest apps/api/tests/test_turn_kernel.py` · `uv run ruff check .` (docs-only; no behavioural tests)
- Eval stub JSON parses; new motif/lens enums cover ALEX-EVAL-01 sketches

## Privacy constraints

- Docs must not introduce a biography store, CoT-as-memory, or Oscar-inbox corpus
- Alex remains a crash-test dummy ([ADR-026](../../docs/adr/026-ethics-creed-user-is-subject.md))
