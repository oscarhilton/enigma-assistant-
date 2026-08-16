# N03 — Preference learning from NextAction rejects

| Field | Value |
| --- | --- |
| Status | `todo` |
| Branch | `ticket/N03-next-action-preference` |
| Domain | `next-action` |

## Package boundary (hard)

- May edit: preference store under Private (and Demo-isolated) roots; scorer hooks; tests
- Must not edit: Demo storage shared with Private ([ADR-005](../../docs/adr/005-demo-private-storage-roots.md)); Shadow silence evaluation docs; hard-coded “user hates X” rules

## Hard depends

- M20, N02 (reject event), M00a (persistence patterns)

## Soft depends (~)

- N01
- D01 (Demo root isolation if Demo learns separately)

## Unlocks / enhances

- Improves contextual fit over time without enlarging remote model view of preferences

## Non-goals

- Personality diagnosis
- Cross-user collaborative filtering
- Sending reject transcripts to hosted models
- Permanent category bans from a single reject

## Acceptance criteria

- [ ] Accept / reject (Something else) / ignore events stored privately with context features (attention load, time available, category, effort) — not raw message bodies
- [ ] Memory is **cautious**: e.g. “when no urgent work and load high, maintenance/admin historically low acceptance” — never “hates email cleaning”
- [ ] Scorer can read preference priors as soft weights (N01)
- [ ] Demo and Private preference stores do not share keys/roots
- [ ] Unit tests: repeated rejects under same context lower that category’s fitness; accepts raise it modestly; single reject does not zero a category

## Test plan

- Synthetic reject stream → prior update → score delta
- Isolation test: Demo preference path ≠ Private path

## Privacy constraints

- Preference memory is local enrichment of the private world model; select → transform → transmit last. Do not ship raw reject reasons with PII to remote inference.
