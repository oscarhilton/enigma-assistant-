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

- UI2 stack merged: #113 shell → #115 streaming → #118 shadcn + continuity → #114 semantic forensics (landed via [#122](https://github.com/oscarhilton/enigma-assistant-/pull/122))
- UI2-04 conversation continuity (~)
- P02 Life Scripts (`done`)

## Frozen spec (launchpad)

**Fossil policy** — matching v1 behaviour not required unless Life Script says so.

## Fossil policy (UI2-fossil-hunt)

**Sidebar thread title after Forget:** POLICY-OK — title is the **first user utterance** (dialogue label frozen at thread creation), not a projection of retained memory. It is not sent to the context compiler or used to regenerate assistant truth. The Forget life script (`forget.yaml`) forbids Cases and Why from treating forgotten facts as current; transcript and sidebar label may still echo what was said.

**Checkpoint jump:** wholesale conversation replace must reconcile sidebar title — otherwise a prior thread label (e.g. ceramics) survives as an unjustified derivative after Alex Lab time-machine reset.

**Freeze bar:**

> Every constitutional Life Script must work in UI2, and every failure must produce a useful forensic snapshot without requiring console archaeology.

When a Life Script fails, one copied forensic bundle (Safe / Detailed / Local) should explain why — diagnosable by construction. Debug dimension: captured state only, never invented missing state (see [README invariants](./README.md#constitutional-invariants)).

## Five constitutional Life Scripts

Replay P02 scripts through `/v2` (Alex Lab world). Fixtures live under `apps/web/src/pilot/life-scripts/`.

| Script | Fixture | What v2 must prove |
| --- | --- | --- |
| **Brunch** | `brunch` / P02a | Calendar hold ≠ booking — talked about ≠ booked |
| **Monday/Maya** | `monday_maya.yaml` | Challenge premise without inventing truth |
| **HONK HONK** | `honk_honk.yaml` | Relationship continuity (C34 expressiveness survives UI boundary) |
| **FALSE VICTORY** | `verification_failure.yaml` | Streaming/Goose cannot imply success — acting ≠ completed |
| **Forget** | `forget.yaml` | No resurrection after forget |

Plus **world switching and thread isolation**: Alex Lab ↔ My Enigma must not leak threads, messages, or Goose state across worlds.

## Acceptance criteria

- [x] **Brunch** — unresolved brunch → “what did I book?” → calendar hold ≠ reservation; Goose/Why honest
- [x] **Monday/Maya** — bank holiday discovery, QUALIFIES premise, no invented truth
- [x] **HONK HONK** — recognition → serious frame suppression → recovery through v2 shell
- [x] **FALSE VICTORY** — PREPARE → APPROVE → ACTING → VERIFYING → fail; prose/Goose must not imply Done
- [x] **Forget** — retain → recall → forget → no resurrection in conversation surface
- [x] World switch isolates thread history (ADR-040); GOOSE_01 isolation on world switch
- [x] Browser-level product tests live under `apps/web/src/v2/`
- [x] Any script failure: ⌘⇧D → Copy produces a forensic bundle that explains the failure without console archaeology

## Development loop

1. Oscar opens `/v2`
2. Goose moves, something streams
3. Something weird happens
4. ⌘⇧D → Copy (Safe / Detailed / Local)
5. Paste for diagnosis

Agents implementing UI2-06 should be able to reproduce and diagnose failures through this loop alone.

## Test plan

- Port P02 assertions to v2 route (`/v2` + Alex Lab world)
- Reference v1 tests: `BrunchProduct.test.tsx`, `MondayMayaProduct.test.tsx`, `HonkHonkProduct.test.tsx`, `VerificationFailureProduct.test.tsx`, `ForgetProduct.test.tsx`
- WORLD_SWITCH parity: thread list and active thread scoped per world; refresh within same world preserves thread
- Goose GOOSE_01 isolation on world switch
- Forensic smoke: force a known failure, copy bundle includes Build / World / Turn / Privacy level and explains mismatch

## Privacy constraints

- Alex Lab only for synthetic scripts; My Enigma not used for Life Script replay
