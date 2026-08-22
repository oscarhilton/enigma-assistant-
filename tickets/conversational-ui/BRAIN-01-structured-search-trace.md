# BRAIN-01 — Structured search trace

| Field | Value |
| --- | --- |
| Status | `future` |
| Branch | `ticket/BRAIN-01-structured-search-trace` |
| Domain | `conversational-ui` (observability) |

## Package boundary (hard)

- May edit: trace types (Python domain + TS consumer types), tests, docs pointers
- Must not edit: Cortex as control plane; LLM CoT persistence; C10 Three.js scene; world writers

## Hard depends

- [POLARIS-SEARCH-04](../polaris/POLARIS-SEARCH-04-receding-horizon-search.md) `done`

## Soft depends (~)

- C10 Cortex types (do not overload `BrainEvent` with PV nodes without a distinct kind)
- C14 activity stream (public hops ≠ search tree)
- C39 “discard the deliberation”

## Unlocks / enhances

- BRAIN-02; POLARIS-SEARCH-06 artefacts

## Non-goals

- Showing model chain-of-thought
- Click-to-COMMIT
- Restoring C30 Brain memory UI

## Acceptance criteria

- [ ] Typed machine-readable trace: candidates, rejected/pruned reasons, evidence refs, uncertainty, assumptions, principal variation, authority, invalidation triggers ([ADR-048](../../docs/adr/048-structured-search-trace-and-lens.md))
- [ ] No deliberation/CoT/hidden thought fields; reason **codes** not essays
- [ ] Confidence present per ply and fades with depth (from 04)
- [ ] Feeds Lens; Cortex may ignore or show a single “search completed” event — not the tree
- [ ] Round-trip tests; golden dentist-critique trace fixture

## Exit conditions

Done when BRAIN-02 can render from the schema alone (no live model transcript).

## Test plan

- Schema reject unknown `chain_of_thought` / `thinking` keys
- Invalidation trigger list non-empty on blocked-task fixture
- Egress: raw trace must not be the default remote prompt ([ADR-029](../../docs/adr/029-context-compilation-request-shaped-memory.md))

## Privacy constraints

- Trace holds assertion ids, not mail bodies
- Alex Lab first
