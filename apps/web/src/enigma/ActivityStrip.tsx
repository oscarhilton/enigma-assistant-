import type { EnigmaActivityEvent } from "./activity";
import { isThreadActivity } from "./activity";

type Props = {
  events: EnigmaActivityEvent[];
};

export function ActivityStrip({ events }: Props) {
  const visible = events.filter(isThreadActivity);
  if (visible.length === 0) {
    return null;
  }

  if (visible.length === 1) {
    const event = visible[0]!;
    return (
      <p className="activity-strip" data-testid="activity-strip">
        <span className="activity-strip-mark" aria-hidden="true">
          ✓
        </span>
        {event.label}
      </p>
    );
  }

  return (
    <details className="activity-strip activity-strip--collapsed" data-testid="activity-strip">
      <summary>Checked {visible.length} things</summary>
      <ul className="activity-strip-list">
        {visible.map((event) => (
          <li key={event.id}>
            <span className="activity-strip-mark" aria-hidden="true">
              ✓
            </span>
            {event.label}
          </li>
        ))}
      </ul>
    </details>
  );
}
