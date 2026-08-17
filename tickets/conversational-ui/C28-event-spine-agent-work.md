# C28 — Event spine and agent-work lifecycle

**Status:** todo  
**Branch:** `ticket/C28-event-spine-agent-work`  
**Domain:** conversational-ui  
**May edit:** `apps/api/src/personal_enigma/api/demo_orchestrator.py`, `apps/api/src/personal_enigma/api/routes/demo.py`, `apps/web/src/enigma/activity.ts`, `apps/web/src/enigma/cortex/events.ts`, `apps/web/src/enigma/cortex/mapEvents.ts`, `apps/api/tests/test_c28_*.py`, `apps/web/src/enigma/*.test.ts*`, `docs/architecture/conversational-stream.md`, `docs/architecture/cortex-visualizer.md`, `tickets/conversational-ui/**`

**Must not edit:** private-world truth rules · execution ledger semantics owned by [C17](./C17-execution-receipts-verification-ledger.md)

**Hard depends:** [C26](./C26-grounded-assertions-epistemics.md) · [C27](./C27-handoff-turn-contract.md)  
**Soft (~):** [C14](./C14-conversation-activity-stream.md) · [C24](./C24-read-only-evidence-worker.md)

## Goal

Make events the causal wakeups for agent work and keep execution, verification, and interruption policy explicit.

## Deliverables

- [ ] Typed `source.*`, `evidence.*`, `world.*`, `attention.*`, `conversation.*`, `work.*`, `assist.*`, and `effect.*` event vocabulary
- [ ] Agent-work lifecycle states such as `DETECTED`, `INVESTIGATING`, `WAITING_EXTERNAL`, `READY_FOR_USER`, `VERIFYING`, `HANDLED`
- [ ] Clear separation between execution start and verified external effect
- [ ] Tests cover idempotency and causal lineage

## Definition of done

The system can answer “why are you bringing this up?” with causal state transitions rather than “the AI thought it was relevant.”
