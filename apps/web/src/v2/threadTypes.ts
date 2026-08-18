import type { ConversationItem } from "../enigma/types";

export type V2Thread = {
  id: string;
  title: string;
  items: ConversationItem[];
  updatedAt: string;
};

export const NEW_CHAT_TITLE = "New chat";

export function threadTitleFromMessage(text: string): string {
  const trimmed = text.trim();
  if (!trimmed) {
    return NEW_CHAT_TITLE;
  }
  return trimmed.length > 48 ? `${trimmed.slice(0, 45)}…` : trimmed;
}

function conversationHead(items: ConversationItem[]): ConversationItem | undefined {
  return items[0];
}

function headsMatch(a: ConversationItem[], b: ConversationItem[]): boolean {
  const headA = conversationHead(a);
  const headB = conversationHead(b);
  if (!headA || !headB) {
    return headA === headB;
  }
  return headA === headB || JSON.stringify(headA) === JSON.stringify(headB);
}

/** Reconcile sidebar title when conversation items change (checkpoint jumps, etc.). */
export function reconcileThreadTitleOnItemsChange(
  previousItems: ConversationItem[],
  nextItems: ConversationItem[],
  currentTitle: string,
): string {
  if (nextItems.length === 0) {
    return NEW_CHAT_TITLE;
  }

  const wholesaleReplace =
    previousItems.length > 0 &&
    nextItems.length > 0 &&
    (nextItems.length < previousItems.length || !headsMatch(previousItems, nextItems));

  if (wholesaleReplace) {
    const firstUser = nextItems.find((item) => item.kind === "user_message");
    return firstUser ? threadTitleFromMessage(firstUser.text) : NEW_CHAT_TITLE;
  }

  if (currentTitle === NEW_CHAT_TITLE) {
    const firstUser = nextItems.find((item) => item.kind === "user_message");
    return firstUser ? threadTitleFromMessage(firstUser.text) : NEW_CHAT_TITLE;
  }

  return currentTitle;
}

export function createThread(id?: string): V2Thread {
  const now = new Date().toISOString();
  return {
    id: id ?? crypto.randomUUID(),
    title: NEW_CHAT_TITLE,
    items: [],
    updatedAt: now,
  };
}
