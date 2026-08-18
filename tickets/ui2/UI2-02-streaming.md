# UI2-02 — True response streaming

| Field | Value |
| --- | --- |
| Status | `done` |
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

**North star:** Start familiar. Make it excellent. Let Enigma earn its uniqueness.

UI2-DEBUG will consume these as two independent channels. Do not mix text and AgentWork into one reconstructed stream — not for Goose, not for Debug.

Once this ticket lands, Debug’s first wiring is two parallel lanes from real stream events only:

```
ASSISTANT OUTPUT
chunk → chunk → chunk → complete

AGENT WORK
investigating → advancing → waiting / verifying → handled
```

## Converge

Intended after UI2-01 (#113), before UI2-03/04 and before rebasing UI2-DEBUG (#114) onto the resulting shell. Debug may land earlier if conflict-light; do not reshape this ticket around #114.

## Acceptance criteria

- [x] Incremental token/chunk rendering in v2 message list
- [x] Cancel in-flight turn (Stop generating response — not cancel underlying work)
- [x] Reconnect / resume semantics documented and tested
- [x] AgentWork stream independent from text stream (Goose updates without waiting for text)
- [x] UI2-DEBUG can consume the two channels as parallel lanes; do not mix text and AgentWork
- [x] v1 remains non-streaming

## Cancel semantics (frozen)

**Stop generating response ≠ cancel underlying work** unless the work itself is explicitly cancellable.

When the user hits Stop during streaming:

- Abort the fetch / prose stream (stop rendering new tokens).
- Do **not** reset AgentWork — Goose reflects the last `agent_work` event received, not idle, unless the server sends that.
- UI copy: "Stopped generating response" (not "Cancelled work").
- Server emits **nothing** on client abort today — the client must not fabricate work cancellation.
- Reconcile durable state via GET `/worlds/my_enigma/conversation` after Stop (`session.refresh()`).

## Test plan

- Stream renders partial text before turn completes
- Stop aborts prose fetch and clears busy state without resetting AgentWork
- Stop during prose preserves last `agent_work` Goose motion (e.g. `return`)
- Composer shows generation-stopped copy, not work-cancel wording
- Goose motion can update while text still streaming

## Privacy constraints

- Stream must not leak PrivatePerson or raw egress before transform
