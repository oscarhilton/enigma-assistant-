import type { EnigmaClient } from "./client";
import type { EnigmaEventHandler } from "./events";
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
} from "./types";
import { MOCK_ATTENTION_JAN19, MOCK_CONVERSATION, MOCK_DISCLOSURES } from "./fixtures";

export class MockEnigmaClient implements EnigmaClient {
  private conversation = structuredClone(MOCK_CONVERSATION);
  private state = structuredClone(MOCK_ATTENTION_JAN19);
  private handlers = new Set<EnigmaEventHandler>();

  isDemo(): boolean {
    return false;
  }

  subscribe(handler: EnigmaEventHandler): () => void {
    this.handlers.add(handler);
    return () => this.handlers.delete(handler);
  }

  async getConversation(): Promise<ConversationItem[]> {
    return structuredClone(this.conversation);
  }

  async sendMessage(text: string): Promise<ConversationTurn> {
    const at = new Date().toISOString();
    this.conversation.push({ kind: "user_message", text, at });
    const reply: ConversationItem = {
      kind: "enigma_message",
      text: `Mock reply to: ${text}`,
      at,
    };
    this.conversation.push(reply);
    return { items: [reply], conversation: { items: structuredClone(this.conversation) } };
  }

  async getAttentionState(): Promise<AttentionState> {
    return structuredClone(this.state);
  }

  async getQualificationDebug(_itemId: string): Promise<QualificationDebug> {
    throw new Error("Qualification debug unavailable in mock client");
  }

  async getProvenance(_itemId: string): Promise<ProvenanceView> {
    throw new Error("Provenance unavailable in mock client");
  }

  async proposeAssist(intent: string): Promise<AssistProposal> {
    return {
      id: "mock-assist",
      title: intent,
      description: "Mock assist",
      action_label: "Approve",
    };
  }

  async approveAssist(proposalId: string): Promise<AssistResult> {
    const at = new Date().toISOString();
    const result: ConversationItem = {
      kind: "assist_result",
      proposal_id: proposalId,
      ok: true,
      message: "Mock assist approved",
      at,
    };
    this.conversation.push(result);
    for (const handler of this.handlers) {
      handler({ type: "conversation_updated" });
      handler({ type: "attention_changed", checkpoint_id: this.state.checkpoint_id ?? "" });
    }
    return { ok: true, message: "Mock assist approved" };
  }

  async jumpCheckpoint(_checkpointId: string): Promise<void> {
    return;
  }

  async listCheckpoints(): Promise<{ id: string; at: string; label: string }[]> {
    return [];
  }

  async getDemoEvents(): Promise<DemoEvent[]> {
    return [];
  }

  async getRecentDisclosures(_limit?: number): Promise<EgressDisclosure[]> {
    return structuredClone(MOCK_DISCLOSURES);
  }
}
