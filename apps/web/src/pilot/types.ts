export type WorldId = "alex_lab" | "my_enigma";

export type WorldView = {
  id: WorldId;
  label: string;
  subtitle: string;
  environment_mode: "demo" | "private";
  clock_kind: "simulation" | "system";
  resettable: boolean;
  persistent: boolean;
  storage_root: string;
  database_path: string;
  hmac_fingerprint: string;
  scenario: string | null;
};

export type WorldsPayload = {
  active: WorldId;
  worlds: WorldView[];
};

export const WORLD_LABELS: Record<WorldId, string> = {
  alex_lab: "Alex Lab",
  my_enigma: "My Enigma",
};

export const WORLD_SUBTITLES: Record<WorldId, string> = {
  alex_lab: "Synthetic world · controlled clock · resettable",
  my_enigma: "Private world · real clock · persistent",
};
