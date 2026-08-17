# C29 — Life memory, retention gate, and third-party ethics

**Status:** todo  
**Branch:** `ticket/C29-life-memory-and-retention`  
**Domain:** conversational-ui  
**May edit:** `packages/domain/src/personal_enigma/domain/retention.py`, `apps/api/src/personal_enigma/api/storage/derived.py`, `apps/api/src/personal_enigma/api/routes/forget.py`, `apps/api/tests/test_c29_*.py`, `docs/architecture/data-retention.md`, `docs/architecture/enigma-master-gap-analysis.md`, `tickets/conversational-ui/**`

**Must not edit:** raw-source retention guarantees · SEC-06 forget cascade invariants · new psych-profile storage

**Hard depends:** [C26](./C26-grounded-assertions-epistemics.md)  
**Soft (~):** SEC-06 lineage/forget work · [C30](./C30-brain-cortex-case-file.md) Brain projection follow-on

## Goal

Separate establishment from retention and make third-party memory ethically narrow and inspectable.

## Deliverables

- [ ] Retention gate asks whether an established assertion deserves persistence, for how long, and for what purpose
- [ ] Distinguish durable facts, hypotheses, stale items, and derived summaries
- [ ] Define third-party memory rules around concrete preferences vs prohibited profiling
- [ ] Tests cover derivative-aware forgetting and “truth does not imply retention”

## Definition of done

Enigma can retain useful concrete facts for the user while refusing to turn other people into psychological dossiers.
