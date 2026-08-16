# MVP source matrix

| Source | MVP | Access | Default risk |
| --- | --- | --- | --- |
| Gmail | Yes | cloud API, read-only | Medium |
| Google Calendar | Yes | cloud API, read-only | Medium |
| Apple Calendar | Yes | local EventKit | Medium |
| Apple Reminders | Yes | local EventKit | Medium |
| Apple Contacts | Yes | Contacts framework | High |
| Apple Notes | Yes, experimental | macOS automation | High |
| Apple Mail | Later | provider-specific | High |
| Messages | Later / research | TBD | Very High |
| Health | Later | HealthKit | Very High |
| Photos | Later | PhotoKit | Very High |
| Safari | Later | limited / selective | High |

## Explicitly out of MVP

- Apple Mail (Phase 2 — do not scrape Mail.app DB)
- Messages
- HealthKit
- Photos
- Safari history / bookmarks (bookmarks maybe later, low risk)
