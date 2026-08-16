import { useState } from "react";

export type AppleCalendarOption = {
  id: string;
  title: string;
  source?: string;
};

type AppleCalendarSelectionProps = {
  calendars?: AppleCalendarOption[];
  selectedIds?: string[];
  onChange?: (selectedIds: string[]) => void;
};

const FIXTURE_CALENDARS: AppleCalendarOption[] = [
  { id: "cal-personal", title: "Personal", source: "iCloud" },
  { id: "cal-work", title: "Work", source: "Exchange" },
];

/**
 * Minimal Apple calendar selection UI (M08). Persistence / settings shell is M00b.
 */
export function AppleCalendarSelection({
  calendars = FIXTURE_CALENDARS,
  selectedIds,
  onChange,
}: AppleCalendarSelectionProps) {
  const [internalSelected, setInternalSelected] = useState<string[]>(
    selectedIds ?? calendars.map((calendar) => calendar.id),
  );
  const selected = selectedIds ?? internalSelected;

  function toggle(id: string) {
    const next = selected.includes(id)
      ? selected.filter((value) => value !== id)
      : [...selected, id];
    if (selectedIds === undefined) {
      setInternalSelected(next);
    }
    onChange?.(next);
  }

  return (
    <section className="apple-calendar-selection" aria-label="Apple calendars">
      <h2>Apple Calendars</h2>
      <p>Choose which calendars Enigma may read. Selection is required before sync.</p>
      <ul>
        {calendars.map((calendar) => (
          <li key={calendar.id}>
            <label>
              <input
                type="checkbox"
                checked={selected.includes(calendar.id)}
                onChange={() => toggle(calendar.id)}
              />
              <span>
                {calendar.title}
                {calendar.source ? ` (${calendar.source})` : ""}
              </span>
            </label>
          </li>
        ))}
      </ul>
    </section>
  );
}
