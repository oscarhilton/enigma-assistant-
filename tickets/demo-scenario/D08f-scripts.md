# D08f-scripts — Life Scripts for significant days (not C11)

| Field | Value |
| --- | --- |
| Status | `todo` |
| Branch | `ticket/D08f-scripts` |
| Domain | `demo-scenario` (YAML) / evaluation scripts |
| Parent | [D08f](./D08f-alex-six-month.md) |

## Package boundary (hard)

- May edit: `packages/evaluation/scripts/alex_feb12_running_late.script.yaml`, `alex_mar03_waiting_on_reply.script.yaml`, `alex_apr18_quiet_day.script.yaml`, `alex_may07_old_thread_returns.script.yaml`, `alex_jun30_what_do_you_remember.script.yaml`
- May edit: `packages/evaluation/tests/test_life_scripts.py` (register new scripts), `tickets/conversational-ui/C12-life-scripts.md` (library list)
- Must not edit: C09 production tool registry, `intent_router.py`, C11 tone store, SEC-07 attacker, `packages/ingestion/**`, monthly timeline files (those are D08f-02…06)

## Hard depends

- [C12](../conversational-ui/C12-life-scripts.md) format + runner (landed)
- Matching month source events for each episode (soft per-script: author the script after that month’s events exist)

## Soft depends (~)

- [C13](../conversational-ui/C13-life-script-reliability.md) — same YAML, later reliability; do not block
- [C11](../conversational-ui/C11-tone-memory.md) — **do not implement**; June/Apr scripts may *observe* public tone only if C11 is already unparked

## Unlocks / enhances

- Vertical depth on a six-month horizontal corpus
- `alex_jun30_what_do_you_remember` as the conversational face of SEC-06 inventory (not the SEC-07 attacker)

## Non-goals

- `alex_week_03.yaml` (still later C12)
- UI `▶ Run Alex` player
- C11 implementation
- Expanding phrase families
- Implementing forget/decay pipelines

## Episodes

| Script | Clock | Depends on month |
| --- | --- | --- |
| `alex_feb12_running_late` | 2026-02-12 | [D08f-02](./D08f-02-february.md) |
| `alex_mar03_waiting_on_reply` | 2026-03-03 | [D08f-03](./D08f-03-march.md) |
| `alex_apr18_quiet_day` | 2026-04-18 | [D08f-04](./D08f-04-april.md) |
| `alex_may07_old_thread_returns` | 2026-05-07 | [D08f-05](./D08f-05-may.md) |
| `alex_jun30_what_do_you_remember` | 2026-06-30 | [D08f-06](./D08f-06-june.md) |

Frozen C12 rules apply: speak like Alex; assert public effects; no router internals.

## Acceptance criteria

- [ ] Each episode is embarrassingly readable YAML in the C12 format
- [ ] Deterministic pytest coverage (skip/defer turns that are not on the v1 surface — same as Jan 19)
- [ ] `alex_jun30_what_do_you_remember` uses inspect/forget **public** capabilities if present; otherwise `v1: deferred` — do not fake SEC-07
- [ ] No `ALEX_BIOGRAPHY.md`; scripts do not dump six months of recap as user turns

## Test plan

```bash
uv run pytest packages/evaluation/tests/test_life_scripts.py
uv run enigma-eval --life-script alex_feb12_running_late
```

## Privacy constraints

- Fictional Alex only. June inspect must not print raw mail bodies into the transcript assertion.
