/** Build identity shown in v2 chrome — injected at build time via vite.config.ts */
export function buildIdentityLabel(): string {
  const commit =
    (import.meta.env.VITE_BUILD_COMMIT as string | undefined)?.trim() || "dev";
  return `Enigma v2 · ${commit}`;
}
