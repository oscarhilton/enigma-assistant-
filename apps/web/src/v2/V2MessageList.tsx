import type { ConversationItem } from "../enigma/types";

/** Projection rows for v2 message list — structured for streaming append in UI2-02. */
export type V2MessageRow =
  | { id: string; role: "user"; text: string; at?: string }
  | { id: string; role: "assistant"; text: string; at?: string; streaming?: boolean }
  | { id: string; role: "status"; text: string; at?: string };

export function projectConversationItems(items: ConversationItem[]): V2MessageRow[] {
  const rows: V2MessageRow[] = [];
  for (let index = 0; index < items.length; index += 1) {
    const item = items[index]!;
    const id = `${item.kind}-${index}`;
    switch (item.kind) {
      case "user_message":
        rows.push({ id, role: "user", text: item.text, at: item.at });
        break;
      case "enigma_message":
        rows.push({ id, role: "assistant", text: item.text, at: item.at, streaming: false });
        break;
      case "status":
        rows.push({ id, role: "status", text: item.text, at: item.at });
        break;
      default:
        break;
    }
  }
  return rows;
}
