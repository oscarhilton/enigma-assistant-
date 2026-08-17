# ADR-019: Delegated authority and execution ladder

## Status

Accepted

## Date

2026-08-17

## Context

Permission to **communicate** across the trust boundary ([ADR-013](./013-inter-enigma-coordination-trust-boundary.md)) is separate from permission to **commit** or **execute** world-state changes. The conversational UI already routes "structured Assist → approval / action" ([conversational-ui.md](../architecture/conversational-ui.md), ticket [C07](../../tickets/conversational-ui/C07-assist-proposals.md)) but had no formal authority ladder. This ADR establishes the **canonical Assist authority model (A0–A5)** for local and cross-boundary actions. It extends — does not conflict with — existing Assist proposal types in `apps/web/src/enigma/types.ts`.

Coordination proposals, disclosure answers, and calendar writes must map to explicit rungs.

## Decision

### Authority ladder (capability-specific, never global)

| Rung | Name | Typical scope |
| --- | --- | --- |
| **A0** | Inspect / navigate | Read local state for user; no external effects |
| **A1** | Local reversible | Drafts, local tags, reversible local edits |
| **A2** | External reversible | Send preview-only or revocable external side effects |
| **A3** | Communication with preview | Emit signed protocol envelope **after user sees structured preview** |
| **A4** | Consequential — explicit approval | Spending, cancellation, binding accept, wide disclosure |
| **A5** | Bounded delegated autonomy | Auto-act within pre-approved capability + budget ([ADR-018](./018-disclosure-ledger-and-inference-attack-protection.md)) |

Authority is **capability-specific**: A5 for `availability.query` among teammates does not imply A5 for `shared_task.propose` or spending.

### Examples

| Scenario | Rung |
| --- | --- |
| Auto-answer team availability within work hours | A5 (with ledger budget) |
| Negotiate meeting times within work-hour bounds | A5 negotiate / A3 send counter |
| Cancel existing commitments automatically | **Never** below A4 |
| Prepare procurement counterproposal | A1–A3 draft; A4 to send |
| Spending | **Always A4** minimum |

### Execution lifecycle

World-state mutations follow:

```text
PROPOSED → APPROVED → EXECUTING → VERIFIED
```

- **PROPOSED:** Assist or coordination layer drafts action.
- **APPROVED:** Human or delegated policy at required rung.
- **EXECUTING:** Side effect in flight (send envelope, write calendar).
- **VERIFIED:** Outcome confirmed; only then treat world model as updated.

Incoming remote messages do not skip to VERIFIED ([ADR-016](./016-bilateral-consent-and-shared-commitments.md)).

### Mapping to coordination

| Action | Minimum rung |
| --- | --- |
| Draft dinner PROPOSE locally | A1 |
| Send PROPOSE envelope | A3 |
| Accept shared commitment | A4 |
| Auto-reply availability ASK within budget | A5 |
| First ASK from unknown identity | A4 |

## Consequences

- C07 Assist proposal UI implements A3/A4 surfaces for Demo; coordination tickets reuse the same approval chrome.
- API routes must not send envelopes or mutate commitments without policy check at rung.
- Demo Assist stubs remain Demo-only; no Private key use ([ADR-005](./005-demo-private-storage-roots.md)).
- Shareable recipes ([ADR-024](./024-shareable-recipes-procedure-never-personal-state.md)) execute on this same ladder: each recipe step declares a minimum rung; recipes cannot skip PROPOSED → APPROVED → EXECUTING → VERIFIED or collapse grants into a global “trust recipes” toggle. Recipe runtime is **not** authorised by this ADR.

## Alternatives considered

| Alternative | Why rejected |
| --- | --- |
| Binary "auto vs ask" | Too coarse for communication vs commit vs spend. |
| OAuth scope strings only | Describes access not execution; misses preview and verify steps. |
| Remote Enigma approves on behalf of user | Violates bilateral consent ([ADR-016](./016-bilateral-consent-and-shared-commitments.md)). |
| Single global "trust Enigma" toggle | Fails capability-specific and cumulative disclosure needs. |

## References

- [ADR-013](./013-inter-enigma-coordination-trust-boundary.md) · [ADR-016](./016-bilateral-consent-and-shared-commitments.md) · [ADR-017](./017-cryptographic-identity-signed-envelopes-and-encrypted-relay.md) · [ADR-018](./018-disclosure-ledger-and-inference-attack-protection.md)
- [conversational-ui.md](../architecture/conversational-ui.md) · [C07](../../tickets/conversational-ui/C07-assist-proposals.md)
- [enigma-coordination-protocol.md](../architecture/enigma-coordination-protocol.md)
- [ADR-024](./024-shareable-recipes-procedure-never-personal-state.md) · [shareable-recipes.md](../architecture/shareable-recipes.md) · [REC00](../../tickets/recipes/REC00-shareable-recipes-north-star.md) (`future`)
