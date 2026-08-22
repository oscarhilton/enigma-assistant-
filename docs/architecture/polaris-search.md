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

## Enigma / Polaris / Foundry

These are **roles in one product**, not three apps and not a theme-park cast ([north-star.md](./north-star.md) visibility rules still hold).

```text
STIMULUS (clock, ingest, attestation, receipts, user choice)
        ↓
     ENIGMA                         world truth · memory · attention · compiler · policy
        ↓ Context Graph
  DecisionPosition                  minimum decision-relevant snapshot
        ↓
     FOUNDRY                        named capabilities → candidate moves → legality
        ↓ legal moves
     POLARIS                        receding-horizon search · local eval · PV
        ↓ ply-0 suggestion only
  PREVIEW / PREPARE / COMMIT        existing Assist ladder — not a new one
        ↓
      LENS                          structured trace explorer (Alex Lab) — not chain-of-thought
```

| Layer | Owns | Analog | Must not |
| --- | --- | --- | --- |
| **Enigma** | What is true, remembered, interrupting, compilable, permitted | The board *and* the rules of the match | Optimise a life; treat the LLM as truth |
| **Foundry** | What *can* be attempted: capabilities, effects, legality filters | Move generator + referee | Invent grants; skip PREPARE |
| **Polaris** | Which legal line looks best *locally* under uncertainty | Search + eval | Define reality or execute |
| **Lens** | Inspectable PV / alternatives / invalidation | Engine analysis pane | Theatrical thoughts; click-to-COMMIT |

**Stimulus** is any typed world change that updates the Context Graph: simulation/injected clock ([ADR-006](../adr/006-clock-injection.md)), source ingest, user attestation ([ADR-028](../adr/028-conversational-constitution-attestation-dialogue-support.md)), execution receipts (historical ADR-032 — file not on `main`; see [NORTHSTAR-SEARCH-DOCS](../../tickets/northstar/NORTHSTAR-SEARCH-DOCS.md)), rejects, and blocker arrivals. Event Spine grammar (historical C28) is the intended substrate; this page does not restore that ticket.

Product characters (Assistant / Goose / Vault) stay **presentation of labour**. Polaris is not a fourth sitcom character. Goose does not search. The Assistant may *explain* a Lens line; it does not become the evaluator of record.

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

Alex Lab gets a **Stockfish-style explorer** over structured state: current position, best line, alternatives, confidence fading with depth, evaluation factors, provenance, assumptions, invalidation triggers.

This is **structured introspection**, not model chain-of-thought, not a mind, not C10 Cortex event pulses, not a control plane. Ticket prefix **BRAIN-***; product copy **Lens**. See [ADR-048](../adr/048-structured-search-trace-and-lens.md) · [cortex-visualizer.md](./cortex-visualizer.md).

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

## Delivery order

See [tickets/polaris/README.md](../../tickets/polaris/README.md). Hard sequence: docs → position → moves → eval → search → motifs → Alex positions → tournament → trace → Lens → live invalidation → shadow → controlled promotion.

## Out of scope (this page)

- Runtime packages, schemas, UI, migrations
- Restoring missing ADR-030–035 / 038 files or `product-characters.md` / `enigma-interior.md` (reviewed in NORTHSTAR-SEARCH-DOCS; not resurrected here)
- Personality profiling, ADHD runtime flags, `ALEX_BIOGRAPHY.md`
- Replacing Cortex, Goose, or the conversational constitution
