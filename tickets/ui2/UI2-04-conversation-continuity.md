# UI2-04 — Conversation continuity

| Field | Value |
| --- | --- |
| Status | `todo` |
| Branch | `ticket/UI2-04-conversation-continuity` |
| Domain | `ui2` |
| Programme | [UI2](./README.md) |

## Package boundary (hard)

- May edit: `apps/web/src/v2/**`
- May edit: `apps/api` conversation thread routes if needed
- Must not edit: v1 EnigmaProvider semantics without ADR

## Hard depends

- UI2-01 v2 shell
- UI2-02 streaming (~)

## Frozen spec (launchpad)

**Basically ChatGPT** — conversation-first, sidebar/history, bottom composer, minimal chrome.

**Architecture:** Read-model driven — UI consumes `AssistantTurn` projections; world-switch isolation (C34 survives streaming).

## Acceptance criteria

- [ ] Thread list in sidebar with create/select
- [ ] History persists per world (Alex Lab ↔ My Enigma isolated)
- [ ] World switch clears or scopes thread selection (ADR-040)
- [ ] C34 relational bootstrap expressiveness survives streaming turns

## Test plan

- WORLD_SWITCH parity with P01 for v2 thread state
- Thread survives refresh within same world

## Privacy constraints

- No cross-world thread or message leakage
