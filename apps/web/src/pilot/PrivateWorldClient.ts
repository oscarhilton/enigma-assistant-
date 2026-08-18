import type { EnigmaClient } from "../enigma/client";
import type { EnigmaEventHandler } from "../enigma/events";
import type {
  AssistProposal,
  AssistResult,
  AttentionState,
  ConversationItem,
  ConversationTurn,
  DemoEvent,
  EgressDisclosure,
  ProvenanceView,
  QualificationDebug,
} from "../enigma/types";

const API_BASE = (import.meta.env.VITE_API_BASE as string | undefined)?.replace(/\/$/, "") ?? "";

const SILENCE: AttentionState = {
  simulated_time: new Date(0).toISOString(),
  checkpoint_id: null,
  needs_you: [],
  context: [],
  next_actions: [],
  can_wait_summary: null,
  presentation: {
    chat_opening_count: 0,
    notification_slot_count: 0,
    proactive_silence: true,
  },
};

async function readJson<T>(response: Response): Promise<T> {
  const url = response.url || "(unknown url)";
  const text = await response.text();
  if (!response.ok) {
    throw new Error(`HTTP ${response.status} ${url}`);
  }
  return JSON.parse(text) as T;
}

/** Live My Enigma client — quiet until P03 connects Calendar. */
export class PrivateWorldClient implements EnigmaClient {
  private handlers = new Set<EnigmaEventHandler>();

  isDemo(): boolean {
    return false;
  }

  subscribe(handler: EnigmaEventHandler): () => void {
    this.handlers.add(handler);
    return () => this.handlers.delete(handler);
  }

  private emit(event: Parameters<EnigmaEventHandler>[0]): void {
    for (const handler of this.handlers) {
      handler(event);
    }
  }

  async getConversation(): Promise<ConversationItem[]> {
    const body = await readJson<{ items: ConversationItem[] }>(
      await fetch(`${API_BASE}/worlds/my_enigma/conversation`),
    );
    return body.items;
  }

  async sendMessage(text: string): Promise<ConversationTurn> {
    const body = await readJson<ConversationTurn>(
      await fetch(`${API_BASE}/worlds/my_enigma/conversation/message`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ text }),
      }),
    );
    this.emit({ type: "conversation_updated" });
    return body;
  }

  async getAttentionState(): Promise<AttentionState> {
    try {
      return await readJson<AttentionState>(
        await fetch(`${API_BASE}/worlds/my_enigma/attention/state`),
      );
    } catch {
      return { ...SILENCE, simulated_time: new Date().toISOString() };
    }
  }

  async getQualificationDebug(_itemId: string): Promise<QualificationDebug> {
    throw new Error("Qualification debug unavailable until a private source is connected");
  }

  async getProvenance(_itemId: string): Promise<ProvenanceView> {
    throw new Error("Provenance unavailable until a private source is connected");
  }

  async proposeAssist(_intent: string): Promise<AssistProposal> {
    throw new Error("Assist is not available in My Enigma until a private source is connected");
  }

  async approveAssist(_proposalId: string): Promise<AssistResult> {
    throw new Error("Assist is not available in My Enigma until a private source is connected");
  }

  async jumpCheckpoint(_checkpointId: string): Promise<void> {
    throw new Error("My Enigma uses the real clock; checkpoints are Alex Lab only");
  }

  async listCheckpoints(): Promise<{ id: string; at: string; label: string }[]> {
    return [];
  }

  async getDemoEvents(): Promise<DemoEvent[]> {
    return [];
  }

  async getRecentDisclosures(): Promise<EgressDisclosure[]> {
    return [];
  }
}
