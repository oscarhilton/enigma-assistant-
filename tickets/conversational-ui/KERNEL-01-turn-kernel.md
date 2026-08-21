# KERNEL-01 — Shared turn kernel (Demo + My Enigma)

| Field | Value |
| --- | --- |
| Status | `done` |
| Branch | `ticket/kernel-01-turn-kernel` |
| Domain | `conversational-ui` |
| Programme | Shared conversation turn path (Alex Lab + My Enigma) |

**Partial.** First stacked PR extracts the shared kernel and tool wiring; exit criteria below remain open.

## Intent

One turn execution path for Demo and Private worlds:

`interpret → plan tools → execute → compile outcome / forensic trace`

so My Enigma and Alex Lab cannot diverge on planner, privacy gates, or calendar gravity.

## Soft depends (~)

- [P03 calendar READ/SUPPORT](../pilot/P03-calendar-read-support.md) / PR [#126](https://github.com/oscarhilton/enigma-assistant-/pull/126) (`ticket/p03-forensic-calendar-gravity`) — forensic binding + CALENDAR_GRAVITY base; **must not extend #126** with kernel commits (stack on top instead).

Soft only: kernel work can proceed on the stacked branch; merge order prefers #126 first.

## Package boundary

- `apps/api/src/personal_enigma/api/turn_kernel.py`
- `apps/api/src/personal_enigma/api/private_conversation.py`
- `apps/api/src/personal_enigma/api/routes/demo.py`
- `apps/api/src/personal_enigma/api/routes/worlds.py` (agent_work from `turn_outcome`)
- `apps/api/src/personal_enigma/api/demo_tools.py` / `private_tools.py` (tool aliases only as needed by kernel)
- `apps/api/src/personal_enigma/api/intent_router.py` (period-briefing regressions frozen for kernel)
- `apps/api/src/personal_enigma/api/demo_intents.py` (horizon copy contract)
- `apps/web/src/enigma/activity.ts` / `apps/web/src/v2/debug/forensicTurn.ts` (tool name maps)
- `apps/api/tests/test_turn_kernel.py`, `test_period_briefing.py`, `test_gravity_integration.py`, and related conversation/P03 updates

**Out of scope for this ticket:** RESPOND-01, proactive BRIEF-01 consumer, Phase 0 cloud-agent scaffolding.

## Done in partial PR (this branch)

- [x] New `turn_kernel.py` shared by Demo + Private entrypoints
- [x] `private_conversation` wiring through `run_private_turn` / kernel
- [x] `demo.py` `run_alex_turn` wiring
- [x] `briefing.read` + `calendar.agenda.get` on demo/private tools
- [x] Intent router period-briefing regex (BRIEF-01 frozen regressions that support kernel)
- [x] Demo horizon copy contract (`demo_intents`)
- [x] `worlds.py` agent_work labels from `turn_outcome`
- [x] Web activity / forensicTurn tool name maps
- [x] Tests: `test_turn_kernel`, `test_period_briefing`, `test_gravity_integration` (six-turn privacy/gravity gate as **kernel safety invariant**), plus C09 / demo context / P03 updates

## Remaining exit conditions

- [x] My Enigma conversation path fully through `interpret_request` (no parallel private-only interpret fork)
- [x] Compiler / oracle alignment for turn outcomes
- [x] Removal of `_route_private_tool` (or equivalent private-only router leftover)
- [x] Routing / privacy tests covering the full kernel contract beyond the six-turn gate

## Explicit non-goals (this run)

- Do **not** start RESPOND-01
- Do **not** start the proactive BRIEF-01 consumer
- Do **not** fold Phase 0 cloud-agent scaffolding into the KERNEL PR

## Test plan

```bash
uv run pytest \
  apps/api/tests/test_turn_kernel.py \
  apps/api/tests/test_period_briefing.py \
  apps/api/tests/test_gravity_integration.py \
  apps/api/tests/test_p03_calendar_read_support.py \
  apps/api/tests/test_demo_conversation_context.py \
  apps/api/tests/test_c09_conversation_benchmark.py
```

## PR

- Partial KERNEL-01 stacked on `ticket/p03-forensic-calendar-gravity` (base ≠ `main`)
