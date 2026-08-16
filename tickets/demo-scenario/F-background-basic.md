# Feature scenario stub — background-basic

| Field | Value |
| --- | --- |
| Status | `done` |
| Domain | `demo-scenario` |
| Related | D08c, D03 |
| Branch | `ticket/F-background-basic` |
| Path | `scenarios/feature/background-basic/` |

## Intent

Canonical message surrounded by ~50 irrelevant background messages. Enigma should still surface the canonical obligation.

## Package boundary

- `scenarios/feature/background-basic/**`
- Ground-truth `signal_class` for background items (`expected_attention: false`)
- May edit: `packages/simulation` background expand helper + `tests/test_background_basic.py`

## Acceptance

- [x] Scenario package validates
- [x] Critical recall holds with background present
- [x] Source payloads omit `signal_class`
