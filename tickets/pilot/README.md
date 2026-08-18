# PILOT-01 — My Enigma

**North star:** Turn the proven architecture and Alex Life Scripts into one persistent application Oscar can actually live with.

**Governing invariant:** Alex and My Enigma are the **same product** operating against different worlds. Not a demo frontend vs a real frontend.

```text
                        ENIGMA
                           │
              ┌────────────┴────────────┐
              │                         │
          ALEX LAB                 MY ENIGMA
       deterministic              real governed
       synthetic world               world
```

| Same | Different |
| --- | --- |
| Today, Cases, Assistant, THE Goose, Why/inspectability, AgentWork, context compiler, authority model | source adapters, persistence namespace, clock, effects, identities/data |

**Storage:** Demo Mode never shares Private storage roots or HMAC / PERSON_* keys ([ADR-005](../../docs/adr/005-demo-private-storage-roots.md)). Product worlds are labels over `EnvironmentMode`, not a second app ([ADR-040](../../docs/adr/040-product-worlds-same-enigma.md)).

**Two tracks (do not contaminate):**

- C37 — Is THE Goose telling the truth about work?
- PILOT-01 — Does Enigma actually make Oscar’s day easier?

C36 stays unclaimed. No Goose habitat. No Settings Palace. No Memory Explorer redesign.

## Tickets

| Ticket | Title | Status |
| --- | --- | --- |
| [P01](./P01-world-isolation-pilot-shell.md) | World isolation + pilot shell | `done` |
| [P02](./P02-alex-life-scripts-as-product-tests.md) | Replay Alex Life Scripts as browser-level product tests | `future` |
| [P03](./P03-calendar-read-support.md) | First real source: Calendar READ + SUPPORT (no writes) | `future` |
