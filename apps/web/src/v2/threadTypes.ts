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

export function createThread(id?: string): V2Thread {
  const now = new Date().toISOString();
  return {
    id: id ?? crypto.randomUUID(),
    title: NEW_CHAT_TITLE,
    items: [],
    updatedAt: now,
  };
}
