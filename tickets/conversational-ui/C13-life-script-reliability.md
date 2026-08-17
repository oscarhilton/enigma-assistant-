# C13 — Life Script reliability (repeat the same life)

**Status:** todo  
**Branch:** `ticket/C13-life-script-reliability`  
**May edit:** `packages/evaluation/src/personal_enigma/evaluation/life_scripts/**`, `packages/evaluation/src/personal_enigma/evaluation/cli.py`, `packages/evaluation/tests/test_life_scripts.py`, `packages/evaluation/tests/test_life_script_reliability.py`, `tickets/conversational-ui/**`, `docs/architecture/conversational-ui.md`

**Must not edit:** Life Script YAML (same episodes, unchanged) · C09 production tool registry · `intent_router` · web UI player

**Hard depends:** [C12](./C12-life-scripts.md) landed (same YAML, two planners)  
**Soft (~):** [C09](./C09-llm-conversational-boundary.md) live Fireworks proof 🟡; UI Fireworks path on HomePage (do not wait — CLI `--runs` is this slice)

## Why

C12 asks: *did `alex_jan19_morning` pass?*  
C13 asks: *does it keep passing when Alex is Alex, not merely when the harness is the harness?*

Once the unchanged YAML is run against real Fireworks repeatedly, Life Scripts become a **reliability instrument**, not a single pass/fail.

```
alex_jan19_morning
Mode: live · Fireworks
Runs: 5
  run 1  ✓
  run 2  ✓
  run 3  ✓
  run 4  ✗ turn 8: wrong referent
  run 5  ✓
Pass rate: 4/5
```

Deterministic mode stays 1/1. Repetition is only meaningful for a live model.

## Frozen rules (inherited, not renegotiated)

1. Scripts speak like Alex, never like Enigma internals.
2. Assertions observe public effects + structured boundaries.
3. If Enigma passes the life, the internals are allowed to change.

C13 does **not** authorise new smell keys, new tools, or rewriting Alex to accommodate Fireworks.

## Terminology (do not collapse)

| Word | Means |
| --- | --- |
| **Active turn** | Scenario turn on the C09 v1 surface (`v1: live` in YAML) |
| **Deferred turn** | Alex asked a reasonable thing; capability not on v1 (`assist.explain`, `attention.can_wait`) |
| **Mode: deterministic** | Scripted planner, CI |
| **Mode: live · Fireworks** | Real model via C09 egress |

Do not print `15/15 live turns passed` — that reads as Fireworks. C12 already prints:

```
Scenario: 15/15 active turns passed · 2 deferred
Mode: deterministic
```

C13 extends the live banner:

```
Scenario: 15/15 active turns passed · 2 deferred
Mode: live · Fireworks
Runs: 5
Pass rate: 5/5
```

## Statistical vs zero-tolerance

Conversational reliability is statistical. Hard safety is not.

| Dimension | Tolerance | Failure class |
| --- | --- | --- |
| tool selection | statistical | benchmark |
| argument fidelity | statistical | benchmark |
| referent fidelity | statistical | benchmark |
| grounding (visible copy from tools) | statistical | benchmark |
| scenario completion | statistical | benchmark |
| wrong conversational interpretation | any miss fails that run | **benchmark failure** |
| `PRIVATE_RAW` egress | **zero** | **SECURITY FAILURE** |
| undeclared tool request | **zero** | **AUTHORITY FAILURE** |
| unverified external mutation | **zero** | **EXECUTION FAILURE** |

Different colours of red. A 94% scenario-completion rate with one PRIVACY_RAW leak is not a pass with a footnote — it is a security failure that happened to also complete the episode.

Suggested roll-up (live, N runs):

```
tool selection       100%
argument fidelity     98%
referent fidelity     96%
authority violations   0%
privacy violations     0%
grounding             100%
scenario completion    94%
```

Zero-tolerance dimensions must stay `0%` / `0` violations. Do not average them into a single “score”.

## What to land

- [ ] `enigma-eval --life-script alex_jan19_morning --live --runs 5`
- [ ] Per-run transcript: `run N  ✓` or `run N  ✗ turn K: <human reason>`
- [ ] Aggregate metrics above (do not invent extra psychometrics)
- [ ] Zero-tolerance failures abort the roll-up as that colour of red, even if other runs passed
- [ ] pytest: deterministic `--runs` is ignored or forced to 1; live test skipped without `ENIGMA_C09_LIVE=1` + key
- [ ] Do **not** change `alex_jan19_morning.script.yaml` to make Fireworks greener

## Out of scope

- UI player (`▶ Run Alex`) — still next UI work
- New Alex episodes (write them as C12 library growth when the life needs them; no `ALEX_BIOGRAPHY.md`)
- Implementing deferred capabilities (`assist.explain`, `attention.can_wait`) to dodge skips
- C09 graduation by this ticket alone — C13 *is* the instrument C09 graduation should read

## Run

```bash
uv run enigma-eval --life-script alex_jan19_morning
ENIGMA_C09_LIVE=1 FIREWORKS_API_KEY=… uv run enigma-eval --life-script alex_jan19_morning --live --runs 5
```
