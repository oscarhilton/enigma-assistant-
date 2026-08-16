export const DEMO_BANNER_TEXT = "DEMO MODE — FICTIONAL DATA ONLY";

export type DemoModeBannerProps = {
  /** When true, render the unmistakable Demo Mode label. */
  active?: boolean;
  scenarioLabel?: string;
};

/**
 * Persistent Demo Mode label. Force `active` on `/demo/*` chrome; otherwise
 * enable via prop or `import.meta.env.VITE_ENIGMA_MODE === "demo"`.
 */
export function DemoModeBanner({
  active,
  scenarioLabel = "Alex Morgan v1",
}: DemoModeBannerProps) {
  const envActive =
    typeof import.meta !== "undefined" &&
    import.meta.env?.VITE_ENIGMA_MODE === "demo";
  const show = active ?? envActive;
  if (!show) {
    return null;
  }

  return (
    <aside className="demo-banner" role="status" aria-live="polite">
      <strong>{DEMO_BANNER_TEXT}</strong>
      <span>Scenario: {scenarioLabel}</span>
    </aside>
  );
}
