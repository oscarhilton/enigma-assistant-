# R07 — Exit report and architecture decision

| Field | Value |
| --- | --- |
| Status | `todo` |
| Branch | `ticket/R07-reasoning-value-gate-report` |
| Domain | `demo-evaluation` + docs |

## Package boundary (hard)

- May edit: `packages/evaluation/src/personal_enigma/evaluation/reasoning_value_gate.py` (create)
- May edit: `packages/evaluation/tests/test_reasoning_value_gate.py`
- May edit: `docs/reports/reasoning-value-gate-report.md` (generated or checked-in exemplar)
- May edit: `docs/adr/012-reasoning-value-gate-decision.md` (fill evidence table — stub exists from docs PR)
- Must not edit: `packages/attention/**` ranking logic, Shadow Mode tickets

## Hard depends

- [R05](./R05-failure-attribution.md)
- [R06](./R06-privacy-ablation.md)

## Soft depends (~)

- [ADR-012](../../docs/adr/012-reasoning-value-gate-decision.md) stub (from docs sprint)

## Unlocks / enhances

- Architecture decision: adopt / hybrid / keep deterministic ([ADR-012](../../docs/adr/012-reasoning-value-gate-decision.md))
- Stretch: [V2-EF-02](../demo-scenario/V2-EF-02-ef-arc-authoring.md) three longitudinal arcs (after gate passes)

## Non-goals

- Tauri / desktop shell
- Shadow Mode features
- 40k email corpus generation
- Runtime NextAction product surface

## Acceptance criteria

- [ ] `reasoning_value_gate.py` CLI or `enigma-eval` subcommand aggregates R02–R06 outputs
- [ ] Report table populated (not hypothetical placeholders):

| Metric | Arm A (heuristic) | Arm B (LLM) |
| --- | --- | --- |
| Critical recall | measured | measured |
| Must-suppress accuracy | measured | measured |
| Top-3 critical recall | measured | measured |
| Next-action fit | measured | measured |
| Median latency | ~ms | ~s |
| Cost/month extrapolation | ~$0 | measured |
| Privacy ablation delta | — | raw vs transformed |

- [ ] Written architecture decision with evidence in report + [ADR-012](../../docs/adr/012-reasoning-value-gate-decision.md)
- [ ] Failure attribution summary per disagreement category
- [ ] Sprint exit gate checklist in [reasoning-value-gate.md](../../docs/demo/reasoning-value-gate.md) marked complete

### Architecture outcomes (fill with evidence)

| Outcome | Decision path |
| --- | --- |
| LLM clearly wins | Adopt: local evidence → privacy transform → reasoning LLM → structured judgement → deterministic policy |
| Barely wins | Hybrid: obvious → local; uncertain → LLM |
| Loses | Keep deterministic; save cost/latency/privacy exposure |

## Test plan

- Integration test with replay fixtures → report JSON schema validates
- All metric rows non-null when R03–R06 fixtures present
- ADR-012 outcome row selected matches report conclusion enum

## Privacy constraints

- Report is Demo Mode / developer artefact only
- No PrivatePerson, raw Notes, or support contract YAML in published report excerpts intended for external sharing without redaction

## Notes

- Primary sprint deliverable — confident A/B report, not product features
- Architecture: [reasoning-value-gate.md](../../docs/demo/reasoning-value-gate.md)
