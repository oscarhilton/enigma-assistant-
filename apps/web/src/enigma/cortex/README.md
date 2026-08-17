# Cortex (Enigma brain visualizer)

Read-only observability UI for Enigma state transitions and privacy boundaries.

## Status: DEFERRED

| Deliverable | Status |
| --- | --- |
| `BrainEvent` types | ✅ |
| Event projection (`mapEvents`) | ✅ |
| Architecture doc | ✅ |
| Placeholder panel (`CortexPanel`) | ✅ |
| HomePage wiring | ❌ removed |

Resume after SEC-04 stabilises source→vault→transform→egress event flow. See [C10](../../../../tickets/conversational-ui/C10-cortex-brain-visualizer.md).

## Observability stack (now)

```text
Enigma Core → SEC-02/03 audit events → Egress Disclosure Panel (active)
```

Cortex wakes after SEC-04 gives stable ingestion lifecycle events.

## Frozen rule (C10)

> **Cortex may observe Enigma, but Cortex must never become a way of operating Enigma.**

Instrument panel, not control plane. No clicking nodes to mutate world model, approve assist, or alter attention.

## Invariant

**Cortex reads events — it never writes the world model.** All mutation stays in Enigma Core; this folder only projects audit/state feeds into `BrainEvent` values for display.

## Layout (v0)

- `events.ts` — `BrainEvent` union, region labels, SEC-07 slider stub metrics
- `mapEvents.ts` — project `DemoEvent`, `EnigmaEvent`, `EgressDisclosure` → `BrainEvent`
- `CortexPanel.tsx` — placeholder panel (region legend + event log); Three.js scene is future work

## Event sources

| Feed | API / hook | Maps to |
| --- | --- | --- |
| Demo evaluation log | `EnigmaClient.getDemoEvents()` | `world_state_changed`, `attention_qualified` |
| Live client bus | `EnigmaClient.subscribe()` | Same via `projectEnigmaEvent` |
| Egress disclosures | `EnigmaClient.getRecentDisclosures()` | `egress`, `privacy_transform` |

Future (post-SEC-04): `source_ingested`, `mime_parsed`, `private_record_created`, `relation_changed`, `egress_allowed`, `egress_denied`, plus SEC-06 `memory_decayed` / `memory_forgotten`.

## Dev

```bash
pnpm --filter @personal-enigma/web test src/enigma/cortex
```

Architecture: [docs/architecture/cortex-visualizer.md](../../../../docs/architecture/cortex-visualizer.md)  
Ticket: [C10](../../../../tickets/conversational-ui/C10-cortex-brain-visualizer.md)
