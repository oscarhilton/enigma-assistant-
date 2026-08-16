# Provider-agnostic ingestion

Define a single protocol so Core never becomes a forest of provider conditionals:

```python
class DataSource(Protocol):
    async def get_changes(
        self,
        cursor: SyncCursor | None,
    ) -> ChangeBatch:
        ...
```

Implementations (planned):

- `GmailSource`
- `GoogleCalendarSource`
- `AppleCalendarSource`
- `AppleReminderSource`
- `AppleContactsSource`
- `AppleNotesSource`

Scaffold lives in [`packages/ingestion`](../../packages/ingestion).

## SourceType vs Provider

```text
SourceType  → what the thing is   (email, calendar_event, reminder, note, contact)
Provider    → where it came from (google, apple, local)
```

These are separate enums in `packages/domain`. A calendar event is always a `calendar_event`; whether it came from Apple or Google is metadata at the ingestion boundary.

## Canonical private models

After ingestion, Core works with:

- `PrivateCalendarEvent` (`provider`: `apple_calendar` | `google_calendar`)
- `PrivateReminder` (`provider`: `apple_reminders`)
- `PrivatePerson`
- `PrivateNote` (`provider`: `apple_notes`)

Calendar selection (which calendars to watch) is preferable to blindly importing everything. Deduplication of the same Google calendar configured inside Apple Calendar is required — see [deduplication.md](./deduplication.md).
