import { useState } from "react";
import type { AttentionItem } from "../types";

type Props = {
  item: AttentionItem;
  onWhy?: (itemId: string) => void;
  onQualificationDebug?: (itemId: string) => void;
  demoMode?: boolean;
};

export function RadarItemRow({
  item,
  onWhy,
  onQualificationDebug,
  demoMode = false,
}: Props) {
  const [expanded, setExpanded] = useState(false);

  return (
    <div className="radar-item">
      <button
        type="button"
        className="radar-item-title"
        aria-expanded={expanded}
        onClick={() => setExpanded((open) => !open)}
      >
        {item.title}
      </button>
      {expanded ? (
        <div className="radar-item-detail">
          <p>{item.explanation}</p>
          <div className="attention-actions">
            {onWhy ? (
              <button type="button" onClick={() => onWhy(item.id)}>
                Why now?
              </button>
            ) : null}
            {demoMode && onQualificationDebug ? (
              <button type="button" onClick={() => onQualificationDebug(item.id)}>
                Why isn&apos;t this in NEEDS YOU?
              </button>
            ) : null}
          </div>
        </div>
      ) : null}
    </div>
  );
}
