# C30 — Brain, Cortex, and Case File projections

**Status:** todo  
**Branch:** `ticket/C30-brain-cortex-case-file`  
**Domain:** conversational-ui  
**May edit:** `apps/web/src/enigma/cortex/**`, `apps/web/src/enigma/ConversationViewport.tsx`, `apps/web/src/enigma/types.ts`, `apps/web/src/enigma/forensicDump.ts`, `apps/web/src/styles.css`, `apps/web/src/enigma/*.test.ts*`, `docs/architecture/conversational-stream.md`, `docs/architecture/cortex-visualizer.md`, `docs/architecture/conversational-ui.md`, `tickets/conversational-ui/**`

**Must not edit:** backend authority decisions from the UI · capsule truth boundaries

**Hard depends:** [C26](./C26-grounded-assertions-epistemics.md) · [C28](./C28-event-spine-agent-work.md) · [C29](./C29-life-memory-and-retention.md) MemoryInventory (slice 4)  
**Soft (~):** [C10](./C10-cortex-brain-visualizer.md)

## Goal

Project one serious substrate into three inspectable views:

- Brain: what Enigma remembers and why
- Cortex: what Enigma is doing and why
- Case File: what this thread is about

C29 `MemoryInventory` is the Brain read model. Compile from it; do not invent a second store. Inventory absence is **not** proof that GC ran: the projector also hides elapsed-TTL rows before `expire_ttl()`, while descendants may still sit in `derived_records`. Forget is SQL DELETE. **The vault remembers. The inventory explains.**

## Deliverables

- [ ] Brain projection over retained assertions and retention metadata
- [ ] Cortex projection over event lineage and evidence flow
- [ ] Case File projection over structured case state plus user-authored content
- [ ] Tests prove these are compiled views, not rival truth stores

## Definition of done

Users can inspect memory, activity, and case progress without the UI inventing a second ontology.
