export type CalendarSource = {
  id: string;
  name: string;
  provider: string;
  enabled: boolean;
};

export type ApplePermissionPlaceholder = {
  id: string;
  label: string;
  status: string;
  detail: string;
};

export type SettingsState = {
  calendars: CalendarSource[];
  apple_permissions: ApplePermissionPlaceholder[];
  scheduled_for_sync: string[];
};
