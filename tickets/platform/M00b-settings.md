# M00b — Settings and calendar selection

| Field | Value |
| --- | --- |
| Status | `todo` |
| Branch | `ticket/M00b-settings` |
| Domain | `platform` |

## Package boundary (hard)

- May edit: `apps/web/src/pages/SettingsPage.tsx` and `apps/web/src/settings/**` (create as needed)
- May edit: `apps/api/src/personal_enigma/api/routes/settings.py` (create as needed)
- Must not edit: Apple Bridge Swift sources, ingestion source adapters

## Hard depends

- None (can start after scaffold)

## Soft depends (~)

- M07 (live capability status)
- M00a (persist selection)

## Unlocks / enhances

- M08/M12 calendar selection UX
- Permission status display for Apple sources

## Non-goals

- Full design system
- OAuth UI for Google (belongs with M11/M12)

## Acceptance criteria

- [ ] Settings UI lists calendars with enable/disable checkboxes (fixture or API-backed)
- [ ] API persists which calendar sources Enigma watches
- [ ] Shows Apple permission placeholders (Calendar, Reminders, Contacts, Notes)
- [ ] Disabled sources are not scheduled for sync

## Test plan

- Web component tests for toggle behaviour
- API tests for selection persistence

## Privacy constraints

- Settings payloads must not include note bodies or full contact records
