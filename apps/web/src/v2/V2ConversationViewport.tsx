import { Skeleton } from "../components/ui/skeleton";
import { ScrollArea } from "../components/ui/scroll-area";
import type { ConversationItem } from "../enigma/types";
import { projectConversationItems, type V2MessageRow } from "./V2MessageList";
import { V2StructuredConversation } from "./V2StructuredConversation";

export type { V2MessageRow };

type V2AssistantRow = Extract<V2MessageRow, { role: "assistant" }>;

type Props = {
  items: ConversationItem[];
  loading?: boolean;
  streamingRow?: V2MessageRow | null;
  demoMode?: boolean;
  onWhy?: (itemId: string) => void;
  onQualificationDebug?: (itemId: string) => void;
  onHelpAssist?: () => void;
  onApproveAssist?: (proposalId: string) => void | Promise<void>;
};

export function appendStreamingText(current: V2MessageRow | null, delta: string): V2AssistantRow {
  if (current?.role === "assistant") {
    return { ...current, text: `${current.text}${delta}`, streaming: true };
  }
  return {
    id: "streaming-assistant",
    role: "assistant",
    text: delta,
    streaming: true,
  };
}

function StreamingBubble({ row }: { row: V2MessageRow }) {
  if (row.role !== "assistant") {
    return null;
  }
  return (
    <article
      className="v2-message v2-message--assistant"
      data-testid="v2-message-assistant"
      data-streaming={row.streaming ? "true" : "false"}
    >
      <p>{row.text}</p>
    </article>
  );
}

function hasStructuredItems(items: ConversationItem[]): boolean {
  return items.some(
    (item) =>
      item.kind === "attention_summary" ||
      item.kind === "attention_item" ||
      item.kind === "assist_proposal" ||
      item.kind === "assist_result" ||
      item.kind === "next_action" ||
      item.kind === "provenance",
  );
}

export function V2ConversationViewport({
  items,
  loading = false,
  streamingRow = null,
  demoMode = false,
  onWhy,
  onQualificationDebug,
  onHelpAssist,
  onApproveAssist,
}: Props) {
  const structured = hasStructuredItems(items) || demoMode;

  if (loading) {
    return (
      <div className="v2-messages" data-testid="v2-conversation">
        <p className="sr-only">Loading conversation…</p>
        <div className="max-w-xl mx-auto space-y-3 pt-4" data-testid="v2-conversation-skeleton">
          <Skeleton className="h-4 w-2/3" />
          <Skeleton className="h-4 w-1/2" />
          <Skeleton className="h-4 w-3/5" />
        </div>
      </div>
    );
  }

  if (items.length === 0 && !streamingRow) {
    return (
      <div className="v2-messages" data-testid="v2-conversation">
        <p className="text-sm text-muted-foreground max-w-lg mx-auto text-center pt-8">
          Ask Enigma anything. Answers come from your world — not chat history alone.
        </p>
      </div>
    );
  }

  return (
    <ScrollArea className="v2-messages" data-testid="v2-conversation">
      <div className="pb-4">
        {structured ? (
          <V2StructuredConversation
            items={items}
            demoMode={demoMode}
            onWhy={onWhy}
            onQualificationDebug={onQualificationDebug}
            onHelpAssist={onHelpAssist}
            onApproveAssist={onApproveAssist}
          />
        ) : (
          projectConversationItems(items).map((row) => {
            if (row.role === "user") {
              return (
                <article key={row.id} className="v2-message v2-message--user" data-testid="v2-message-user">
                  <div className="v2-message-bubble">{row.text}</div>
                </article>
              );
            }
            if (row.role === "assistant") {
              return (
                <article
                  key={row.id}
                  className="v2-message v2-message--assistant"
                  data-testid="v2-message-assistant"
                  data-streaming="false"
                >
                  <p>{row.text}</p>
                </article>
              );
            }
            return (
              <p key={row.id} className="v2-message v2-message--status" data-testid="v2-message-status">
                {row.text}
              </p>
            );
          })
        )}
        {streamingRow ? <StreamingBubble row={streamingRow} /> : null}
      </div>
    </ScrollArea>
  );
}
