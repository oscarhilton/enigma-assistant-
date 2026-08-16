# S04 — Shadow attention log

| Field | Value |
| --- | --- |
| Status | `todo` |
| Branch | `ticket/S04-shadow-attention-log` |
| Domain | `shadow` |
| Baseline | `v0.2.0-demo` |

## Package boundary (hard)

- May edit: `packages/attention/**` for Shadow log writer / schema
- May edit: `apps/api/**`, `apps/worker/**` to persist attention under Shadow root
- May edit: tests under those packages
- May amend: `docs/architecture/shadow-mode.md` log path notes; soft cross-link [shadow-silence-evaluation.md](../../docs/architecture/shadow-silence-evaluation.md) / SE04 for full SUPPRESS snapshots
- Must not edit: Demo evaluation runner, scenario corpora, notification delivery adapters beyond calling the log, Gmail OAuth

## Hard depends

- S01 `done`
- S02 `done`
- S03 `done` (or soft if log-only path proven without delivery)

## Soft depends (~)

- M06 attention engine behaviour
- SE04 (extends suppress decisions with frozen snapshots — soft; S04 may land surface/candidate rows first)

## Unlocks / enhances

- Evidence base for S05 comparison stubs and the seven evaluation goals
- Candidate ids for [SE04](./SE04-suppression-decision-log.md) silence snapshots

## Non-goals

- Answering the seven questions (evaluation goals only — S05)
- Surfacing Shadow attention as user notifications
- Demo attention card polish
- Full frozen SUPPRESS snapshot schema (SE04)

## Acceptance criteria

- [ ] Shadow runs generate attention records into `~/.enigma/shadow/attention-log/` (or equivalent under Shadow root)
- [ ] Records include enough fields for later scoring (item id, score, rationale stub, timestamps)
- [ ] Log writes do not trigger notification delivery
- [ ] Demo and Private attention stores remain untouched
- [ ] Docs note relationship to silence evaluation ([shadow-silence-evaluation.md](../../docs/architecture/shadow-silence-evaluation.md))

## Test plan

- Generate N attention events in Shadow → N log rows under Shadow root
- Assert no delivery adapter calls
- Assert Demo/Private paths not written

## Privacy constraints

- Log stays local under Shadow root; no hosted-model dump of raw Notes / `PrivatePerson`
