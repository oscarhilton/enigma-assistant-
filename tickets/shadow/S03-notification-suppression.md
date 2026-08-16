# S03 — Notification suppression

| Field | Value |
| --- | --- |
| Status | `todo` |
| Branch | `ticket/S03-notification-suppression` |
| Domain | `shadow` |
| Baseline | `v0.2.0-demo` |

## Package boundary (hard)

- May edit: `packages/attention/**` for delivery-policy / suppress flag
- May edit: `apps/api/**`, `apps/worker/**` only for Shadow delivery guards
- May edit: `apps/web/src/**` only if a “notifications off” status stub is required
- May edit: matching tests under those packages
- Must not edit: Demo UI polish, tray/Electron packaging, Gmail OAuth, storage roots (S02)

## Hard depends

- S01 `done`

## Soft depends (~)

- S02 storage isolation
- Desktop tray tickets (if present) — must not block; suppress at Core first

## Unlocks / enhances

- Safe real-source observation without nagging the user
- Unlocks S04 (log without notify)

## Non-goals

- Designing notification copy / UX for Private Mode
- Electron tray implementation
- Muting Demo Mode notifications (Demo is fictional UI)

## Acceptance criteria

- [ ] When `EnvironmentMode.SHADOW`, attention items are not delivered to OS / push / tray channels
- [ ] Suppression is structural (delivery adapter no-ops or refuses), not merely hidden UI
- [ ] Private Mode delivery path unchanged when mode is private
- [ ] Banner / status continues to state notifications are off

## Test plan

- Shadow mode: fake delivery adapter never called / returns suppressed
- Private mode: delivery still invoked in unit test double
- Mode flip coverage

## Privacy constraints

- Suppressed payloads must not be forwarded to third-party push vendors
