# UI2-DEBUG — Semantic Forensics

| Field | Value |
| --- | --- |
| Status | `done` |
| Branch | `ticket/UI2-DEBUG-semantic-forensics` |
| Domain | `ui2` |
| Programme | [UI2](./README.md) |

## Package boundary (hard)

- May edit: `apps/web/src/v2/debug/**`
- May edit: `apps/web/src/v2/V2DebugRoute.tsx`
- Must not edit: v1 `TurnTracePanel` / Cortex as product surface

## Hard depends

- UI2-01 v2 shell
- UI2-02 streaming (~)

## Frozen spec (launchpad)

**UI:** Show what matters, what Enigma is doing, and why — without requiring users to understand architecture.

**Deferred from UI2-01:** Full panel not required for boot; stub route OK.

## Acceptance criteria

- [x] Turn snapshot viewer (read-model: Turn Contract, Evidence, Handoff, AgentWork, Authority, egress, streaming trace, Memory impact)
- [x] Copy bug report tiers: Safe / Detailed / Local forensic
- [x] Keyboard shortcut ⌘⇧D opens forensics
- [x] "Why not?" explainer for suppressed or absent actions
- [x] No Cortex on main conversation surface
- [x] Unavailable semantic state is never reconstructed or guessed by the frontend (TURN CONTRACT, RELATIONAL BOOTSTRAP, HANDOFF, AUTHORITY, MEMORY, STREAMING TRACE render “Not captured for this turn” until the real projection is on the wire)
- [x] Every copy bundle starts with an unmistakable header (`ENIGMA FORENSIC SNAPSHOT` + Build / World / Turn / Privacy level: SAFE | DETAILED | LOCAL)
- [x] STREAMING TRACE is the captured SSE chronological log (WORK / PROSE / TURN / ERROR) with client capture timestamps; one-shot JSON turns stay “Not captured for this turn”

## Test plan

- Forensic dump copies valid JSON for each tier
- Every copy bundle starts with `ENIGMA FORENSIC SNAPSHOT` and a `Privacy level:` line
- Unavailable sections render “Not captured for this turn” and are not reconstructed from nearby fields
- STREAMING TRACE lanes stay independent in projection; UI shows unified timeline for race diagnosis; empty / one-shot turns stay Not captured
- Shortcut toggles panel without breaking composer focus

## Privacy constraints

- Safe tier never includes raw PrivatePerson or wholesale Notes
- Local forensic tier never leaves machine without explicit user action
