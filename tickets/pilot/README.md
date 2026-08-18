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

**Data boot** ([data-boot.md](../../docs/architecture/data-boot.md) · [ADR-042](../../docs/adr/042-three-level-data-boot.md)):

```text
LEVEL 1 — Life Scripts          "Does the system behave correctly?"
          small, deterministic, constitutional
          = P02 / UI2-06     (in-repo fixtures; current boot; no Hugging Face)

LEVEL 2 — Full Alex corpus      "Does it behave correctly when life is noisy?"
          HF messy synthetic life (email / WhatsApp / calendar / history)
          = P04              NOT UI2-06; must use normal ingest machinery

LEVEL 3 — My Enigma             "Does it genuinely help?"
          Oscar's actual governed sources
          = P03+
```

Current Alex Lab boot does **not** need the Hugging Face corpus. Level 1 fixtures stay resettable. Do not fold P04 into UI2-06. Forbidden: dataset → prebuilt Alex brain.

**Order:** merge UI2 stack → UI2-06 five-script graduation → pilot-grade → **then** P04. **Start-gate:** do not start P04 until Goose has passed basic flight certification (UI2-06 through `/v2`, forensic diagnosability, UI2 declared pilot-grade). No Hugging Face download required yet.

**Two tracks (do not contaminate):**

- C37 — Is THE Goose telling the truth about work?
- PILOT-01 — Does Enigma actually make Oscar’s day easier?

C36 stays unclaimed. No Goose habitat. No Settings Palace. No Memory Explorer redesign.

## Tickets

| Ticket | Title | Status |
| --- | --- | --- |
| [P01](./P01-world-isolation-pilot-shell.md) | World isolation + pilot shell | `done` |
| [P02](./P02-alex-life-scripts-as-product-tests.md) | Replay Alex Life Scripts as browser-level product tests | `done` (#107, #108) |
| [P03](./P03-calendar-read-support.md) | First real source: Calendar READ + SUPPORT (no writes) | `in_progress` (P03a #109; P03c ingress; **not done**) |
| [P03b](./P03b-live-calendar-ingress.md) | Store ingress contract (CI slice) | `done` (#110) |
| [P03c](./P03c-apple-live-ingress.md) | Apple live ingress (operator sync → private store) | `in_progress` |
| [P04](./P04-alex-full-life-reprime.md) | Alex Full-Life Reprime (Level 2 HF stress-test world) | `future` (start-gate: Goose flight cert) |
