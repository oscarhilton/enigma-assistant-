import { ScrollArea } from "../components/ui/scroll-area";
import type { ConversationItem } from "../enigma/types";
import { projectConversationItems, type V2MessageRow } from "./V2MessageList";

type Props = {
  items: ConversationItem[];
  loading?: boolean;
  /** Reserved for UI2-02 partial assistant text while streaming. */
  streamingRow?: V2MessageRow | null;
};

function MessageBubble({ row }: { row: V2MessageRow }) {
  if (row.role === "user") {
    return (
      <article className="v2-message v2-message--user" data-testid="v2-message-user">
        <div className="v2-message-bubble">{row.text}</div>
      </article>
    );
  }
  if (row.role === "assistant") {
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
  return (
    <p className="v2-message v2-message--status" data-testid="v2-message-status">
      {row.text}
    </p>
  );
}

export function V2ConversationViewport({ items, loading = false, streamingRow = null }: Props) {
  const rows = projectConversationItems(items);

  if (loading) {
    return (
      <div className="v2-messages" data-testid="v2-conversation">
        <p className="text-sm text-muted-foreground">Loading conversation…</p>
      </div>
    );
  }

  if (rows.length === 0 && !streamingRow) {
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
        {rows.map((row) => (
          <MessageBubble key={row.id} row={row} />
        ))}
        {streamingRow ? <MessageBubble row={streamingRow} /> : null}
      </div>
    </ScrollArea>
  );
}
