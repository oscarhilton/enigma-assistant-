# OBSERVATORY-03 — Runtime and wiring probes

| Field | Value |
| --- | --- |
| Status | `future` |
| Branch | `ticket/OBSERVATORY-03-runtime-probes` |
| Domain | `observatory` |

## Package boundary (hard)

- May edit: probe runners (API health / capability ping / wiring assertions), registry `RUNNING` / `USABLE` writers, tests, docs pointers
- Must not edit: Assist execution; retention policy; PolarIS searcher; Observatory visual language (02)

## Hard depends

- [OBSERVATORY-02](./OBSERVATORY-02-observatory-ui.md) `done`
- [RECON-08](../recon/RECON-08-alex-eval-catalogue.md) `done` (catalogue gives probe targets / Alex hooks)

## Soft depends (~)

- Existing health routes (`apps/api` health)
- C14 public hops as optional probe signals (do not invent CoT)

## Unlocks / enhances

- Honest `RUNNING` / `USABLE` on the Observatory; later PolarIS shadow comparison can cite the same probe grammar

## Intent

Back `RUNNING` and `USABLE` with **real evidence**, not docs checkboxes.

- **last_verified** — clock of the newest successful verification or probe
- **Freshness** — elapsed probe → demote `RUNNING` / `USABLE`
- **Broken-wire detection** — missing import/route/job/adapter edges become `broken_wires[]`
- **USABLE** additionally requires the user-facing path to succeed in this environment (Demo/Alex Lab first)

## Non-goals

- Probing Oscar’s Private mailbox
- Using LLM judges as the probe of record
- Fake green by catching-and-ignoring probe failures
- Restoring C28 inside this ticket

## Acceptance criteria

- [ ] Probes emit evidence refs the registry accepts (id + clock + pass/fail + edge)
- [ ] `RUNNING.held` cannot be true without a probe newer than the freshness window
- [ ] Failed or absent probe demotes headline and lists `broken_wires` or `stale_probe`
- [ ] `USABLE.held` requires `RUNNING` + documented user path + hard deps usable/verified per [observatory.md](../../docs/architecture/observatory.md)
- [ ] Calendar-coverage analog: if a required adapter is down, capability is not `USABLE` (Goose/incomplete-picture parity — do not invent a free day)
- [ ] At least one Alex-catalogue probe target from RECON-08

## Exit conditions

Done when 02 can show a live demotion (kill a fixture wire → graph edge breaks; **Can I use this now?** flips) without editing markdown.

## Test plan

- Fresh probe → `RUNNING`
- Clock jump past freshness → demotion
- Missing route fixture → `broken_wires`
- Negative: docs-only checkbox cannot set `RUNNING`

## Privacy constraints

- Probes stay on compiled / Demo surfaces; no vault dump
- Evidence is ids and status, not mail bodies
