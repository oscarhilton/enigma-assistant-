# POLARIS-SEARCH-06 — Shadow mode (search beside current planner)

| Field | Value |
| --- | --- |
| Status | `future` |
| Branch | `ticket/POLARIS-SEARCH-06-shadow-planner` |
| Domain | `polaris` |

## Package boundary (hard)

- May edit: shadow comparison hook next to existing Next Action planner (API/worker observation path), tests, docs
- Must not edit: user-visible Next Action / conversation output; Attention policy; Shadow Mode storage roots ([ADR-008](../../docs/adr/008-shadow-storage-roots.md) Phase 3 — do not confuse names)

## Hard depends

- [POLARIS-SEARCH-04](./POLARIS-SEARCH-04-receding-horizon-search.md) `done`
- [ALEX-EVAL-02](../demo-evaluation/ALEX-EVAL-02-planner-tournament.md) `done`
- [BRAIN-01](../conversational-ui/BRAIN-01-structured-search-trace.md) `done`

## Soft depends (~)

- BRAIN-02 Lens (operators may inspect traces; not required to land 06)
- N01 live scorer (compare against whatever currently drives WORTH DOING)

## Unlocks / enhances

- POLARIS-SEARCH-07

## Non-goals

- Changing what Alex Lab / My Enigma shows as NEXT
- Phase 3 Shadow Mode environment
- Promotion

## Acceptance criteria

- [ ] Search planner runs **alongside** the existing next-work / Next Action planner
- [ ] User-visible output **byte-stable** vs baseline in a frozen Alex Lab fixture (same NEXT title/category)
- [ ] Shadow record includes both planners’ ply-0 + trace id; Demo/Private/Shadow **storage roots remain unshared** ([ADR-005](../../docs/adr/005-demo-private-storage-roots.md))
- [ ] Fail-closed: search exception → existing planner still serves; no empty panic
- [ ] Flag default off-for-output, on-for-observation in Alex Lab only until 07

## Exit conditions

Done when CI proves output parity with search enabled-in-shadow, and ALEX-EVAL-02 can consume the shadow pairs.

## Test plan

- Golden conversation / `next_action.get` fixture: search-shadow on vs off → identical user payload
- Exception injection in search → fallback planner
- No write to Private DB from Alex Lab shadow

## Privacy constraints

- Shadow traces stay in Demo/Alex Lab
- No Oscar mailbox; no remote dump of PV as biography
