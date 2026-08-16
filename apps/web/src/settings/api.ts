import type { SettingsState } from "./types";
import { FIXTURE_SETTINGS } from "./fixtures";

const SETTINGS_URL = "/settings";

export async function fetchSettings(
  fetchImpl: typeof fetch = fetch,
): Promise<SettingsState> {
  try {
    const response = await fetchImpl(SETTINGS_URL);
    if (!response.ok) {
      return structuredClone(FIXTURE_SETTINGS);
    }
    return (await response.json()) as SettingsState;
  } catch {
    return structuredClone(FIXTURE_SETTINGS);
  }
}

export async function persistCalendarSelection(
  enabledIds: string[],
  fetchImpl: typeof fetch = fetch,
): Promise<SettingsState> {
  const response = await fetchImpl("/settings/calendars", {
    method: "PUT",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ enabled_ids: enabledIds }),
  });
  if (!response.ok) {
    throw new Error(`Failed to persist calendar selection (${response.status})`);
  }
  return (await response.json()) as SettingsState;
}
