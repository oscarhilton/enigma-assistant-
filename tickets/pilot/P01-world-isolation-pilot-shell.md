# P01 — World Isolation + Pilot Shell

| Field | Value |
| --- | --- |
| Status | `done` (PR #105) |
| Branch | `ticket/P01-world-isolation` |
| Domain | `pilot` |
| Programme | [PILOT-01](./README.md) |

## Package boundary (hard)

- May edit: `packages/simulation/src/personal_enigma/simulation/worlds.py` (create)
- May edit: `packages/simulation/src/personal_enigma/simulation/__init__.py`
- May edit: `packages/simulation/src/personal_enigma/simulation/environment.py` (exports / helpers only)
- May edit: `packages/simulation/tests/test_worlds.py` (create)
- May edit: `apps/api/src/personal_enigma/api/routes/worlds.py` (create)
- May edit: `apps/api/src/personal_enigma/api/main.py` (install world routes)
- May edit: `apps/api/src/personal_enigma/api/routes/demo.py` (gate Demo routes on active **Alex Lab** world, not process env alone)
- May edit: `apps/api/tests/test_world_routes.py` (create)
- May edit: `apps/web/src/pilot/**` (create)
- May edit: `apps/web/src/App.tsx`, `apps/web/src/App.test.tsx`
- May edit: `apps/web/src/pages/HomePage.tsx` (Today surface inside the pilot shell)
- May edit: `apps/web/src/enigma/EnigmaProvider.tsx` (select client from active world)
- May edit: `apps/web/src/styles.css` (pilot chrome only)
- May add/amend: [ADR-040](../../docs/adr/040-product-worlds-same-enigma.md), [ADR-005](../../docs/adr/005-demo-private-storage-roots.md) (pointer only)
- May edit: `docs/architecture/overview.md`, `docs/architecture/milestone-map.md`, `tickets/README.md`, `tickets/conversational-ui/README.md`, this folder
- Must not edit: Gmail / Google Calendar write paths, C36, Goose habitat, Settings Palace, Memory Explorer redesign, `packages/ingestion/.../sources/*`, scenario corpora

## Hard depends

- D01 environment separation (`done`)
- D02 simulation clock (`done`)
- ADR-005 / ADR-008 storage roots (`done`)
- C01 conversation shell + C35 Goose pixel licence (`done`)

## Soft depends (~)

- D16 Demo reset (`done`) — Alex Lab reset reuses the Demo wipe, never Private
- C08 LiveEnigmaClient — My Enigma conversation may be a quiet stub until C08

## Unlocks / enhances

- Launch one Enigma and switch Alex Lab ↔ My Enigma
- [P02](./P02-alex-life-scripts-as-product-tests.md) browser-level Life Scripts
- [P03](./P03-calendar-read-support.md) first real source

## Non-goals

- C36 / Goose habitat / extra Goose chrome (Goose remains C35 projection)
- Settings Palace, Memory Explorer redesign
- Gmail, calendar writes, or connecting a real mailbox
- Replaying Life Scripts as browser tests (P02)
- Shadow Mode in the world switcher (still a third storage identity)

## Acceptance criteria

- [x] Product worlds: **Alex Lab** (synthetic, `SimulationClock`, resettable) and **My Enigma** (private, `SystemClock`, persistent)
- [x] Hard storage / HMAC / identity boundary — never share Private storage roots or HMAC keys ([ADR-005](../../docs/adr/005-demo-private-storage-roots.md))
- [x] Launch Enigma and switch worlds in chrome; one app shell (Today + Cases + Ask Enigma)
- [x] Goose stays C35 (`surface-goose` from AgentWork); no extra Goose chrome
- [x] Alex Lab reset does not touch My Enigma; My Enigma reset is refused
- [x] Deferred work recorded as [P02](./P02-alex-life-scripts-as-product-tests.md) / [P03](./P03-calendar-read-support.md) notes only
- [x] Freeze isolation: WORLD_SWITCH_01/02, IDENTITY_01, KEY_01, RESET_01/02, ROUTE_01, CLOCK_01, GOOSE_01, CASE_01
- [x] ADR-040: no world-derived state survives a switch unless explicitly product-global (including React leftover state)

## Test plan

- WORLD_SWITCH_01/02 — conversation does not cross Alex Lab ↔ My Enigma (API + React remount)
- IDENTITY_01 — same email → different PERSON_* tokens
- KEY_01 — demo/private HMAC fingerprints differ
- RESET_01 — Alex reset destroys only Alex state
- RESET_02 — private reset is impossible through `/worlds/my_enigma/reset` and `/demo/reset`
- ROUTE_01 — `/demo/*` rejected while My Enigma is active
- CLOCK_01 — Alex clock manipulation cannot alter private temporal state
- GOOSE_01 — world switch cannot leave stale AgentWork projected by Goose
- CASE_01 — case selected in world A cannot remain selected as if valid in B
- UI still uses one app shell (Today / Cases / world switcher / Ask Enigma)

## Privacy constraints

- Demo never loads `PRIVATE_HMAC_KEY` or real connector credentials
- World API must not return raw HMAC key material
- Switching must not copy Demo conversation, aliases, or keys into Private
