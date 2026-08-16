# Demo Mode (Phase 2)

**Status:** Tickets ready (post-`v0.1.0-mvp`) — implementation starts at D01  
**Spec:** Enigma Phase 2 — Demo Mode Technical Specification v0.2  
**Tickets:** [milestone-map.md](./milestone-map.md) (D01–D12)

## Executive summary

MVP proves Enigma can ingest, transform, reason, attend, and stay private for individual events. Phase 2 asks a harder question:

> Can Enigma develop a useful model of a person **over time**?

Demo Mode runs the **real** Enigma pipeline against one or more fictional lives whose synthetic world has **known ground truth**. The canonical initial persona is **Alex Morgan** (`scenarios/alex-v1/`). Downstream packages must not know whether inputs came from synthetic or private adapters.

Demo Mode simultaneously serves as:

- system-level evaluation harness
- regression suite
- product demonstration / onboarding
- privacy demonstration under adversarial content
- debugging and memory/attention benchmark

## Synthetic vs private adapters

Only source adapters differ. Everything downstream is production code.

```text
PRIVATE MODE                         DEMO MODE
─────────────                        ─────────
GmailSource                          SyntheticMailSource
AppleCalendarSource                  SyntheticCalendarSource
AppleRemindersSource                 SyntheticReminderSource
AppleNotesSource                     SyntheticNotesSource
AppleContactsSource                  SyntheticContactsSource
GoogleCalendarSource                 (same synthetic calendar surface)
```

Synthetic adapters live under `packages/simulation/.../sources/` (D4). Real adapters stay under `packages/ingestion/.../sources/`.

## Hard environment separation

Demo and Private must never share:

- databases, vector indexes, caches, attachments
- credentials, HMAC / PERSON_* keys, entity aliases
- provider audit logs, memory tables, source cursors

Preferred layout (configurable roots; see [ADR-005](../adr/005-demo-private-storage-roots.md)):

```text
~/.enigma/
  private/
    enigma.db
    vectors/
    config/
    secrets/
  demo/
    alex-v1/
      enigma.db
      vectors/
      state/
      config/
```

## Security invariant

When Demo Mode is active:

```text
REAL SOURCE ACCESS = IMPOSSIBLE
```

Not merely UI-disabled. `DemoEnvironment` exposes no real credentials (`gmail_credentials = None`, `apple_bridge = None`). Registering or instantiating a real connector while `EnvironmentMode.DEMO` must raise. This is a tested invariant owned by D01 (`packages/simulation`).

## Environment banner

Every Demo interface must label itself unmistakably, e.g.:

```text
DEMO MODE — FICTIONAL DATA ONLY
Scenario: Alex Morgan v1
```

API and web stubs ship with D01; full demo chrome is D10. Attention / Why
representation layers: [representation-layers.md](../demo/representation-layers.md).

## Clock injection

Domain logic must not call `datetime.now()` directly. Inject a `Clock` ([ADR-006](../adr/006-clock-injection.md)): `SystemClock` in Private Mode, `SimulationClock` in Demo Mode (D2).

## Governing principle

MVP asks whether Enigma can understand **information**. Demo Mode asks whether it can understand **continuity** — what was promised, what changed, what still matters — and answer:

> What would actually help right now?

before Enigma is entrusted with a real person's life.

## Package map

| Path | Role |
| --- | --- |
| `packages/simulation` | Environment, clock stubs, event stubs, synthetic source pins |
| `packages/evaluation` | Eval runner + metric placeholders |
| `scenarios/` | Immutable scenario packages (`alex-v1`, …) |
| `tickets/demo-*` | Phase 2 work units D01–D12 |
