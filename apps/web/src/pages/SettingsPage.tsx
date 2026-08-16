import { useEffect, useState } from "react";
import { ApplePermissions } from "../settings/ApplePermissions";
import { CalendarSelection } from "../settings/CalendarSelection";
import { fetchSettings, persistCalendarSelection } from "../settings/api";
import { withScheduledSync } from "../settings/fixtures";
import type { SettingsState } from "../settings/types";

type SettingsPageProps = {
  fetchImpl?: typeof fetch;
};

export function SettingsPage({ fetchImpl = fetch }: SettingsPageProps) {
  const [settings, setSettings] = useState<SettingsState | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [saving, setSaving] = useState(false);

  useEffect(() => {
    let cancelled = false;
    void fetchSettings(fetchImpl).then((next) => {
      if (!cancelled) {
        setSettings(next);
      }
    });
    return () => {
      cancelled = true;
    };
  }, [fetchImpl]);

  async function handleToggle(calendarId: string, enabled: boolean) {
    if (!settings) {
      return;
    }
    const calendars = settings.calendars.map((calendar) =>
      calendar.id === calendarId ? { ...calendar, enabled } : calendar,
    );
    const optimistic = withScheduledSync(calendars);
    optimistic.apple_permissions = settings.apple_permissions;
    setSettings(optimistic);
    setSaving(true);
    setError(null);
    try {
      const enabledIds = calendars.filter((c) => c.enabled).map((c) => c.id);
      const persisted = await persistCalendarSelection(enabledIds, fetchImpl);
      setSettings(persisted);
    } catch {
      setSettings(settings);
      setError("Could not save calendar selection. Changes were reverted.");
    } finally {
      setSaving(false);
    }
  }

  if (!settings) {
    return (
      <section className="page">
        <h1>Settings</h1>
        <p>Loading settings…</p>
      </section>
    );
  }

  return (
    <section className="page">
      <h1>Settings</h1>
      <p>Select calendars to watch and review Apple data permissions.</p>
      {error ? <p role="alert">{error}</p> : null}
      <CalendarSelection
        calendars={settings.calendars}
        onToggle={(id, enabled) => {
          void handleToggle(id, enabled);
        }}
        disabled={saving}
      />
      <p className="sync-summary">
        Scheduled for sync:{" "}
        {settings.scheduled_for_sync.length > 0
          ? settings.scheduled_for_sync.join(", ")
          : "none"}
      </p>
      <ApplePermissions permissions={settings.apple_permissions} />
    </section>
  );
}
