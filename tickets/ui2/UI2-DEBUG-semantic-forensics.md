# UI2-DEBUG — Semantic Forensics

| Field | Value |
| --- | --- |
| Status | `todo` |
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

- [ ] Turn snapshot viewer (read-model: Turn Contract, Evidence, Handoff, AgentWork, Authority, egress, streaming trace, Memory impact)
- [ ] Copy bug report tiers: Safe / Detailed / Local forensic
- [ ] Keyboard shortcut ⌘⇧D opens forensics
- [ ] "Why not?" explainer for suppressed or absent actions
- [ ] No Cortex on main conversation surface

## Test plan

- Forensic dump copies valid JSON for each tier
- Shortcut toggles panel without breaking composer focus

## Privacy constraints

- Safe tier never includes raw PrivatePerson or wholesale Notes
- Local forensic tier never leaves machine without explicit user action
