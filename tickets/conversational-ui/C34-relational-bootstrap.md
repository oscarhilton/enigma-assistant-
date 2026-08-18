# C34 — Relational Bootstrap (continuation mechanics)

**Status:** in_progress  
**Branch:** `ticket/C34-relational-bootstrap`  
**Depends (hard):** C15 semantic bootstrap / ADR-031 on main  
**Depends (soft ~):** C33 forensic corpus (goose frame exemplars)

## Scope (package boundary)

- `apps/api/src/personal_enigma/api/relational_bootstrap.py`
- `apps/api/src/personal_enigma/api/context_compilation.py` (wire hook only)
- `apps/api/tests/test_c34_relational_bootstrap.py`
- this ticket

## Frozen spec

Relational Bootstrap is **continuation mechanics**, not a hidden person model.

**Inputs (explicit only):** product voice, interaction prefs, shared conventions, ephemeral register, approved exemplars.

**Output:** compact bootstrap block segregated from evidence and authority.

**Invariants:**

- Retrieval success does NOT imply conversational use (bootstrap may contain THE Goose; response may contain zero goose).
- Shared convention → understand grammar → use / mutate / ignore — NEVER “reference must appear”.
- Must NOT: create truth, grant authority, retain biography, profile personality, force callbacks, Mad Libs culture, fake intimacy, emotional inference.

## Acceptance

- [ ] HONK HONK test — participates in established frame; forbids meta/emotional inference/duck emoji
- [ ] Abstinence — sane without bootstrap; culture retrievable but ignorable
- [ ] Crowbar — unrelated personal memory stays out of bootstrap wire
- [ ] `uv run pytest apps/api/tests/test_c34_relational_bootstrap.py`
