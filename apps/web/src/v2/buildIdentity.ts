/** Git commit injected at build time via vite.config.ts */
export function buildCommitLabel(): string {
  return (import.meta.env.VITE_BUILD_COMMIT as string | undefined)?.trim() || "dev";
}

/** Build identity shown in v2 chrome — injected at build time via vite.config.ts */
export function buildIdentityLabel(): string {
  return `Enigma v2 · ${buildCommitLabel()}`;
}
