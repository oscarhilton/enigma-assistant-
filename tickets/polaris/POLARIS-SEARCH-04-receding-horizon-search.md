# POLARIS-SEARCH-04 — Receding-horizon search

| Field | Value |
| --- | --- |
| Status | `future` |
| Branch | `ticket/POLARIS-SEARCH-04-receding-horizon-search` |
| Domain | `polaris` |

## Package boundary (hard)

- May edit: search engine module (iterative deepening, prune, chance nodes, quiescence, PV), tests
- Must not edit: user-visible Next Action path (that is 06/07); Lens UI (BRAIN-02); motif opening book (05)

## Hard depends

- [POLARIS-SEARCH-02](./POLARIS-SEARCH-02-move-generation-legality.md) `done`
- [POLARIS-SEARCH-03](./POLARIS-SEARCH-03-local-evaluator.md) `done`

## Soft depends (~)

- POLARIS-SEARCH-05 (ordering/pruning priors — 04 must work with uniform ordering first)
- BRAIN-01 trace schema (04 may emit a stub trace; typed freeze is BRAIN-01)

## Unlocks / enhances

- 05, ALEX-EVAL-02, BRAIN-01, 06

## Non-goals

- Authorising more than ply-0
- Promising a fixed “20 moves ahead” to users
- Chain-of-thought logs
- Driving live recommendations (07)

## Acceptance criteria

- [ ] Iterative deepening: complete shallow search before deeper
- [ ] Planning depth may exceed execution depth; **only ply-0** is the executable suggestion
- [ ] Future nodes carry **fading confidence** with depth
- [ ] Chance / uncertainty branches (reply happens | doesn’t) are representable
- [ ] Quiescence: extend in unstable/forcing positions (overlap, deadline cliff, blocker arrival) then stop. **`herald`** (Sirius-as-Herald) is the forcing-change detector that can trigger quiescence / replan — it is **not** a value head that outranks `recovery` or `craft`
- [ ] Incomplete coverage (`coverage_adequate: false`) must not invent empty calendars as free time
- [ ] Pruning uses 03 effort hints + 02 legality; never prunes REST solely as “unproductive”
- [ ] Principal variation is hypotheses, not a granted plan
- [ ] “20 moves” is a test budget cap, not a product SLA
- [ ] Example: token-inventory-blocker — PV ply-0 considers unblock (Figma/Jordan) before “finish the whole inventory”; deeper plies may sketch later draft work **without** authorising it

## Exit conditions

Done when a deterministic search on frozen Alex positions returns a PV + ply-0 + confidence-by-depth, with tests that COMMIT is not implied by a long PV.

## Test plan

- Deepening: depth 1 legal move ⊆ depth 2 first ply
- Fade: confidence(ply n) ≥ confidence(ply n+1) on the PV
- Negative: API/user payload must not include “committed_line” of length > 1
- Chance node: waiting-on-someone has at least two successor chance outcomes
- Coverage gap fixture: calendar fail → ply-0 is incomplete-picture, not deep work

## Privacy constraints

- Search stays on compiled `DecisionPosition`; no vault dump into the tree
- Trace text fields are reason codes, not model hidden states
