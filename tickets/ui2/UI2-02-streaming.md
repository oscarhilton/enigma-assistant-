# UI2-02 — True response streaming

| Field | Value |
| --- | --- |
| Status | `todo` |
| Branch | `ticket/UI2-02-streaming` |
| Domain | `ui2` |
| Programme | [UI2](./README.md) |

## Package boundary (hard)

- May edit: `apps/web/src/v2/**`
- May edit: `apps/api/src/personal_enigma/api/routes/worlds.py` (stream endpoint only, if not already present)
- Must not edit: v1 pilot conversation path

## Hard depends

- UI2-01 v2 shell (`in_progress`)

## Frozen spec (launchpad)

**Streaming responses** — first-class token/chunk streaming; text stream and AgentWork stream are **independent channels** (C35 honest).

## Acceptance criteria

- [ ] Incremental token/chunk rendering in v2 message list
- [ ] Cancel in-flight turn
- [ ] Reconnect / resume semantics documented and tested
- [ ] AgentWork stream independent from text stream (Goose updates without waiting for text)
- [ ] v1 remains non-streaming

## Test plan

- Stream renders partial text before turn completes
- Cancel aborts fetch and clears busy state
- Goose motion can update while text still streaming

## Privacy constraints

- Stream must not leak PrivatePerson or raw egress before transform
