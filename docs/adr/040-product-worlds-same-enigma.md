# ADR-040: Alex Lab and My Enigma are the same Enigma

## Status

Accepted

## Context

Demo Mode (Alex) proved the architecture against a deterministic synthetic world. The next programme is PILOT-01 — a persistent application Oscar can live with. The failure mode to avoid is splitting the product into “demo frontend” vs “real frontend.”

Storage isolation already exists: Demo, Private, and Shadow are separate roots and HMAC namespaces ([ADR-005](./005-demo-private-storage-roots.md), [ADR-008](./008-shadow-storage-roots.md)). What was missing was a **product-facing world** that a single app shell can switch, with those roots as the hard boundary.

## Decision

1. **One product.** Today, Cases, Assistant, THE Goose, Why/inspectability, AgentWork, the context compiler, and the authority model are shared. Worlds differ in source adapters, persistence namespace, clock, effects, and identities/data.

2. **Two product worlds** (P01 switcher), mapped onto existing `EnvironmentMode` values — not a new storage identity:

   | World | Label | Mode | Clock | Persistence |
   | --- | --- | --- | --- | --- |
   | `alex_lab` | Alex Lab | `demo` | `SimulationClock` | resettable Demo root |
   | `my_enigma` | My Enigma | `private` | `SystemClock` | persistent Private root |

   Shadow remains a third storage identity and is **not** in the P01 switcher.

3. **Runtime switch selects a `WorldHandle`.** A process may hold both handles. Switching never copies databases, vector indexes, HMAC / PERSON_* keys, aliases, conversation, or credentials. Equal storage roots or equal HMAC fingerprints are a hard error (`WorldIsolationError`).

4. **HMAC keys live under each world’s `secrets/hmac.key`.** Alex Lab must not load `PRIVATE_HMAC_KEY`. Resetting Alex Lab wipes only the Demo scenario root (D16). Resetting My Enigma is refused.

5. **Same shell.** The daily UI is one chrome (world switcher + Today + Cases + Ask Enigma + C35 Goose). `/demo/*` remains developer Demo chrome, gated on Alex Lab being the active world.

## Consequences

- `ENIGMA_ENVIRONMENT_MODE` sets the **default** active world (`demo` → Alex Lab, otherwise My Enigma). After boot, the active world is session state on the world registry.
- Demo conversation / timeline routes require the active world to be Alex Lab, not merely process env.
- Later Life Script browser tests (P02) and Calendar READ+SUPPORT (P03) attach to this shell; they must not fork a second app.

## Related

- [ADR-005](./005-demo-private-storage-roots.md) · [ADR-006](./006-clock-injection.md) · [ADR-008](./008-shadow-storage-roots.md)
- Tickets: [P01](../../tickets/pilot/P01-world-isolation-pilot-shell.md)
