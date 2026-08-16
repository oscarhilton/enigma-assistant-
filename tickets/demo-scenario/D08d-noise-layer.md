# D08d — Noise layer (machine sludge)

| Field | Value |
| --- | --- |
| Status | `done` |
| Branch | `ticket/D08d-noise-layer` |
| Domain | `demo-scenario` / `demo-simulation` |
| Parent | [D08](./D08-canonical-alex.md) |
| PR | [#47](https://github.com/oscarhilton/enigma-assistant-/pull/47) |

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

- [x] Deterministic local noise templates with distinct distributions (newsletters, receipts, automated notifications, marketing, account notices, delivery updates, calendar confirmations, spam-like)
- [x] Noise enters the **same** mailbox stream as canonical/background (identical ingestion; no Enigma-visible labels)
- [x] Headline metric: **Background False Alerts / 1,000 messages** measured and under agreed threshold (≤1.0 / 1k; quiet-day hard-gates at 0)
- [x] **Quiet-day** scenario: 183 emails arrive, **0** genuine obligations → **Attention empty** (`attention_items == 0`)
- [x] Inventing something to say because there is lots to read is a **product-level failure** (test asserts zero attention)

## Test plan

- [x] Feature scenario `background-no-alert` / quiet-day
- [x] Noise classification never visible on `PrivateMessage` payloads
- [x] False-alert rate fixture at known noise volume (alex-v1 demo mini)

## Privacy constraints

- Synthetic-only for public Demo; SpamAssassin/TREC developer-only
