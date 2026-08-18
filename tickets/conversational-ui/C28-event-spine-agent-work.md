# C28 — Event spine and agent-work lifecycle

**Status:** done · **frozen** (substrate `9e72ad2`, integration bridge complete)  
**Branch:** `ticket/C28-event-spine-agent-work`  
**Domain:** conversational-ui  
**May edit:** `apps/api/src/personal_enigma/api/demo_orchestrator.py`, `apps/api/src/personal_enigma/api/routes/demo.py`, `apps/web/src/enigma/activity.ts`, `apps/web/src/enigma/cortex/events.ts`, `apps/web/src/enigma/cortex/mapEvents.ts`, `apps/api/tests/test_c28_*.py`, `apps/web/src/enigma/*.test.ts*`, `docs/architecture/conversational-stream.md`, `docs/architecture/cortex-visualizer.md`, `tickets/conversational-ui/**`

**Must not edit:** private-world truth rules · execution ledger semantics owned by [C17](./C17-execution-receipts-verification-ledger.md)

**Hard depends:** [C26](./C26-grounded-assertions-epistemics.md) · [C27](./C27-handoff-turn-contract.md)  
**Soft (~):** [C14](./C14-conversation-activity-stream.md) · [C24](./C24-read-only-evidence-worker.md)

## Goal

Make events the causal wakeups for agent work and keep execution, verification, and interruption policy explicit.

## Deliverables

- [x] Typed `source.*`, `evidence.*`, `world.*`, `attention.*`, `conversation.*`, `work.*`, `assist.*`, and `effect.*` event vocabulary (DemoSession semantic spine)
- [x] Agent-work lifecycle states such as `DETECTED`, `INVESTIGATING`, `WAITING_EXTERNAL`, `READY_FOR_USER`, `VERIFYING`, `HANDLED`
- [x] Clear separation between execution start and verified external effect
- [x] Tests cover idempotency and causal lineage (substrate + integration bridge)
- [x] **Integration bridge:** `assist.approve` in `demo_tools` / orchestrator delegates to `DemoSession.start_assist_execution` → `verify_assist_effect` (no direct world mutation bypass)

## Definition of done

The system can answer “why are you bringing this up?” with causal state transitions rather than “the AI thought it was relevant.”

## Freeze notes

- Substrate semantics frozen at `9e72ad2` — do not reopen event/work-state/authority models on this ticket.
- `READY_FOR_USER` does **not** couple to notify-now / attention surfacing.
- Legacy `assist.approve` without an `AssistEventSpine` host cannot produce consequential world updates.
- `/demo/assist/{id}/approve` and orchestrator `assist.approve` both route through the same spine.

## Deferred (follow-on tickets)

- Web activity / Cortex event projection (`apps/web/src/enigma/activity.ts`, `cortex/events.ts`, `mapEvents.ts`) → [C30](./C30-brain-cortex-case-file.md) / [C31](./C31-goose-work-projection-and-proactivity.md)
- Broader non-assist ingestion paths emitting `source.*` / `evidence.*` in live demo flows
- Full execution receipt ledger → [C17](./C17-execution-receipts-verification-ledger.md)
