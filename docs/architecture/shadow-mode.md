# Shadow Mode (Phase 3)

**Status:** Bootstrap after Phase 2.5 PASS (`v0.2.0-demo`) — implementation starts at S01  
**Tickets:** [tickets/shadow/](../../tickets/shadow/) (S01–S06)  
**Storage ADR:** [ADR-008](../adr/008-shadow-storage-roots.md)  
**Open questions (evaluation goals):** [shadow-mode-questions.md](./shadow-mode-questions.md)

Demo Mode proved Enigma on a coherent fictional life with known ground truth. Shadow Mode asks whether a **real** life behaves like that synthetic world — quietly, without acting on the user’s attention surface.

## Executive summary

Shadow Mode runs the **real** Enigma pipeline against **real** sources under a strict policy:

| Property | Shadow Mode |
| --- | --- |
| Sources | Real connectors only (read-only ingest policy) |
| Attention | Generated and logged |
| Notifications | Suppressed (no OS / tray / push delivery) |
| Storage | Fresh root under `~/.enigma/shadow/` — never Demo, never Private |
| Demo → Shadow | **Hard refuse** — no copy, link, remap, or key reuse |
| Clock | Wall clock (`SystemClock`) |

Demo Mode stays frozen for product polish (no new F-* / Demo chrome). Shadow does not enlarge Demo; it observes Private-shaped reality in isolation.

## Modes compared

```text
DEMO MODE                         SHADOW MODE                      PRIVATE MODE
─────────                         ───────────                      ────────────
Synthetic sources                 Real sources (read-only)         Real sources
SimulationClock                   SystemClock                      SystemClock
Attention + Demo UI               Attention logged, UI quiet       Attention + notify
~/.enigma/demo/<scenario>/        ~/.enigma/shadow/                ~/.enigma/private/
Fictional HMAC / PERSON_*         Fresh Shadow HMAC namespace       Private HMAC
```

Downstream packages still reason about domain concepts, not provider payloads. Only environment policy and storage roots differ.

## Hard environment separation

Shadow must never share with Demo **or** Private:

- databases, vector indexes, caches, attachments
- credentials namespaces / HMAC / PERSON_* keys / entity aliases
- provider audit logs, memory tables, source cursors
- attention history written for notification delivery

Preferred layout (configurable roots; see [ADR-008](../adr/008-shadow-storage-roots.md)):

```text
~/.enigma/
  private/
    enigma.db
    vectors/
    config/
    secrets/
  demo/
    alex-v1/
      ...
  shadow/
    enigma.db
    vectors/
    state/
    config/
    secrets/
    attention-log/
```

## Security / product invariants

When Shadow Mode is active:

```text
DEMO DATA MIGRATION = IMPOSSIBLE
NOTIFICATIONS = SUPPRESSED
```

- Registering a Demo→Shadow (or Demo→Private) migration path must raise — tested in S01.
- Shadow may construct real connectors; Demo still may not ([ADR-005](../adr/005-demo-private-storage-roots.md)).
- Attention scores and rationales are written to a Shadow attention log (S04); delivery channels stay off (S03).

## Environment banner

Every Shadow interface must label itself unmistakably, e.g.:

```text
SHADOW MODE — OBSERVATION ONLY · NOTIFICATIONS OFF
```

API and web stubs ship with S01; fuller chrome lands with later Shadow tickets.

## Evaluation goals (not implementation)

Shadow exists to confront the seven questions in [shadow-mode-questions.md](./shadow-mode-questions.md). Those questions are **evaluation goals** for Phase 3 — metrics, journals, and comparison stubs (S05) — not a checklist of features to ship in S01–S04.

Detailed observables, stub schemas, and weekly review layout: [shadow-evaluation.md](./shadow-evaluation.md) (SE01–SE03).

1. Act-on recognition  
2. Nearly-forgot  
3. Importance overestimate  
4. Relationship correctness  
5. Memory improvement  
6. Timing  
7. Misses synthetic never taught  

Comparison stubs may reference Demo eval artefacts for *shape* of metrics only. They must not import Demo scenario DBs or HMAC material into Shadow storage.

## Exit criteria (from Phase 2.5)

Shadow bootstrap is allowed because Phase 2.5 exit is PASS (`docs/reports/phase-2.5-exit-report.md`, tag `v0.2.0-demo`). Leaving Shadow for full Private notifications requires a later gate (S06) — not “Demo looked good.”

## Package map

| Path | Role |
| --- | --- |
| `packages/simulation` | `EnvironmentMode.SHADOW`, storage roots, migration refuse, Shadow env |
| `apps/api` | `/shadow/*` banner / status stubs |
| `apps/web` | SHADOW MODE banner stub |
| `packages/attention` | Shadow attention log wiring (S04) |
| `packages/evaluation` | Comparison stubs vs Demo-shaped metrics (S05); Shadow eval artefacts (SE01–SE03) |
| `tickets/shadow/` | S01–S06 work units + SE01–SE03 eval instrumentation |

## Ticket order

```text
S01 env flag + scaffold + refuse migration
  → S02 storage isolation (keys, DB wiring)
  → S03 notification suppression
  → S04 shadow attention log
  → S05 comparison stubs (seven questions as goals)
  → S06 exit criteria / promote-from-shadow gate
```
