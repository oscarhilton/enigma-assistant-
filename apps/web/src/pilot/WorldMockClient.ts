import type { EnigmaClient } from "../enigma/client";
import type { EnigmaEventHandler } from "../enigma/events";
import { MOCK_ATTENTION_JAN19, MOCK_LLM_TRACE_LLM } from "../enigma/fixtures";
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
import type { WorldId } from "./types";

/** Distinctive Alex Lab copy — WORLD_SWITCH_02 / CLOCK_01 canaries. */
export const ALEX_CONVERSATION_CANARY = "ALEX_LAB_CONVERSATION_MUST_NOT_LEAK";
export const ALEX_CASE_ID = "item-obligation_token_audit";
export const ALEX_SIMULATED_TIME = MOCK_ATTENTION_JAN19.simulated_time;

const ALEX_CONVERSATION: ConversationItem[] = [
  {
    kind: "enigma_message",
    text: ALEX_CONVERSATION_CANARY,
    at: ALEX_SIMULATED_TIME,
    llm_trace: MOCK_LLM_TRACE_LLM,
  },
];

const PRIVATE_ATTENTION: AttentionState = {
  simulated_time: "2026-08-18T16:45:00+00:00",
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

/** Per-world mock so leftover React state is observable in freeze tests. */
export class WorldMockClient implements EnigmaClient {
  readonly world: WorldId;
  private conversation: ConversationItem[];
  private state: AttentionState;
  private handlers = new Set<EnigmaEventHandler>();

  constructor(world: WorldId) {
    this.world = world;
    if (world === "alex_lab") {
      this.conversation = structuredClone(ALEX_CONVERSATION);
      this.state = structuredClone(MOCK_ATTENTION_JAN19);
    } else {
      this.conversation = [];
      this.state = structuredClone(PRIVATE_ATTENTION);
    }
  }

  static forWorld(world: WorldId): WorldMockClient {
    return new WorldMockClient(world);
  }

  isDemo(): boolean {
    return this.world === "alex_lab";
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
    throw new Error("Qualification debug unavailable in world mock");
  }

  async getProvenance(_itemId: string): Promise<ProvenanceView> {
    throw new Error("Provenance unavailable in world mock");
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
    return { ok: true, message: "Mock assist approved" };
  }

  async jumpCheckpoint(_checkpointId: string): Promise<void> {
    return;
  }

  async listCheckpoints(): Promise<{ id: string; at: string; label: string }[]> {
    if (this.world !== "alex_lab") {
      return [];
    }
    return [
      {
        id: MOCK_ATTENTION_JAN19.checkpoint_id ?? "cp-2026-01-19T10:00",
        at: ALEX_SIMULATED_TIME,
        label: "Mon 19 Jan",
      },
    ];
  }

  async getDemoEvents(): Promise<DemoEvent[]> {
    return [];
  }

  async getRecentDisclosures(_limit?: number): Promise<EgressDisclosure[]> {
    return [];
  }
}
