# RECON-06 — Event / action spine (C28 on current main)

| Field | Value |
| --- | --- |
| Status | `future` |
| Branch | `ticket/RECON-06-event-action-spine` |
| Domain | `recon` |

## Package boundary (hard)

- May edit: event-spine / agent-work modules under `apps/api` (current layout, not donor paths), typed event vocabulary in `packages/domain` if required, tests `test_recon06_*` / `test_c28_*`, [conversational-stream.md](../../docs/architecture/conversational-stream.md) pointers, this ticket
- Must not edit: Observatory UI (02); PolarIS search; C38/C39 implementation; vault/retention (RECON-04/05); Life Script YAML rewrite (07)

## Hard depends

- [OBSERVATORY-02](../observatory/OBSERVATORY-02-observatory-ui.md) `done`

## Soft depends (~)

- Historical C28 (`tickets/conversational-ui/C28-event-spine-agent-work.md` at `974d666`) — inspect; file **not** on `main`
- [C14](../conversational-ui/C14-conversation-activity-stream.md) public hops
- Historical C17 execution receipts — if the file is absent, do not fork a second ledger

## Unlocks / enhances

- RECON-07; C38 unpark (still `future` until this lands)

## Intent

Land a **current-main** event / action spine so the system can answer “why are you bringing this up?” with causal transitions. Historical C28 named the slice (`source.*` / `world.*` / `work.*` / `assist.*` / `effect.*`, agent-work lifecycle). This ticket **adapts** that constitution to today’s orchestrator — it does not dump the donor tree.

Polaris already treats Event Spine as the intended stimulus substrate ([polaris-search.md](../../docs/architecture/polaris-search.md)); this ticket supplies it.

## Non-goals

- Wholesale restore of missing C28 / C26 / C27 files
- C38 shared-uncertainty implementation
- Observatory probes (03)
- PolarIS search tree

## Acceptance criteria

- [ ] Typed event vocabulary sufficient for ingest, world change, attention, conversation, work, assist, effect
- [ ] Agent-work lifecycle states explicit (detect → investigate → wait → ready → verify → handled — names may match current enums)
- [ ] Execution start ≠ verified external effect
- [ ] Idempotency + causal lineage tests
- [ ] Observatory registry can mark the spine `IMPLEMENTED`/`WIRED`/`VERIFIED` with evidence refs (not `USABLE` until a user path exists)
- [ ] C38/C39 remain unimplemented

## Exit conditions

Done when RECON-07 can hang Life Scripts on real work events, and Observatory shows the spine edge as present rather than missing.

## Test plan

- Lineage: one stimulus → one work record
- Idempotent re-delivery does not double-handle
- Negative: LLM “thought it was relevant” is not an allowed wakeup reason code

## Privacy constraints

- Events carry assertion / source ids, not wholesale Notes
- Demo/Alex first
