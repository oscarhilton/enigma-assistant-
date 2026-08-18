# C39 — Handoff working conclusion (compiled view, not stored state)

**Status:** future  
**Branch:** `ticket/C39-handoff-working-conclusion`  
**Domain:** conversational-ui  
**Package boundary (docs capture):** `docs/architecture/conversational-ui.md`, `docs/adr/029-context-compilation-request-shaped-memory.md`, `tickets/conversational-ui/**`, optional ADR amendment if handoff constitution needs a dedicated record  
**Package boundary (implementation — do not start):** `packages/domain/src/personal_enigma/domain/**` (handoff / working-conclusion types), `apps/api/src/personal_enigma/api/context_compilation.py`, `apps/api/src/personal_enigma/api/conversation_context.py`, `apps/api/src/personal_enigma/api/demo_orchestrator.py`, `apps/api/tests/test_c39_*.py`

**Hard depends:** [C27](./C27-handoff-turn-contract.md) handoff + turn contract substrate landed  
**Soft (~):** [C26](./C26-grounded-assertions-epistemics.md) · [C25](./C25-evidence-coverage-bundle.md) · [C38](./C38-shared-uncertainty-collapse.md) (`dependency_resolved` semantic result) · PILOT-01

**Unlocks / enhances:** Agent replacement and multi-step jobs without transcript-as-truth; Telephone Test continuity — **after** unpark only.

## Parked

```text
C27 Handoff  →  pilot multi-step jobs  →  unpark C39 implementation
```

Do **not** implement now. No `ReasoningPayloadService`. Documentation capture below is the whole current scope.

## Frozen constitution

The **working conclusion** is a **compiled view, not stored state**.

| Layer | Question it answers |
| --- | --- |
| **EvidencePack** | What may I believe? |
| **Turn contract** | What are we trying? |
| **Relational bootstrap** ([C34](./C34-relational-bootstrap.md)) | How does conversation work? |
| **Handoff** | What understanding does the next step inherit? |

Rules:

1. **Pass the conclusion. Preserve the evidence. Discard the deliberation.**
2. A downstream agent may inherit **understanding** from a handoff. It must inherit **truth** from evidence.
3. Reasoning text may compress justified interpretation; it may **not** become evidence merely because another agent received it.
4. **Never** derive durable memory from another agent's prose ([ADR-029](../../docs/adr/029-context-compilation-request-shaped-memory.md)).
5. Belongs on **Handoff**, not EvidencePack.

### Example handoff shape (illustrative)

```yaml
handoff:
  resolved:
    - question: "Has brunch been booked?"
      answer: "No restaurant reservation has been established."
      basis: [...]  # evidence handles / assertion IDs — not deliberation prose
  unresolved:
    - question: "Which Sunday slot works for Elena?"
      blockers: [...]
```

### Constraints

- Ephemeral, purpose-bound, evidence-linked
- Non-authoritative (recomputable when evidence changes)
- Explicit about unresolved uncertainty
- Replaceable — invalidate underlying evidence → recompile; prose alone cannot sustain the claim

### Acceptance tests (design-level)

**Telephone Test:** Agent B continues from `resolved` + `basis` + `unresolved` without Agent A's deliberation transcript.

**Fossil Test:** Invalidate underlying evidence → the handoff conclusion cannot establish the claim; recompilation required.

## Connection to shared-dependency resolution

When [C38](./C38-shared-uncertainty-collapse.md) resolves a shared epistemic dependency, the handoff carries the **semantic result** (e.g. Event Spine `dependency_resolved` / Q17-style payload: question, grounded answer, basis, remaining unknowns) — not the investigation dialogue.

## Non-goals (must not)

- **No** `ReasoningPayloadService` or new persistence service for deliberation
- **No** storing working conclusions as durable vault memory
- **No** putting working conclusions on EvidencePack (evidence ≠ compiled interpretation)
- **No** epistemic backchannel — handoff is not a covert truth channel between agents
- **No** implementation in this ticket slice (spec only)

## Acceptance criteria (implementation — after unpark)

Tests TBD when pilot exposes handoff failure modes. Directional criteria:

- [ ] Handoff wire shape includes `resolved[]` and `unresolved[]` with evidence-linked `basis` on every resolved item
- [ ] Deliberation / chain-of-thought never serialised into handoff or durable storage
- [ ] **Telephone Test** passes: model replacement continues job from handoff + evidence only
- [ ] **Fossil Test** passes: evidence invalidation forces conclusion drop / recompile
- [ ] Handoff, turn contract, capsule, and evidence remain distinct on the wire ([C27](./C27-handoff-turn-contract.md))
- [ ] Shared dependency resolution ([C38](./C38-shared-uncertainty-collapse.md)) populates handoff `resolved` without duplicating investigation

## Test plan (after unpark)

- Compile handoff from fixture evidence + investigation outcome → assert no deliberation fields
- Drop evidence assertion → handoff `resolved` entry invalidated or removed on recompile
- Agent B fixture: given handoff + evidence pack only, completes next step (Telephone Test)
- Negative: prose-only “answer” without `basis` → rejected at compile time

## Privacy constraints

- Handoff egress follows context compilation ([ADR-029](../../docs/adr/029-context-compilation-request-shaped-memory.md)): request-shaped, minimal, no biography reconstruction
- `basis` references governed assertions ([C26](./C26-grounded-assertions-epistemics.md)); no raw mail bodies in handoff

## Related

- [C27 — Handoff and turn contract](./C27-handoff-turn-contract.md)
- [C38 — Shared uncertainty collapse](./C38-shared-uncertainty-collapse.md)
- [C34 — Relational bootstrap](./C34-relational-bootstrap.md)
- [C25 — Evidence coverage bundle](./C25-evidence-coverage-bundle.md)
- [ADR-029 — Context compilation](../../docs/adr/029-context-compilation-request-shaped-memory.md)
- [C28 — Event spine](./C28-event-spine-agent-work.md)
