# C26 — Grounded assertions, epistemic status, and challenge/reconciliation

**Status:** done (frozen response-grounding bridge checkpoint `8ada705`)  
**Branch:** `ticket/C26-grounded-assertions-epistemics`  
**Domain:** conversational-ui  
**May edit:** `packages/domain/src/personal_enigma/domain/grounding.py` (new), `packages/domain/src/personal_enigma/domain/__init__.py`, `packages/domain/tests/test_grounding.py` (new), `apps/api/src/personal_enigma/api/evidence_bundle.py`, `apps/api/src/personal_enigma/api/respond_grounding.py`, `apps/api/tests/test_c26_*.py`, `docs/adr/035-*.md`, `docs/architecture/enigma-master-gap-analysis.md`, `tickets/conversational-ui/**`

**Must not edit:** `ConversationCapsule` shape · `intent_router.py` phrase families · new product capabilities · retention/forget storage semantics beyond metadata reuse

**Hard depends:** [C25](./C25-evidence-coverage-bundle.md) bundle shape landed enough to extend  
**Soft (~):** [C21](./C21-grounded-values-no-invented-facts.md) · [C24](./C24-read-only-evidence-worker.md)

## Goal

Give Enigma a first-class way to say:

- what do I know?
- how do I know it?
- what is still unknown?
- what evidence merely qualifies a conclusion?

without flattening everything into confidence or transcript residue.

## Deliverables

- [x] `EpistemicStatus`, `GroundedAssertion`, `EvidenceUnknown`, and `AssertionChallenge` canonical models
- [x] `EvidenceBundle` carries proposition-shaped assertions, unknowns, and typed challenges as ephemeral compiled state
- [x] Challenge semantics distinguish `CONFIRMS` / `QUALIFIES` / `CONFLICTS` / `DOES_NOT_ADDRESS`
- [x] Tests cover verified observation, missing evidence, unresolved referent, and useful-but-insufficient evidence

## Definition of done

The repo can represent a verified fact, a plausible hypothesis, a missing fact, and a qualifying challenge without promoting any of them merely because confidence is high.

## Closure notes

- `apps/api/tests/test_c25_evidence_bundle.py`, `packages/domain/tests/test_grounding.py`, and `apps/api/tests/test_c26_respond_grounding_integration.py` are passing at this frozen checkpoint.
- Commit `8ada705` is the response-grounding bridge checkpoint: the respond path consumes canonical `GroundedAssertion` data from `EvidenceBundle` without reopening the orchestrator fence shape in this ticket.
- Deferred hardening, not unfinished C26: richer predicate-to-language mapping for more natural renderings over canonical assertions.
- Explicitly out of scope for this closure pass: continuity implementation, epistemology reopening, and orchestrator double-fence refactors unless a later review proves contradictory behavior.
- Web cleanup was not pulled into C26. The web typecheck remains an existing separate issue in `apps/web/src/enigma/MockEnigmaClient.ts` (`TS2339`: `emit` does not exist on `MockEnigmaClient`).
