# C31 — Goose work projection and proactivity timing

**Status:** todo  
**Branch:** `ticket/C31-goose-work-projection-and-proactivity`  
**Domain:** conversational-ui  
**May edit:** `apps/web/src/enigma/courier.ts`, `apps/web/src/enigma/EvidenceCourier.tsx`, `apps/web/src/enigma/ConversationViewport.tsx`, `apps/web/src/styles.css`, `apps/web/src/enigma/*.test.ts*`, `docs/adr/034-evidence-coverage-bundle.md`, `docs/architecture/conversational-stream.md`, `tickets/conversational-ui/**`

**Must not edit:** core work scheduling, retry policy, escalation policy, interruption policy, or authority decisions

**Hard depends:** [C28](./C28-event-spine-agent-work.md) · [C30](./C30-brain-cortex-case-file.md)  
**Soft (~):** [C24](./C24-read-only-evidence-worker.md)

## Goal

Render bounded agent work as THE Goose without allowing presentation to drive the system.

Core state drives Goose state. GooseCargo is a presentation projection of EvidenceBundle / work-state, not a memory store ([shadows-and-machine.md](../../docs/architecture/shadows-and-machine.md)). Holding is not remembering. Visibility: You / Assistant / Goose / Cases on the surface; Engine Room is inspectable, not a new cast ([north-star.md](../../docs/architecture/north-star.md)). Humour constitution: [ADR-038](../../docs/adr/038-humour-constitution-not-user-trainable.md). Do not implement Goose UI in C33.

## Deliverables

- [ ] Deterministic Goose presentation states derived from real work/evidence state
- [ ] Plain-language and accessibility fallback with identical semantics
- [ ] Humour budget rules: frequent visibility, occasional banter, rare elaborate bit
- [ ] Tests prove Goose state never drives retries, work start, or interruption timing

## Definition of done

THE Goose makes agency legible and delightful while remaining fully removable and architecturally powerless.
