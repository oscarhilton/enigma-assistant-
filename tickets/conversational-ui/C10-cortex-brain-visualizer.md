# C10 — Cortex brain visualizer (observability)

**Status:** **DEFERRED** until SEC-04 stabilises source→vault→transform→egress event flow  
**Branch:** `ticket/C10-cortex-brain-visualizer`  
**Domain:** conversational-ui (observability / debug)  
**May edit:** `apps/web/src/enigma/cortex/**`, `apps/web/src/pages/HomePage.tsx`, `apps/web/src/styles.css`, `docs/architecture/cortex-visualizer.md`, `tickets/conversational-ui/**`  
**Must not edit:** World model writers (`packages/domain`, ingestion, transformation pipelines); audit store implementation (SEC-02 backend); evaluation benchmark runner (SEC-07)

**Hard depends:** [C06](./C06-provenance-debug.md) (provenance / qualification debug patterns), [C02](./C02-enigma-client.md) (`EnigmaClient`, `EnigmaEvent` stream), [SEC-02](../security/SEC-02-audited-remote-egress-gate.md) (egress disclosure feed)  
**Soft (~):** [C03](./C03-demo-time-machine.md) (checkpoint events), [SEC-07](../security/SEC-07-shadow-reconstruction-benchmark.md) (retention slider metrics), [SEC-06](../security/SEC-06-retention-memory-decay-forget.md) (decay / forget events)

## Current state (2026-08-17)

| Deliverable | Status |
| --- | --- |
| `BrainEvent` types | ✅ |
| Event projection (`mapEvents`) | ✅ |
| Architecture doc | ✅ |
| Placeholder panel (`CortexPanel`) | ✅ |
| HomePage wiring | ❌ removed |

## Observability stack (now)

```text
Enigma Core → SEC-02/03 audit events → Egress Disclosure Panel (active)
```

Cortex wakes after SEC-04 gives stable ingestion lifecycle events (source→vault→transform→egress).

## Future BrainEvent vocabulary (post-SEC-04)

`source_ingested` · `mime_parsed` · `private_record_created` · `world_state_changed` · `relation_changed` · `privacy_transform` · `egress_allowed` · `egress_denied` · `memory_decayed` · `memory_forgotten`

## Frozen rule (C10)

> **Cortex may observe Enigma, but Cortex must never become a way of operating Enigma.**

Instrument panel, not control plane. No clicking nodes to mutate world model, approve assist, or alter attention.

## Goal

Interactive **Cortex** view — live debug / privacy observability driven by real system events. Visualises what Enigma **did** (state transitions, data movement), **not** LLM chain-of-thought.

See [docs/architecture/cortex-visualizer.md](../../docs/architecture/cortex-visualizer.md).

## Non-negotiable invariant

> **Cortex reads audit / state / events only — it never writes the world model.**

No mutation endpoints. No feedback into projection, attention, or retention pipelines from the visualiser. See **Frozen rule (C10)** above.

## Deliverables

### v0 scaffold (types + placeholder panel — not on HomePage)

- [x] Architecture doc + ticket
- [x] `BrainEvent` union + region model in `apps/web/src/enigma/cortex/events.ts`
- [x] `CortexPanel` — region legend, event log, privacy-mode placeholder, SEC-07 slider stub
- [x] Project `EnigmaEvent` / `DemoEvent` / egress disclosures → `BrainEvent`
- [ ] ~~Wired on HomePage under-bonnet alongside egress disclosure panel~~ — **removed pending deferral**

### Future (Three.js / react-three-fiber)

- [ ] `@react-three/fiber` + `@react-three/drei` organic network scene
- [ ] Event-driven pulses animating region nodes (see event types in architecture doc)
- [ ] Privacy mode: membrane click → animate collapse from rich structure to coarse shadow
- [ ] Shadow decay visual: RAW → SHADOW → FORGET fade
- [ ] SEC-07 slider bound to live benchmark scores (utility % vs reconstructability %)
- [ ] Private-mode event feed from vault audit tail (post C08)
- [ ] Backend `BrainEvent` projection endpoint (optional; client-side projection acceptable for Demo)
- [ ] Re-wire `CortexPanel` on HomePage when audit event vocabulary is stable

## Acceptance criteria

- [x] Ticket + architecture doc describe regions, events, read-only invariant, privacy mode, SEC-07 tie-in
- [x] `BrainEvent` types cover v0 demo projection kinds (see **Future BrainEvent vocabulary** for post-SEC-04 expansion)
- [ ] Cortex panel reachable from conversational HomePage (under-bonnet) — **deferred**
- [x] Panel subscribes to `EnigmaClient.subscribe` and lists projected brain events (unit tests)
- [x] Egress disclosures map to membrane `egress` / `privacy_transform` events when panel opened
- [ ] Three.js scene renders stable region layout with pulse on new events
- [ ] Privacy mode animates shadow collapse tied to egress disclosure payload summaries
- [ ] SEC-07 slider shows SOURCE → ACTIVE → SHADOW → FORGOTTEN with live or fixture metrics
- [x] Tests: event projection unit tests; panel integration test
- [ ] No write paths from Cortex module into API mutation routes

## Test plan

- Unit: `mapEvents` — demo checkpoint / attention / silence → correct `BrainEvent` types and regions
- Unit: egress disclosure → `egress` vs blocked → `privacy_transform`
- Integration: `CortexPanel` opens, loads demo events + disclosures, renders region legend
- Regression: HomePage still renders conversation viewport when Cortex closed

## Related docs

- [cortex-visualizer.md](../../docs/architecture/cortex-visualizer.md)
- [conversational-ui.md](../../docs/architecture/conversational-ui.md)
- [SEC-07](../security/SEC-07-shadow-reconstruction-benchmark.md) · [SEC-02](../security/SEC-02-audited-remote-egress-gate.md)
- [ADR-023](../../docs/adr/023-persistent-shadow-abstract-state-not-biography.md) · [data-retention.md](../../docs/architecture/data-retention.md)
