# Deduplication and obligation merging

## Calendar duplicates

The same Google calendar may also be configured inside Apple Calendar. Enigma must ingest **one** canonical event.

Initial deduplication signals:

- provider identifiers where available
- start / end time
- normalised title
- organiser
- attendee overlap

Users select which calendar sources Enigma watches (prefer selection over blind import).

## Cross-source obligations

Reminders, email commitments, and calendar events that refer to the same underlying task should converge:

```python
Obligation(
    description="Review proposal",
    due_at=friday_before_meeting,
    evidence=[
        ReminderEvidence(...),
        EmailEvidence(...),
        CalendarEvidence(...),
    ],
    confidence=0.98,
)
```

Attention kinds to distinguish:

- `INFERRED_OBLIGATION`
- `EXPLICIT_REMINDER` (stronger than email inference)
- `INFERRED_COMMITMENT`
- `CALENDAR_OBLIGATION`

Explicit Apple Reminders are stronger signals than inferred email obligations; merge rather than double-alert.
