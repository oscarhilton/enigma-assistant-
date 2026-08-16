import type { SettingsState } from "./types";

/** Fixture calendars when the API is unreachable (dev / offline). */
export const FIXTURE_SETTINGS: SettingsState = {
  calendars: [
    { id: "apple:work", name: "Work", provider: "apple_calendar", enabled: true },
    {
      id: "apple:personal",
      name: "Personal",
      provider: "apple_calendar",
      enabled: true,
    },
    { id: "google:team", name: "Team", provider: "google_calendar", enabled: false },
  ],
  apple_permissions: [
    {
      id: "calendar",
      label: "Calendar",
      status: "pending",
      detail: "read access (pending Apple Bridge)",
    },
    {
      id: "reminders",
      label: "Reminders",
      status: "pending",
      detail: "read access (pending Apple Bridge)",
    },
    {
      id: "contacts",
      label: "Contacts",
      status: "pending",
      detail: "read access (pending Apple Bridge)",
    },
    {
      id: "notes",
      label: "Notes",
      status: "pending",
      detail: "automation, opt-in (pending Apple Bridge)",
    },
  ],
  scheduled_for_sync: ["apple:work", "apple:personal"],
};

export function withScheduledSync(calendars: SettingsState["calendars"]): SettingsState {
  const scheduled_for_sync = calendars.filter((c) => c.enabled).map((c) => c.id);
  return {
    calendars,
    apple_permissions: FIXTURE_SETTINGS.apple_permissions,
    scheduled_for_sync,
  };
}
