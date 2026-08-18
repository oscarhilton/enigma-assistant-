import type { GoosePixelLicence } from "./goosePixels";

type Props = {
  licence: GoosePixelLicence;
  onInspect?: () => void;
};

function inspectName(licence: GoosePixelLicence): string {
  const label = licence.inspectLabels[0] ?? "this work";
  return `Explain ${label}`;
}

function GooseMark() {
  return (
    <svg
      className="goose-mark"
      viewBox="0 0 20 16"
      width="20"
      height="16"
      aria-hidden="true"
      focusable="false"
    >
      <ellipse cx="8" cy="11" rx="6" ry="3.2" />
      <circle cx="13.5" cy="6.2" r="3.1" />
      <rect x="16.2" y="5.4" width="3.2" height="1.4" rx="0.4" />
    </svg>
  );
}

export function GoosePresence({ licence, onInspect }: Props) {
  if (licence.motion === "absent") {
    return null;
  }

  return (
    <div
      className="goose-rail"
      data-testid="surface-goose"
      data-layer="surface"
      data-motion={licence.motion}
      data-expressiveness={licence.expressiveness}
      data-authority="none"
      data-evidence="false"
    >
      <button
        type="button"
        className={`goose-sprite goose-sprite--${licence.motion} goose-sprite--${licence.expressiveness}`}
        onClick={() => onInspect?.()}
        aria-label={inspectName(licence)}
      >
        <GooseMark />
      </button>
    </div>
  );
}
