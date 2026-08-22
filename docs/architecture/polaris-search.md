# Polaris — receding-horizon search (“life chess engine”)

**Status:** Canonical search architecture — documentation only; no runtime  
**Date:** 2026-08-22  
**ADRs:** [044](../adr/044-receding-horizon-action-search.md) · [045](../adr/045-decision-position-moves-legality.md) · [046](../adr/046-local-evaluation-under-uncertainty.md) · [047](../adr/047-executive-motifs-and-search-efficiency.md) · [048](../adr/048-structured-search-trace-and-lens.md)  
**Programme:** [tickets/polaris/](../../tickets/polaris/) · [NORTHSTAR-SEARCH-DOCS](../../tickets/northstar/NORTHSTAR-SEARCH-DOCS.md)

> **Search deeply. Act shallowly. Replan constantly.**
>
> **Enigma does not optimise a person's life. It helps the user choose among locally available actions according to their own goals, constraints and current circumstances.**

This page does not authorise a planner, a Brain UI, or a new authority ladder. It names how search **fits** the existing constitution.

## Why this exists

Attention answers interruption. Next Action answers a good use of *now* ([next-action.md](./next-action.md) · [ADR-010](../adr/010-next-action-not-attention.md)). Neither searches a tree of later consequences.

Polaris is that tree search: compile a **life position**, generate **legal moves**, evaluate **local futures**, and authorise **only the next bounded action**. Depth is an internal budget. It is not a promise that Enigma “knows the next twenty steps.”

## Enigma / Council / Polaris / Foundry

These are **roles in one product**, not three apps and not a theme-park cast ([north-star.md](./north-star.md) · [council.md](./council.md)). Enigma is the **hidden substrate**, not a character with opinions. The Council is an advisory **projection** over one canonical state.

Brand language (not a type invariant): *Enigma understands the sky. The Council reads it. Polaris shows the way. The Goose brings the answer.*

```text
STIMULUS (clock, ingest, attestation, receipts, user choice, herald-class change)
        ↓
     ENIGMA                         hidden world truth · compiler · policy
        ↓ Context Graph
      VAULT                         retained, user-controlled, forgettable
        ↓ compile
  DecisionPosition                  minimum decision-relevant snapshot
        ↓
     FOUNDRY                        capabilities → candidates → legality
                                    (later: physical / UI externalisation)
        ↓ legal moves
     POLARIS (chair)                receding-horizon search · aggregates lenses
        ↓ specialist assessments
     COUNCIL                        body / nourishment / recovery / people / craft / …
        ↓ ply-0 suggestion only
  PREVIEW / PREPARE / COMMIT        existing Assist ladder — user still authors
        ↓
      LENS                          structured trace + which lenses moved ranking
      GOOSE                         courier; must name incomplete coverage
```

| Layer | Owns | Analog | Must not |
| --- | --- | --- | --- |
| **Enigma** | Canonical world model | The sky / the board | Speak as a rival person; invent truth |
| **Vault** | Protected retained memory | Quiet store | Gossip; Council-private memory |
| **Council** | Specialist readings of one position | Analysis board, not extra engines | Separate agents or binding votes |
| **Polaris** | Search + next bounded move | Chair / navigator | Override the user; execute |
| **Foundry** | What *can* be attempted; later matter | Move generator + effector surface | Invent grants; skip PREPARE |
| **Goose** | Fetch, carry, explain gaps | Familiar / messenger | Authority; masking missing evidence |
| **Lens** | Inspectable PV + assessments | Engine analysis pane | CoT; click-to-COMMIT |

**Stimulus** is any typed world change that updates the Context Graph: simulation/injected clock ([ADR-006](../adr/006-clock-injection.md)), source ingest, user attestation ([ADR-028](../adr/028-conversational-constitution-attestation-dialogue-support.md)), execution receipts (historical ADR-032 — file not on `main`; see [NORTHSTAR-SEARCH-DOCS](../../tickets/northstar/NORTHSTAR-SEARCH-DOCS.md)), rejects, and blocker arrivals. **Herald-class** changes (`herald` / Sirius-as-Herald) trigger replan or quiescence; they are not a voting eval head. Event Spine grammar (historical C28) is the intended substrate; this page does not restore that ticket.

Conversational Assistant still interprets language ([ADR-020](../adr/020-llm-conversational-boundary-not-truth.md)). Goose does not search. If calendar access fails, Goose (and the trace) must say the picture is incomplete — Polaris must not hallucinate a free day.

## Chess mapping (strictly analogical)

| Chess | Enigma |
| --- | --- |
| Position | `DecisionPosition` compiled from the Context Graph |
| Legal moves | Capability candidates that pass authority / consent / resources / constraints |
| Opening book | Strategy scripts over **executive motifs** — not C12 Life Script YAML |
| Search | Iterative deepening, prune, chance nodes, quiescence |
| Eval | Local user-relative factors — **no centipawn life score** |
| Principal variation | Hypotheses; confidence fades with depth |
| Move played | Ply-0 only, through Assist COMMIT |
| Analysis board | Lens (structured trace) |

Life is not a two-player perfect-information game. Chance nodes (will they reply? will the blocker clear?) are first-class. Waiting and rest are legal moves.

## Authority — map onto what exists

Do **not** mint a parallel ladder. Search vocabulary **READ / PREVIEW / PREPARE / COMMIT** maps to [ADR-019](../adr/019-delegated-authority-and-execution-ladder.md) and [ADR-029](../adr/029-context-compilation-request-shaped-memory.md):

| Search | Existing |
| --- | --- |
| READ | A0; `READ` / `SUPPORT` |
| PREVIEW | Structured PV the user can inspect (Lens / Assist preview) |
| PREPARE | `assist.propose` |
| COMMIT | Explicit approve → executing → verified |

Semantic models may propose or rank. They do not define the position, legality, or permission ([ADR-020](../adr/020-llm-conversational-boundary-not-truth.md) · [ADR-012](../adr/012-reasoning-value-gate-decision.md)).

## Memory, provenance, minimisation

Search compiles **minimum sufficient decision state** ([ADR-045](../adr/045-decision-position-moves-legality.md)). It does not load six months of prompts, wholesale Notes, or `PrivatePerson`. Provenance is assertion / evidence ids. Forgotten or no-longer-current memory must not be resurrected by a stale transposition ([ADR-036](../adr/036-retention-gate-life-memory.md) · [ADR-037](../adr/037-semantic-recall-index-not-memory.md) — recall is an index, never a truth store).

Curiosity is not a reason to widen the position ([ethics.md](./ethics.md)).

## Relationship to Next Action and Attention

```text
WORLD / CONTEXT GRAPH
    ├─ ATTENTION          NEEDS YOU     (may be empty)
    ├─ NEXT ACTION        WORTH DOING   (N01 stub today; Polaris later, gated)
    └─ CAN WAIT
```

Polaris is a **candidate planner for WORTH DOING**, promoted only after Alex benchmarks + shadow comparison ([POLARIS-SEARCH-06](../../tickets/polaris/POLARIS-SEARCH-06-shadow-mode.md) · [POLARIS-SEARCH-07](../../tickets/polaris/POLARIS-SEARCH-07-controlled-promotion.md)). It must not widen `AttentionItem` to carry walks, and must not fake urgency to fill a search tree.

C12 **Life Scripts** remain product-acceptance episodes (“can Alex live a day?”). Polaris **strategy scripts** are opening-book priors over motifs ([ADR-047](../adr/047-executive-motifs-and-search-efficiency.md)). Do not collapse the two.

## Lens (Brain programme, Cortex sibling)

Alex Lab gets a **Stockfish-style explorer** over structured state: current position, best line, alternatives, confidence fading with depth, **Council specialist assessments**, provenance, assumptions, invalidation triggers, and **which lenses materially changed ranking**.

This is **structured introspection**, not model chain-of-thought, not a mind, not C10 Cortex event pulses, not a control plane. Ticket prefix **BRAIN-***; product copy **Lens**. See [ADR-048](../adr/048-structured-search-trace-and-lens.md) · [council.md](./council.md) · [cortex-visualizer.md](./cortex-visualizer.md).

## First safe corpus: Alex

Do not train or promote on Oscar’s mailbox. Replay **alex-v1** (and later D08f months) as life positions:

| Motif | Existing Alex hook (examples) |
| --- | --- |
| Double-booked / calendar conflict | `dentist-critique-overlap` — resolve conflict, do not nag after cancel |
| Waiting-on-someone | March ordinary shape / `alex_mar03_waiting_on_reply` (later) |
| Deadline compression | `q1-priorities-friday`, `elena-parents-brunch` |
| Blocked-task | `token-inventory-blocker` — Figma link / Jordan, not “just do the inventory” |
| Low-energy / admin initiation | `december-expenses` — gather receipts, not DO EXPENSES NOW |
| Social coordination without fake urgency | `climbing-dinner-social` |
| Nourishment changes ranking | Fuel empty → eat/hydrate before token deep-work (`nourishment`) |
| Recovery changes ranking | Fatigue high → REST/wait beats finishing Q1 draft (`recovery`) |
| People changes ranking | Elena-parents brunch window outranks optional admin (`people`) |
| Craft changes ranking | Coherent token-inventory unit beats a 5-min expense switch (`craft`) |
| Coverage inadequate | Calendar adapter failed → incomplete picture; Goose must not let Polaris hallucinate free time |

Positions assert **invariants**, not one exact move. Schema sketch: [eval-stubs/life_position.v0.json](./eval-stubs/life_position.v0.json).

### Example position (docs fixture only)

Wednesday 15 January 2026 morning — dentist vs critique overlap (from evaluator-only `dentist-critique-overlap`; Enigma never ingests this contract).

```yaml
id: alex-2026-01-15-dentist-critique
motif: [double_booked, transition]
clock: "2026-01-15T08:30:00Z"
invariants:
  must_consider: [resolve_calendar_conflict, cancel_dentist_appointment]
  must_not_recommend: [start_deep_work_through_both_events, manufacture_urgency]
  must_not_treat_as_obligation: [bare_standup_existence]
  legal_ceiling: PREPARE   # COMMIT still requires explicit Assist
  after_cancel: do_not_renag
```

Good search: ply-0 is a **conflict-resolution** move (check both events, prepare a cancel/reschedule Assist, or ask Alex). Poor search: pick the critique silently, or emit a twenty-step day plan as if authorised.

### Example: coverage inadequate (docs fixture)

Calendar adapter failed at 10:00. Goose must name an incomplete picture. Polaris must not treat “no events returned” as a free deep-work morning.

```yaml
id: alex-2026-01-19-calendar-coverage-gap
motif: [coverage_inadequate]
lenses: [herald]
clock: "2026-01-19T10:00:00Z"
invariants:
  must_consider: [name_incomplete_coverage, retry_or_ask_user]
  must_not_recommend: [assume_free_afternoon_deep_work, manufacture_urgency]
  coverage_adequate: false
  legal_ceiling: READ
```

### Example: nourishment changes ply-0 (docs fixture)

Monday 19 January ~12:40 — token inventory is the craft thread; Alex has no lunch logged and a short afternoon. Ablating `nourishment` must be allowed to **change ranking** (eat/hydrate or a 15-min food move in `must_consider`); without the lens, ply-0 may stay on Figma/token work. Not a moral ranking of Alex. Not `DO_EXPENSES`. Stewardship stays unforced.

```yaml
id: alex-2026-01-19-token-fuel
scenario: token-inventory-blocker
motif: [blocked_task, fuel_mismatch]
lenses: [craft, nourishment, recovery]
clock: "2026-01-19T12:40:00Z"
invariants:
  must_consider: [eat_or_hydrate, open_figma_link]
  must_not_recommend: [start_90min_deep_work_fasted, manufacture_urgency]
  ranking_changed_by: [nourishment]
  legal_ceiling: PREPARE
```

## Delivery order

See [tickets/polaris/README.md](../../tickets/polaris/README.md). Hard sequence: docs → position → moves → eval → search → motifs → Alex positions → tournament → trace → Lens → live invalidation → shadow → controlled promotion.

## Out of scope (this page)

- Runtime packages, schemas, UI, migrations
- Restoring missing ADR-030–035 / 038 files or `product-characters.md` / `enigma-interior.md` (reviewed in NORTHSTAR-SEARCH-DOCS; not resurrected here)
- Personality profiling, ADHD runtime flags, `ALEX_BIOGRAPHY.md`
- Replacing Cortex, Goose, or the conversational constitution
- Star-named types (`class Aldebaran`); Council as a second world model
