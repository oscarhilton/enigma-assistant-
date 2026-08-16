import { useState } from "react";

export type GoogleCalendarOption = {
  id: string;
  summary: string;
  primary?: boolean;
};

type GoogleCalendarSelectionProps = {
  calendars?: GoogleCalendarOption[];
  selectedIds?: string[];
  onChange?: (selectedIds: string[]) => void;
};

const FIXTURE_CALENDARS: GoogleCalendarOption[] = [
  { id: "primary", summary: "Personal", primary: true },
  { id: "work@example.com", summary: "Work" },
];

/**
 * Minimal Google calendar selection UI (M12). Persistence / settings shell is M00b.
 * Unchecked calendars are excluded from sync (no blind import).
 */
export function GoogleCalendarSelection({
  calendars = FIXTURE_CALENDARS,
  selectedIds,
  onChange,
}: GoogleCalendarSelectionProps) {
  const [internalSelected, setInternalSelected] = useState<string[]>(
    selectedIds ?? [],
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
    <section className="google-calendar-selection" aria-label="Google calendars">
      <h2>Google Calendars</h2>
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
                {calendar.summary}
                {calendar.primary ? " (primary)" : ""}
              </span>
            </label>
          </li>
        ))}
      </ul>
    </section>
  );
}
