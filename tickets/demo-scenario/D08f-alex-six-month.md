# D08f — Alex six-month ordinary life (programme)

| Field | Value |
| --- | --- |
| Status | `todo` (docs + layout landed; monthly authoring not started) |
| Branch | `ticket/D08f-alex-six-month` |
| Domain | `demo-scenario` |
| Parent | [D08](./D08-canonical-alex.md) |

## Package boundary (hard)

- May edit: `docs/architecture/demo-corpus.md`, `docs/architecture/demo-mode.md`, `docs/architecture/north-star.md`, `docs/architecture/data-retention.md`, `docs/architecture/conversational-ui.md`, `docs/architecture/tone-memory.md`, `docs/architecture/overview.md`, `docs/architecture/milestone-map.md`, `docs/architecture/executive-function-support-benchmark.md`, `docs/demo/reasoning-value-gate.md`
- May edit: `scenarios/alex-v1/timeline/README.md`, `scenarios/alex-v1/timeline/2026-0*/**` (scaffold + one February stub), `scenarios/alex-v1/README.md`, `scenarios/README.md`
- May edit: `tickets/demo-scenario/D08f*.md`, `tickets/demo-scenario/D08-canonical-alex.md`, `tickets/demo-scenario/V2-EF-02-ef-arc-authoring.md`, `tickets/README.md`, `tickets/conversational-ui/C12-life-scripts.md` (library list only)
- May edit: `packages/simulation/tests/test_alex_corpus.py` (0.2.1 January fence only)
- Must not edit: `scenarios/alex-v1/timeline/week-*.yaml` (0.2.1 semantics), `packages/ingestion/**`, C11 tone runtime, SEC-07 attacker, `intent_router.py`, `packages/evaluation/scripts/**` (scripts ticket)

## Hard depends

- [D08](./D08-canonical-alex.md) / [D08a](./D08a-canonical-spine.md) (January spine exists)
- [D03](./D03-scenario-format.md) (source-event format)

## Soft depends (~)

- [C12](../conversational-ui/C12-life-scripts.md) Life Script format (episodes are [D08f-scripts](./D08f-scripts.md))
- [SEC-06](../security/SEC-06-retention-memory-decay-forget.md) (June decay is event + time, not a new forget engine)
- [V2-EF-02](./V2-EF-02-ef-arc-authoring.md) amended — EF threads inside this life; support contracts still after R07

## Unlocks / enhances

- Horizontal continuity for C12 episodes beyond January
- Fixture time-depth for [C11](../conversational-ui/C11-tone-memory.md) (do **not** implement C11 here)
- June 30 steal point for [SEC-07](../security/SEC-07-shadow-reconstruction-benchmark.md)

## Non-goals

- Six months of authored content (monthly tickets)
- `ALEX_BIOGRAPHY.md` or a compiled life
- `scenarios/alex-v2/` as a second Alex
- C11 tone store / learner / C09 payload
- SEC-07 attacker, strip runner, or reconstruction scorer
- WhatsApp / chat ingestion runtime (use existing source types)
- Expanding `intent_router` phrase families
- Moving 0.2.1 `week-*.yaml` into `2026-01/` before the 0.3.0 bump
- Hugging Face full-life reprime ([P04](../pilot/P04-alex-full-life-reprime.md) / [data-boot.md](../../docs/architecture/data-boot.md) Level 2). D08f is authored ordinary events on the alex-v1 spine, not HF ingest as a prebuilt brain.

## Why

D08 shipped **3 weeks** (2026-01-05 → 2026-01-25) and deferred multi-month expansion to a version bump. January is overloaded as both demo week and Alex’s entire existence. Six months of **ordinary events** (not biography) gives change over time: memory, obligations, relationships, tone, tasks, retention, attention.

V2-EF-02 planned a competing `scenarios/alex-v2/` with 3–6 month EF arcs. **Revive here** instead of forking a third corpus. Spec: [demo-corpus.md](../../docs/architecture/demo-corpus.md#six-month-ordinary-life-d08f).

## Acceptance criteria (this programme slice)

- [x] Architecture note: ordinary-events rule, monthly layout, cross-links C12 / C11 / SEC-06 / SEC-07
- [x] Home is `scenarios/alex-v1/` (version bump); V2-EF-02 amended not to create `alex-v2`
- [x] Empty month dirs `timeline/2026-01/` … `2026-06/` + README “source events only, no biography”
- [x] One February stub event matching existing fixture format; **not** loaded by 0.2.1
- [x] Monthly tickets D08f-02 … D08f-06 + [D08f-scripts](./D08f-scripts.md)
- [ ] Recursive timeline glob + `scenario.yaml` 0.3.0 bump — **[D08f-02](./D08f-02-february.md)**, not this slice
- [ ] Monthly source events — monthly tickets
- [ ] Life Script YAML — [D08f-scripts](./D08f-scripts.md)

## Monthly tickets

| Ticket | Month | Notes |
| --- | --- | --- |
| (none) | JAN | Already 0.2.1 `week-01.yaml` … `week-03.yaml` |
| [D08f-02](./D08f-02-february.md) | FEB | First nested load + 0.3.0 bump |
| [D08f-03](./D08f-03-march.md) | MAR | Calendar conflict; waiting-on; weak intention ≠ task |
| [D08f-04](./D08f-04-april.md) | APR | Quiet; decay; dormant project |
| [D08f-05](./D08f-05-may.md) | MAY | New commitment ∩ old context |
| [D08f-06](./D08f-06-june.md) | JUN | SEC-06/07 payoff events |
| [D08f-scripts](./D08f-scripts.md) | — | C12 episodes; not C11 |

## Test plan

- 0.2.1 still loads only January (`test_alex_v1_0_2_1_stays_january`)
- Nested month YAML exists on disk and is ignored until D08f-02
- Scenario validator still rejects world-model keys in payloads

## Privacy constraints

- Fictional content only; no Private paths or real correspondence
- No `ALEX_BIOGRAPHY.md`; no sensitive-inference plot (medical crisis, intimate breakup, etc.)
- Security canaries stay the opt-in overlay — not behavioural timeline
