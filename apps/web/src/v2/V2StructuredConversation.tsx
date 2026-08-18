import { Fragment, type ReactNode } from "react";
import { ActivityStrip } from "../enigma/ActivityStrip";
import { threadActivityFromTrace } from "../enigma/activity";
import { AssistProposalView } from "../enigma/items/AssistProposalView";
import { AttentionItemView } from "../enigma/items/AttentionItemView";
import { AttentionSummaryView } from "../enigma/items/AttentionSummaryView";
import { NextActionView } from "../enigma/items/NextActionView";
import { ProvenanceViewPanel } from "../enigma/items/ProvenanceViewPanel";
import type { ConversationItem, LlmTrace } from "../enigma/types";

type Props = {
  items: ConversationItem[];
  onWhy?: (itemId: string) => void;
  onQualificationDebug?: (itemId: string) => void;
  onHelpAssist?: () => void;
  onApproveAssist?: (proposalId: string) => void | Promise<void>;
  demoMode?: boolean;
};

function isAssistantItem(item: ConversationItem): boolean {
  return item.kind !== "user_message";
}

function isRunEnd(items: ConversationItem[], index: number): boolean {
  if (!isAssistantItem(items[index]!)) {
    return false;
  }
  const next = items[index + 1];
  return next === undefined || next.kind === "user_message";
}

function traceForRunEndingAt(items: ConversationItem[], endIndex: number): LlmTrace | undefined {
  let start = endIndex;
  while (start > 0 && isAssistantItem(items[start - 1]!)) {
    start -= 1;
  }
  for (let i = start; i <= endIndex; i += 1) {
    const trace = items[i]?.llm_trace;
    if (trace) {
      return trace;
    }
  }
  return undefined;
}

/** Alex Lab structured turns — attention, assist, activity (Life Scripts). */
export function V2StructuredConversation({
  items,
  onWhy,
  onQualificationDebug,
  onHelpAssist,
  onApproveAssist,
  demoMode = false,
}: Props) {
  const approvedIds = new Set(
    items
      .filter((item): item is Extract<ConversationItem, { kind: "assist_result" }> => {
        return item.kind === "assist_result" && item.ok;
      })
      .map((item) => item.proposal_id),
  );

  function renderItem(item: ConversationItem, index: number): ReactNode {
    const key = `${item.kind}-${index}`;
    switch (item.kind) {
      case "user_message":
        return (
          <article
            key={key}
            className="v2-message v2-message--user"
            data-testid="v2-message-user"
          >
            <div className="v2-message-bubble">{item.text}</div>
          </article>
        );
      case "enigma_message":
        return (
          <article
            key={key}
            className="v2-message v2-message--assistant"
            data-testid="v2-message-assistant"
            data-streaming="false"
          >
            <p>{item.text}</p>
          </article>
        );
      case "status":
        return (
          <p key={key} className="v2-message v2-message--status" data-testid="v2-message-status">
            {item.text}
          </p>
        );
      case "attention_summary":
        return (
          <div key={key} data-testid="v2-attention-surface">
            <AttentionSummaryView
              state={item.state}
              at={item.at}
              onWhy={onWhy}
              onQualificationDebug={onQualificationDebug}
              onHelpAssist={onHelpAssist}
              demoMode={demoMode}
            />
          </div>
        );
      case "attention_item":
        return (
          <AttentionItemView
            key={key}
            item={item.item}
            onWhy={onWhy}
            onQualificationDebug={onQualificationDebug}
            demoMode={demoMode}
          />
        );
      case "next_action":
        return (
          <NextActionView
            key={key}
            action={item.action}
            sourceItemId={item.action.source_candidate_id}
            onWhy={onWhy}
            onHelpAssist={onHelpAssist}
          />
        );
      case "assist_proposal":
        return (
          <AssistProposalView
            key={key}
            proposal={item.proposal}
            onApprove={onApproveAssist}
            approved={approvedIds.has(item.proposal.id)}
          />
        );
      case "assist_result":
        return (
          <p
            key={key}
            className={`v2-message v2-message--status${item.ok ? "" : " v2-message--error"}`}
            data-testid="assist-result"
          >
            {item.message}
          </p>
        );
      case "provenance":
        return <ProvenanceViewPanel key={key} provenance={item.ref} />;
      default:
        return null;
    }
  }

  return (
    <>
      {items.map((item, index) => {
        const runEnded = isRunEnd(items, index);
        const runTrace = runEnded ? traceForRunEndingAt(items, index) : undefined;
        const activities = runTrace ? threadActivityFromTrace(runTrace, { at: item.at }) : [];
        return (
          <Fragment key={`run-${index}`}>
            {renderItem(item, index)}
            {activities.length > 0 ? <ActivityStrip events={activities} /> : null}
          </Fragment>
        );
      })}
    </>
  );
}
