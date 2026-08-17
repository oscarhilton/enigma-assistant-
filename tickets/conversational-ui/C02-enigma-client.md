# C02 — EnigmaClient + shared types

**Status:** in_progress  
**Branch:** `ticket/C02-enigma-client`  
**May edit:** `apps/web/src/enigma/**`  
**Must not edit:** Python packages (types TS-first)

## Contract (frozen)

```typescript
type AttentionState = {
  simulated_time: string;
  needs_you: AttentionItem[];     // attention policy: surface
  context: AttentionItem[];       // attention policy: context — NOT worth_doing
  next_actions: NextActionView[]; // separate support decision
  can_wait_summary?: CanWaitSummary;
  presentation: PresentationPlan;
};
```

## Deliverables

- [x] `EnigmaClient` interface + `EnigmaEvent` union
- [x] `DemoEnigmaClient` + `MockEnigmaClient`
- [x] `useEnigmaClient()` / `EnigmaProvider`

**Hard depends:** C01  
**Soft depends (~):** C00
