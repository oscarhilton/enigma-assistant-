# UI2-07 — Real pilot (P03 calendar dogfood)

| Field | Value |
| --- | --- |
| Status | `todo` |
| Branch | `ticket/UI2-07-real-pilot` |
| Domain | `ui2` |
| Programme | [UI2](./README.md) |

## Package boundary (hard)

- May edit: `apps/web/src/v2/**`
- Must not edit: P03 hardware proof worker paths (#89)
- Must not close P03

## Hard depends

- UI2-01 v2 shell
- P03 calendar read support (`in_progress`)

## Frozen spec (launchpad)

**Product:** Make safe agency feel obvious, bounded, and delightful.

## Acceptance criteria

- [ ] My Enigma v2 conversation uses live calendar READ when P03 connected
- [ ] Calendar provenance accessible from minimal inspect sheet (UI2-05)
- [ ] Dogfood checklist for Oscar daily use documented in ticket

## Test plan

- Integration test against P03 fixtures when API available
- Graceful quiet state when no calendar connected

## Privacy constraints

- Calendar READ only; no writes
- Private world storage isolation (ADR-005)
