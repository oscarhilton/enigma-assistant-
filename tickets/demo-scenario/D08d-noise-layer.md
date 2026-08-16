# D08d — Noise layer (machine sludge)

| Field | Value |
| --- | --- |
| Status | `todo` |
| Branch | `ticket/D08d-noise-layer` |
| Domain | `demo-scenario` / `demo-simulation` |
| Parent | [D08](./D08-canonical-alex.md) |

## Distinct question from D08c

| Ticket | Asks |
| --- | --- |
| **D08c** | Can Enigma cope with lots of **plausible human conversation**? |
| **D08d** | Can Enigma ruthlessly ignore **machine-generated sludge**? |

Keep background correspondence and noise **conceptually distinct**. Do not fold newsletters into the D08c human-background corpus.

## Package boundary (hard)

- May edit: `GeneratedNoiseStream` templates (newsletters, receipts, automated project notifications, marketing, account notices, delivery updates, calendar confirmations, spam-like material)
- May edit: ground-truth `signal_class: noise` fixtures (evaluator-only)
- May edit: quiet-day scenario + Background False Alerts / 1,000 headline metric
- Must not: mix adversarial/hostile packs into default noise (D09 stays separate)
- Must not: reopen D08c A/B gate definitions except to consume them as baselines

## Hard depends

- D08c background integration (scientific gate green)

## Soft depends (~)

- D09 for optional SpamAssassin developer profiles

## Unlocks / enhances

- D08e scale profile
- UI “signals suppressed” stats (D10 amendment)
- Phase 2.5 exit (quiet-day + false-alert rate)

## Non-goals

- Pushing spam corpora through real Gmail
- Trademarked provider names in templates
- Making noise characters “meaningful”

## Acceptance criteria

- [ ] Deterministic local noise templates with distinct distributions (newsletters, receipts, automated notifications, marketing, account notices, delivery updates, calendar confirmations, spam-like)
- [ ] Noise enters the **same** mailbox stream as canonical/background (identical ingestion; no Enigma-visible labels)
- [ ] Headline metric: **Background False Alerts / 1,000 messages** measured and under agreed threshold
- [ ] **Quiet-day** scenario: e.g. 183 emails arrive, **0** genuine obligations → **Attention empty**
- [ ] Inventing something to say because there is lots to read is a **product-level failure** (test asserts zero attention)

## Test plan

- Feature scenario `background-no-alert` / quiet-day
- Noise classification never visible on `PrivateMessage` payloads
- False-alert rate fixture at known noise volume

## Privacy constraints

- Synthetic-only for public Demo; SpamAssassin/TREC developer-only
