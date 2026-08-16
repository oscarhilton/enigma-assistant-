# SE10 — Counterfactual A/B harness (later)

| Field | Value |
| --- | --- |
| Status | `blocked` |
| Branch | `ticket/SE10-counterfactual-ab-harness` |
| Domain | `shadow` |
| Baseline | [shadow-silence-evaluation.md](../../docs/architecture/shadow-silence-evaluation.md) |

## Package boundary (hard)

- May edit: `packages/evaluation/**` for harness types + offline comparison
- May amend: silence-evaluation / shadow-evaluation docs
- May edit: tests with synthetic timelines
- Must **not** change live attention policy in Private Mode from this ticket alone
- Must **not** edit Demo F-* science gates
- Must **not** edit `EnvironmentMode`

## Hard depends

- Soft preference: SE04 + SE08 landed enough to compare logged B policy against a recorded A policy — until then keep status `blocked` or types-only

## Soft depends (~)

- SE04 frozen snapshots
- SE07 / SE08 labels
- SE01 action joins
- S04 / S05
- S06 exit discussion

## Unlocks / enhances

- Ultimate tradeoff measure: useful caught vs false interruptions vs important misses
- Honest promote-from-Shadow arguments

## Non-goals

- Claiming one system “wins” without human-weighted costs
- Online experiment platform / growth analytics

## Acceptance criteria

- [ ] Define System A = surface everything plausibly actionable; System B = Enigma policy
- [ ] Harness inputs: same real (or fixture) window, frozen evidence for B, generative A candidate set rules documented
- [ ] Outputs: useful_caught, false_interruptions, important_misses (+ optional cost weights)
- [ ] Types-only stub acceptable while `blocked`; document unblock criteria in ticket when SE04/SE08 land
- [ ] Tests: synthetic week yields stable tradeoff triple

## Test plan

- Fixture timeline with known A/B divergence → expected counts

## Privacy constraints

- Harness runs locally on Shadow artefacts
- No upload of raw corpora to third parties
