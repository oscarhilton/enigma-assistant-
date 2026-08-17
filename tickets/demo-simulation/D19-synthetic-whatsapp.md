# D19 — Synthetic WhatsApp adapter

| Field | Value |
| --- | --- |
| Status | `done` |
| Branch | `ticket/D19-synthetic-whatsapp` |
| Domain | `demo-simulation` |

## Package boundary (hard)

- May edit: `packages/simulation/src/personal_enigma/simulation/sources/whatsapp.py`, `packages/simulation/src/personal_enigma/simulation/sources/__init__.py`, `packages/simulation/src/personal_enigma/simulation/scenario.py`, `packages/simulation/tests/sources/**`, `packages/simulation/tests/test_scenario_format.py`, `scenarios/README.md`, `scenarios/feature/whatsapp-*/**`, `tickets/README.md` (ownership table)
- Must not edit: `packages/ingestion/src/personal_enigma/ingestion/sources/**`, `scenarios/alex-v1/**` (D08f)

## Hard depends

- M21
- D03, D04

## Non-goals

- Real WhatsApp ingestion
- Emitting obligations from the adapter
- Alex life overlay (D08f)

## Acceptance criteria

- [x] `whatsapp.receive` / `whatsapp.send` / `whatsapp.reaction` + `source: whatsapp`
- [x] `SyntheticWhatsAppSource` implements `DataSource` → `PrivateChatMessage`
- [x] Feature packs for the eight chat cases (source layer only)
- [x] Adapter never constructs `Obligation` / `AttentionItem`
- [x] Wired only through `DemoEnvironment`
