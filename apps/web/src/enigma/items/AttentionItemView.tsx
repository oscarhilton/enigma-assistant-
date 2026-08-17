import type { AttentionItem } from "../types";

const BUCKET_LABEL: Record<AttentionItem["bucket"], string> = {
  needs_you: "NEEDS YOU",
  context: "CONTEXT",
  can_wait: "CAN WAIT",
};

type Props = {
  item: AttentionItem;
  variant?: "primary" | "quiet";
  onWhy?: (itemId: string) => void;
  onQualificationDebug?: (itemId: string) => void;
  demoMode?: boolean;
};

export function AttentionItemView({
  item,
  variant = "primary",
  onWhy,
  onQualificationDebug,
  demoMode = false,
}: Props) {
  const showBadge = variant === "primary";

  return (
    <article
      className={`attention-item${variant === "quiet" ? " attention-item--quiet" : ""}`}
      data-bucket={item.bucket}
    >
      <header>
        {showBadge ? (
          <span className="attention-badge">{BUCKET_LABEL[item.bucket]}</span>
        ) : null}
        <h3>{item.title}</h3>
      </header>
      <p>{item.explanation}</p>
      <div className="attention-actions">
        {onWhy ? (
          <button type="button" onClick={() => onWhy(item.id)}>
            Why now?
          </button>
        ) : null}
        {demoMode && item.bucket === "context" && onQualificationDebug ? (
          <button type="button" onClick={() => onQualificationDebug(item.id)}>
            Why isn&apos;t this in NEEDS YOU?
          </button>
        ) : null}
      </div>
    </article>
  );
}
