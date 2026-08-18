# C37 — Goose pixel observation (dogfood idle / walk / return)

**Status:** in_progress  
**Branch:** `ticket/C37-goose-pixel-observation`  
**Domain:** conversational-ui  
**Hard depends:** [C35](./C35-goose-pixel-licence.md) done · [C34](./C34-relational-bootstrap.md) frozen  
**Soft (~):** C12 Life Script runner (not on this main) · C28 AgentWork spine (not on this main) · C31 choreography (not this slice)

This is **not C36**. C36 is reserved conceptually for invention (new motions, Shadows, speech, affection). C37 only instruments the three existing steps and captures observations.

## Scope (package boundary)

- `apps/api/src/personal_enigma/api/goose_observation.py`
- `apps/api/src/personal_enigma/api/goose_pixels.py` (no new motions)
- `apps/api/tests/test_c37_goose_pixel_observation.py`
- `apps/api/tests/fixtures/goose_observation/captured/*.yaml`
- `packages/evaluation/scripts/goose_pixel_observation/*.script.yaml` (new scripts only)
- `apps/web/src/enigma/gooseTelemetry.ts`
- `apps/web/src/enigma/gooseTelemetry.test.ts`
- `apps/web/src/enigma/GoosePresence.tsx` · `GoosePresence.test.tsx` (inspect / visibility telemetry)
- `apps/web/src/pages/HomePage.tsx` (local telemetry wire only)
- this ticket · `tickets/conversational-ui/README.md` row
- `docs/architecture/conversational-ui.md` (observation freeze note)

**Must not edit:** C34 `relational_bootstrap.py` · `alex_jan19_continuity_integrity.script.yaml` (C23 frozen; not on this main) · styles.css sprite vocabulary · Cortex / Memory / Sources · Shadows / cargo · speech · affection · C31 courier · C09 tools

## Freeze: observation before invention

`possible_fix: NOT YET` is constitutional for this slice. Do not invent `WAITING_GOOSE_WITH_NEWSPAPER.gif`. Do not add motions. Do not start C36.

Capture format:

```
scenario: waiting_external
observed:
  goose_state: idle
  user_interpretation: "looks finished"
problem: true
severity: medium
possible_fix: NOT YET
```

## Telemetry: meaning, not engagement

Allowed: `goose_became_visible` · `goose_motion_started` · `goose_returned` · `goose_inspected` · `agent_work_changed` · `frame_expression_changed`

Forbidden: `goose_clicked_17_times` · `goose_engagement_score` · `user_affection` · `daily_goose_retention`

Derived questions:

- Did the Goose move when AgentWork moved?
- Did it remain still when nothing semantic changed?
- When inspected, did the explanation match what the animation implied?
- Did frame changes alter only presentation?

Local SURFACE log only. Never attach to the remote working set.

## Life Scripts (7) + constitutional nasty test

New YAML under `packages/evaluation/scripts/goose_pixel_observation/`. Speaks like Alex. Projects **C35** `AgentWorkSnapshot` + C34 frame through `license_goose_pixels`. Not C23. C12 `DemoSession` runner is not on this main — these scripts are the smallest real-life projection of idle / walk / return.

| Script | Intent |
| --- | --- |
| `simple_retrieval` | ask → work starts → walk → result → return |
| `waiting_external` | genuine wait → must not imply active movement |
| `multi_step_work` | investigate → advance → verify; three-state Goose stays truthful |
| `serious_disclosure` | playful → serious frame; presence unchanged, theatricality suppressed |
| `no_work` | conversation continues → no performative waddling |
| `failure` | work fails → sprite must not falsely suggest success |
| `inspect` | click mid-work / after return → existing Why matches animation |
| `false_victory` | **FALSE VICTORY TEST** (constitutional) |

### FALSE VICTORY TEST

AgentWork truth: ACTING → VERIFYING → verification fails.

C35 vocabulary on this main is only `in_flight` / `waiting` / `complete` → `walk` / `idle` / `return`. Failed verification currently lands on `complete` → `return`.

Goose must not perform anything reasonably read as “job successfully completed”. `return` already means “I have returned with a result” and must not automatically mean “The mission succeeded.” Observe that. Do not invent a failure dance.

## Acceptance

- [x] Ticket is this observation / dogfood slice (not C36)
- [x] Seven Life Scripts + FALSE VICTORY, new files only
- [x] Telemetry allowlist / denylist tests
- [x] Captured observations with `possible_fix: NOT YET`
- [x] No new animations, Shadows, speech, affection, wandering
- [x] Tests named below

## Test plan

```bash
uv run pytest apps/api/tests/test_c37_goose_pixel_observation.py -q
uv run ruff check apps/api/src/personal_enigma/api/goose_observation.py apps/api/tests/test_c37_goose_pixel_observation.py
uv run basedpyright apps/api/src/personal_enigma/api/goose_observation.py
pnpm --filter @personal-enigma/web test
pnpm --filter @personal-enigma/web typecheck
```

## Non-goals / deferred

C36 invention · new GIF vocabulary · Shadows / cargo · satchel · speech · affection · C28 lifecycle names as runtime · C31 courier · C23 continuity integrity · always-on mascot chrome

## Privacy

Goose telemetry is a local SURFACE log. It must not enlarge the remote model’s view. Do not attach sprite state or click streams to the compiled remote working set.
