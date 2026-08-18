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
export const BRUNCH_CASE_ID = "item-obligation_brunch_book";
export const BRUNCH_CHECKPOINT_ID = "cp-2026-01-20T11:00";
export const BRUNCH_TITLE = "Book Saturday brunch for Elena's parents";
export const BRUNCH_CALENDAR_EVENT = "Brunch with Elena's parents";
export const BRUNCH_BOOKED_DISTINCTION =
  "Saturday has Brunch with Elena's parents, 11:00–13:00 — Book Saturday brunch for Elena's parents is still open. That calendar hold is not a reservation.";

const BRUNCH_ATTENTION: AttentionState = {
  simulated_time: "2026-01-20T11:00:00+00:00",
  checkpoint_id: BRUNCH_CHECKPOINT_ID,
  needs_you: [
    {
      id: BRUNCH_CASE_ID,
      title: BRUNCH_TITLE,
      explanation: "Elena's parents are visiting Saturday — the booking is still open.",
      policy_decision: "surface",
      bucket: "needs_you",
      rank: 1,
      composite_score: 1,
      actionability_now: 0.8,
      reasons: [
        { code: "USER_COMMITMENT", label: "You committed" },
        { code: "CALENDAR_PROXIMITY", label: "Calendar proximity" },
      ],
      evidence_ids: ["mail-elena-weekend", "rem-brunch-book", "cal-brunch-parents"],
    },
  ],
  context: [
    {
      id: "item-obligation_token_audit",
      title: "Draft colour + spacing token inventory",
      explanation: "Unblocked now — you could move this forward when you have a moment.",
      policy_decision: "context",
      bucket: "context",
      rank: 2,
      composite_score: 0.67,
      actionability_now: 0.9,
      reasons: [{ code: "UNBLOCKED", label: "Unblocked" }],
      evidence_ids: ["mail-jordan-tokens"],
    },
  ],
  next_actions: [],
  can_wait_summary: { total_suppressed: 1, sample_titles: [] },
  presentation: {
    chat_opening_count: 1,
    notification_slot_count: 1,
    proactive_silence: false,
  },
};

const BRUNCH_PROVENANCE: ProvenanceView = {
  item_id: BRUNCH_CASE_ID,
  headline: "WHY ENIGMA HOLDS THIS",
  evidence: ["mail-elena-weekend", "rem-brunch-book", "cal-brunch-parents"],
  inference: [
    "Talk in mail-elena-weekend is not a booking.",
    "cal-brunch-parents is a calendar hold, not a restaurant reservation.",
  ],
  decision: ["The reminder rem-brunch-book is still open."],
  why_now: [
    "Calendar hold cal-brunch-parents is not a reservation; rem-brunch-book is still open.",
  ],
  reason_codes: ["USER_COMMITMENT", "CALENDAR_PROXIMITY"],
};

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

  private emit(event: Parameters<EnigmaEventHandler>[0]): void {
    for (const handler of this.handlers) {
      handler(event);
    }
  }

  async getConversation(): Promise<ConversationItem[]> {
    return structuredClone(this.conversation);
  }

  async sendMessage(text: string): Promise<ConversationTurn> {
    const at = new Date().toISOString();
    this.conversation.push({ kind: "user_message", text, at });
    const brunchAsk = /what did i book/i.test(text);
    const onBrunch = this.state.checkpoint_id === BRUNCH_CHECKPOINT_ID;
    const reply: ConversationItem = {
      kind: "enigma_message",
      text:
        brunchAsk && onBrunch ? BRUNCH_BOOKED_DISTINCTION : `Mock reply to: ${text}`,
      at,
      llm_trace: brunchAsk && onBrunch ? MOCK_LLM_TRACE_LLM : undefined,
    };
    this.conversation.push(reply);
    this.emit({ type: "conversation_updated" });
    return { items: [reply], conversation: { items: structuredClone(this.conversation) } };
  }

  async getAttentionState(): Promise<AttentionState> {
    return structuredClone(this.state);
  }

  async getQualificationDebug(_itemId: string): Promise<QualificationDebug> {
    throw new Error("Qualification debug unavailable in world mock");
  }

  async getProvenance(itemId: string): Promise<ProvenanceView> {
    if (itemId === BRUNCH_CASE_ID) {
      return structuredClone(BRUNCH_PROVENANCE);
    }
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

  async jumpCheckpoint(checkpointId: string): Promise<void> {
    if (this.world !== "alex_lab") {
      throw new Error("My Enigma uses the real clock; checkpoints are Alex Lab only");
    }
    if (checkpointId === BRUNCH_CHECKPOINT_ID) {
      this.state = structuredClone(BRUNCH_ATTENTION);
      this.conversation = [
        {
          kind: "attention_summary",
          at: this.state.simulated_time,
          state: structuredClone(this.state),
        },
      ];
    } else {
      this.state = structuredClone(MOCK_ATTENTION_JAN19);
      this.conversation = structuredClone(ALEX_CONVERSATION);
    }
    this.emit({ type: "attention_changed", checkpoint_id: checkpointId });
    this.emit({ type: "conversation_updated" });
    this.emit({ type: "status_changed" });
  }

  async listCheckpoints(): Promise<{ id: string; at: string; label: string }[]> {
    if (this.world !== "alex_lab") {
      return [];
    }
    return [
      {
        id: MOCK_ATTENTION_JAN19.checkpoint_id ?? "cp-2026-01-19T10:00",
        at: ALEX_SIMULATED_TIME,
        label: "Jan 19 · 10:00",
      },
      {
        id: BRUNCH_CHECKPOINT_ID,
        at: BRUNCH_ATTENTION.simulated_time,
        label: "Jan 20 · 11:00",
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
