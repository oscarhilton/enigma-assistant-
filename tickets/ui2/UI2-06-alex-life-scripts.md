# UI2-06 — Alex Life Scripts through v2

| Field | Value |
| --- | --- |
| Status | `done` |
| Branch | `ticket/UI2-06-alex-life-scripts` |
| Domain | `ui2` |
| Programme | [UI2](./README.md) |

## Package boundary (hard)

- May edit: `apps/web/src/v2/**`
- May edit: `apps/web/src/v2/**/*.test.tsx`
- May reuse: `apps/web/src/pilot/life-scripts/**` (read-only fixtures)
- Must not edit: P02 product test files in v1 pilot

## Hard depends

- UI2-01 v2 shell
- UI2-04 conversation continuity (~)
- P02 Life Scripts (`done`)

## Frozen spec (launchpad)

**Fossil policy** — matching v1 behaviour not required unless Life Script says so.

## Fossil policy (UI2-fossil-hunt)

**Sidebar thread title after Forget:** POLICY-OK — title is the **first user utterance** (dialogue label frozen at thread creation), not a projection of retained memory. It is not sent to the context compiler or used to regenerate assistant truth. The Forget life script (`forget.yaml`) forbids Cases and Why from treating forgotten facts as current; transcript and sidebar label may still echo what was said.

**Checkpoint jump:** wholesale conversation replace must reconcile sidebar title — otherwise a prior thread label (e.g. ceramics) survives as an unjustified derivative after Alex Lab time-machine reset.

## Acceptance criteria

- [x] Brunch script passes through v2 UI
- [x] Monday/Maya script passes
- [x] HONK HONK script passes (C34 expressiveness)
- [x] FALSE VICTORY (verification failure) script passes
- [x] Forget script passes
- [x] Browser-level product tests live under `apps/web/src/v2/`

## Test plan

- Port P02 assertions to v2 route (`/v2` + Alex Lab world)
- Goose GOOSE_01 isolation on world switch

## Privacy constraints

- Alex Lab only for synthetic scripts; My Enigma not used for Life Script replay
