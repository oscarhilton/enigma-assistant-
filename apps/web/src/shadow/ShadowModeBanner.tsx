export const SHADOW_BANNER_TEXT =
  "SHADOW MODE — OBSERVATION ONLY · NOTIFICATIONS OFF";

export type ShadowModeBannerProps = {
  /** When true, render the unmistakable Shadow Mode label. */
  active?: boolean;
};

/**
 * Persistent Shadow Mode label. Enable via prop or
 * `import.meta.env.VITE_ENIGMA_MODE === "shadow"`.
 */
export function ShadowModeBanner({ active }: ShadowModeBannerProps) {
  const envActive =
    typeof import.meta !== "undefined" &&
    import.meta.env?.VITE_ENIGMA_MODE === "shadow";
  const show = active ?? envActive;
  if (!show) {
    return null;
  }

  return (
    <aside className="shadow-banner" role="status" aria-live="polite">
      <strong>{SHADOW_BANNER_TEXT}</strong>
    </aside>
  );
}
