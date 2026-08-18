import type { AttentionState } from "../types";
import { AttentionItemView } from "./AttentionItemView";
import { NextActionView } from "./NextActionView";
import { RadarItemRow } from "./RadarItemRow";

type Props = {
  state: AttentionState;
  at: string;
  onWhy?: (itemId: string) => void;
  onQualificationDebug?: (itemId: string) => void;
  onHelpAssist?: () => void;
  demoMode?: boolean;
};

function nextActionSourceIds(state: AttentionState): Set<string> {
  return new Set(
    state.next_actions
      .map((action) => action.source_candidate_id)
      .filter((id): id is string => Boolean(id)),
  );
}

function radarSummaryLabel(count: number): string {
  if (count === 1) {
    return "1 other thing I'm keeping in mind";
  }
  return `Also on my radar · ${count}`;
}

export function AttentionSummaryView({
  state,
  onWhy,
  onQualificationDebug,
  onHelpAssist,
  demoMode = false,
}: Props) {
  const coalescedSourceIds = nextActionSourceIds(state);
  const radarItems = state.context.filter((item) => !coalescedSourceIds.has(item.id));

  const opening =
    state.presentation.chat_opening_count === 0
      ? "Nothing needs you."
      : state.presentation.chat_opening_count === 1
        ? "One thing needs you."
        : `${state.presentation.chat_opening_count} things need you.`;

  return (
    <section className="attention-summary" aria-label="Attention summary">
      <p className="conversation-line conversation-line--enigma">{opening}</p>
      {state.needs_you.map((item) => (
        <AttentionItemView
          key={item.id}
          item={item}
          variant="primary"
          onWhy={onWhy}
          onQualificationDebug={onQualificationDebug}
          demoMode={demoMode}
        />
      ))}
      {state.needs_you.length === 0 && state.next_actions.length > 0 ? (
        <>
          <p className="conversation-line conversation-line--enigma">
            A good thing you could do:
          </p>
          {state.next_actions.map((action) => {
            const sourceItemId = action.source_candidate_id ?? null;
            const coalescedFromContext =
              sourceItemId !== null && coalescedSourceIds.has(sourceItemId);
            return (
              <NextActionView
                key={action.id}
                action={action}
                coalescedFromContext={coalescedFromContext}
                sourceItemId={sourceItemId}
                onWhy={onWhy}
                onHelpAssist={onHelpAssist}
              />
            );
          })}
        </>
      ) : null}
      {radarItems.length > 0 ? (
        <details className="radar-panel">
          <summary>{radarSummaryLabel(radarItems.length)}</summary>
          {radarItems.map((item) => (
            <RadarItemRow
              key={item.id}
              item={item}
              onWhy={onWhy}
              onQualificationDebug={onQualificationDebug}
              demoMode={demoMode}
            />
          ))}
        </details>
      ) : null}
    </section>
  );
}
