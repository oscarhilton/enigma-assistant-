import { Fragment, type ReactNode } from "react";
import { ActivityStrip } from "./ActivityStrip";
import { EvidenceCourier } from "./EvidenceCourier";
import { threadActivityFromTrace } from "./activity";
import { AssistProposalView } from "./items/AssistProposalView";
import { AttentionItemView } from "./items/AttentionItemView";
import { AttentionSummaryView } from "./items/AttentionSummaryView";
import { NextActionView } from "./items/NextActionView";
import { ProvenanceViewPanel } from "./items/ProvenanceViewPanel";
import { TurnTracePanel } from "./TurnTracePanel";
import type { ConversationItem, LlmTrace } from "./types";

type Props = {
  items: ConversationItem[];
  loading?: boolean;
  onWhy?: (itemId: string) => void;
  onQualificationDebug?: (itemId: string) => void;
  onHelpAssist?: () => void;
  onApproveAssist?: (proposalId: string) => void | Promise<void>;
  demoMode?: boolean;
  showUnderBonnet?: boolean;
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

export function ConversationViewport({
  items,
  loading = false,
  onWhy,
  onQualificationDebug,
  onHelpAssist,
  onApproveAssist,
  demoMode = false,
  showUnderBonnet = false,
}: Props) {
  const approvedIds = new Set(
    items
      .filter((item): item is Extract<ConversationItem, { kind: "assist_result" }> => {
        return item.kind === "assist_result" && item.ok;
      })
      .map((item) => item.proposal_id),
  );

  if (loading) {
    return (
      <div className="conversation-viewport" data-testid="conversation-viewport">
        <p className="conversation-empty" aria-busy="true">
          Loading conversation…
        </p>
      </div>
    );
  }

  if (items.length === 0) {
    return (
      <div className="conversation-viewport" data-testid="conversation-viewport">
        <p className="conversation-empty">
          Ask Enigma what needs you — answers come from world state, not chat history.
        </p>
      </div>
    );
  }

  const underBonnet = demoMode && showUnderBonnet;

  function renderItem(item: ConversationItem): ReactNode {
    switch (item.kind) {
      case "user_message":
        return <p className="conversation-line conversation-line--user">{item.text}</p>;
      case "enigma_message":
        return <p className="conversation-line conversation-line--enigma">{item.text}</p>;
      case "status":
        return <p className="conversation-line conversation-line--status">{item.text}</p>;
      case "source_quote":
        return (
          <blockquote className="conversation-line conversation-line--quote" data-testid="source-quote">
            {item.text}
          </blockquote>
        );
      case "attention_summary":
        return (
          <AttentionSummaryView
            state={item.state}
            at={item.at}
            onWhy={onWhy}
            onQualificationDebug={onQualificationDebug}
            onHelpAssist={onHelpAssist}
            demoMode={demoMode}
          />
        );
      case "attention_item":
        return (
          <AttentionItemView
            item={item.item}
            onWhy={onWhy}
            onQualificationDebug={onQualificationDebug}
            demoMode={demoMode}
          />
        );
      case "next_action":
        return (
          <NextActionView
            action={item.action}
            sourceItemId={item.action.source_candidate_id}
            onWhy={onWhy}
            onHelpAssist={onHelpAssist}
          />
        );
      case "assist_proposal":
        return (
          <AssistProposalView
            proposal={item.proposal}
            onApprove={onApproveAssist}
            approved={approvedIds.has(item.proposal.id)}
          />
        );
      case "assist_result":
        return (
          <p
            className={`conversation-line conversation-line--status${
              item.ok ? " conversation-line--success" : " conversation-line--error"
            }`}
            data-testid="assist-result"
          >
            {item.message}
          </p>
        );
      case "provenance":
        return <ProvenanceViewPanel provenance={item.ref} />;
      default:
        return null;
    }
  }

  return (
    <div className="conversation-viewport" data-testid="conversation-viewport">
      {items.map((item, index) => {
        const key = `${item.kind}-${index}`;
        const runEnded = isRunEnd(items, index);
        const runTrace = runEnded ? traceForRunEndingAt(items, index) : undefined;
        const activities = runTrace ? threadActivityFromTrace(runTrace, { at: item.at }) : [];
        const bundle = runTrace?.evidence_bundle ?? null;
        const forensicTrace = underBonnet ? runTrace : undefined;
        return (
          <Fragment key={key}>
            {renderItem(item)}
            {bundle ? (
              <EvidenceCourier bundle={bundle} />
            ) : activities.length > 0 ? (
              <ActivityStrip events={activities} />
            ) : null}
            {forensicTrace ? <TurnTracePanel trace={forensicTrace} /> : null}
          </Fragment>
        );
      })}
    </div>
  );
}
