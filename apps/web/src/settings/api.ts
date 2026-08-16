import type { SettingsState } from "./types";
import { FIXTURE_SETTINGS } from "./fixtures";

/** Prefer VITE_API_BASE (e.g. http://127.0.0.1:8000); fall back to same-origin /api. */
const API_BASE = (import.meta.env.VITE_API_BASE as string | undefined)?.replace(/\/$/, "") ?? "";
const SETTINGS_URL = `${API_BASE}/api/settings`;
const CALENDARS_URL = `${API_BASE}/api/settings/calendars`;

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
  const response = await fetchImpl(CALENDARS_URL, {
    method: "PUT",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ enabled_ids: enabledIds }),
  });
  if (!response.ok) {
    throw new Error(`Failed to persist calendar selection (${response.status})`);
  }
  return (await response.json()) as SettingsState;
}
