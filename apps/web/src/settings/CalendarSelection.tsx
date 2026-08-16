import type { CalendarSource } from "./types";

type CalendarSelectionProps = {
  calendars: CalendarSource[];
  onToggle: (calendarId: string, enabled: boolean) => void;
  disabled?: boolean;
};

export function CalendarSelection({
  calendars,
  onToggle,
  disabled = false,
}: CalendarSelectionProps) {
  return (
    <section className="settings-section" aria-labelledby="calendar-selection-heading">
      <h2 id="calendar-selection-heading">Calendars</h2>
      <p>Choose which calendars Enigma watches. Disabled calendars are not synced.</p>
      <ul className="calendar-list">
        {calendars.map((calendar) => (
          <li key={calendar.id}>
            <label>
              <input
                type="checkbox"
                checked={calendar.enabled}
                disabled={disabled}
                onChange={(event) => onToggle(calendar.id, event.target.checked)}
              />
              <span>
                {calendar.name}
                <span className="calendar-provider"> ({calendar.provider})</span>
              </span>
            </label>
          </li>
        ))}
      </ul>
    </section>
  );
}
