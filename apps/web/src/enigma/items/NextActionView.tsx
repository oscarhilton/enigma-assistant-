import type { NextActionView as NextActionType } from "../types";

type Props = {
  action: NextActionType;
  coalescedFromContext?: boolean;
  sourceItemId?: string | null;
  onWhy?: (itemId: string) => void;
  onHelpAssist?: () => void;
};

export function NextActionView({
  action,
  coalescedFromContext = false,
  sourceItemId,
  onWhy,
  onHelpAssist,
}: Props) {
  return (
    <article className="next-action-item">
      {coalescedFromContext ? (
        <span className="next-action-context-hint">Context · Optional</span>
      ) : null}
      <h3>{action.title}</h3>
      <p>{action.reason}</p>
      <div className="next-action-actions">
        {onWhy && sourceItemId ? (
          <button type="button" onClick={() => onWhy(sourceItemId)}>
            Why now?
          </button>
        ) : null}
        {onHelpAssist ? (
          <button type="button" onClick={onHelpAssist}>
            Help me do this
          </button>
        ) : null}
      </div>
    </article>
  );
}
