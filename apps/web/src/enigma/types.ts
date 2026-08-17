/** Shared Enigma client contract — Demo and Live use identical types. */

export type PolicyDecision = "surface" | "context" | "suppress";
export type AttentionBucket = "needs_you" | "context" | "can_wait";

export type AttentionReason = {
  code: string;
  label: string;
};

export type AttentionItem = {
  id: string;
  title: string;
  explanation: string;
  policy_decision: PolicyDecision;
  bucket: AttentionBucket;
  rank?: number | null;
  composite_score?: number | null;
  actionability_now?: number | null;
  reasons: AttentionReason[];
  evidence_ids: string[];
  state_changed_at?: string | null;
};

export type NextActionView = {
  id: string;
  title: string;
  reason: string;
  optional: true;
  estimated_minutes?: number | null;
  source_candidate_id?: string | null;
};

export type CanWaitSummary = {
  total_suppressed: number;
  sample_titles: string[];
};

export type PresentationPlan = {
  chat_opening_count: number;
  notification_slot_count: number;
  proactive_silence: boolean;
};

/** Attention ≠ Next Action. Context is not WORTH DOING. */
export type AttentionState = {
  simulated_time: string;
  checkpoint_id?: string | null;
  needs_you: AttentionItem[];
  context: AttentionItem[];
  next_actions: NextActionView[];
  can_wait_summary?: CanWaitSummary | null;
  presentation: PresentationPlan;
};

export type QualificationDebug = {
  item_id: string;
  checkpoint_id: string;
  policy_decision: PolicyDecision;
  composite_score: number;
  surface_threshold: number;
  context_threshold: number;
  obligation_strength: number;
  user_responsibility: number;
  importance: number;
  time_sensitivity: number;
  actionability_now: number;
  confidence: number;
  overdue_boost: number;
  near_term_boost: number;
  calendar_boost: number;
  noise_multiplier: number;
  eligible_for_needs_you: boolean;
  policy_reason?: string | null;
  reason_codes: string[];
};

export type LlmTracePath = "intent_router" | "llm" | "fireworks" | "openai";

export type LlmTraceToolCall = {
  name: string;
  arguments: Record<string, unknown>;
};

export type LlmTraceToolResult = {
  name: string;
  ok: boolean;
  data: Record<string, unknown>;
};

export type LlmTraceDisclosure = {
  id: string;
  provider: string;
  purpose: string;
  model: string;
  payload_hash: string;
  payload_field_summary: Record<string, unknown>;
  blocked: boolean;
  block_reason?: string | null;
  included?: string[];
  excluded?: string[];
  outbound_payload?: Record<string, unknown> | null;
  transport_endpoint?: string | null;
};

/** Deterministic turn trace — input → context → tool → result → response. Not chain-of-thought. */
export type LlmTrace = {
  path: LlmTracePath;
  planner: string;
  user_message: string;
  conversation_state: {
    current_subject_id?: string | null;
    current_subject_kind?: string | null;
  };
  tools_available: string[];
  remote_context_sent?: Record<string, unknown> | null;
  model_tool_request: LlmTraceToolCall[];
  referent_resolution?: {
    tool: string;
    source: string;
    bound_id?: string | null;
    summary: string;
    model_arguments?: Record<string, unknown>;
    executed_arguments?: Record<string, unknown>;
  }[];
  executed_tool_request?: LlmTraceToolCall[];
  tool_results: LlmTraceToolResult[];
  model_response: { kind: string; text?: string | null }[];
  intent_name?: string | null;
  router_fallback?: boolean;
  disclosure_id?: string | null;
  disclosure?: LlmTraceDisclosure | null;
  included?: string[];
  excluded?: string[];
  correlation_id?: string | null;
};

type ConversationStamp = {
  at: string;
  llm_trace?: LlmTrace;
  correlation_id?: string;
};

export type ConversationItem =
  | ({ kind: "user_message"; text: string } & ConversationStamp)
  | ({ kind: "enigma_message"; text: string } & ConversationStamp)
  | ({ kind: "attention_item"; item: AttentionItem } & ConversationStamp)
  | ({ kind: "attention_summary"; state: AttentionState; text?: string } & ConversationStamp)
  | ({ kind: "next_action"; action: NextActionView } & ConversationStamp)
  | ({ kind: "assist_proposal"; proposal: AssistProposal } & ConversationStamp)
  | ({ kind: "assist_result"; proposal_id: string; ok: boolean; message: string } & ConversationStamp)
  | ({ kind: "provenance"; ref: ProvenanceView } & ConversationStamp)
  | ({ kind: "status"; text: string } & ConversationStamp);

export type AssistProposal = {
  id: string;
  title: string;
  description: string;
  action_label: string;
};

export type AssistResult = {
  ok: boolean;
  message: string;
};

export type ProvenanceView = {
  item_id: string;
  headline: string;
  evidence: string[];
  inference: string[];
  decision: string[];
  why_now: string[];
  reason_codes: string[];
};

export type DemoCheckpoint = {
  id: string;
  at: string;
  label: string;
};

export type DemoEvent = {
  kind: string;
  at: string;
  checkpoint_id?: string;
  proactive_silence?: boolean;
  needs_you_count?: number;
};

export type ConversationTurn = {
  items: ConversationItem[];
  conversation: { items: ConversationItem[] };
  llm_trace?: LlmTrace;
  debug?: LlmTrace;
};

export type Unsubscribe = () => void;

export type EnigmaAction = {
  name: string;
  effect: "allowed" | "denied" | "no_side_effect";
  side_effect?: boolean;
  reason?: string | null;
  ok?: boolean;
};

export type ToolTraceHop = {
  request?: { name?: string; arguments?: Record<string, unknown> };
  result?: { name?: string; ok?: boolean; data?: Record<string, unknown> };
};

/** Audited egress disclosure — exact remote-safe payload plus forensic hops (SEC-02 / C09). */
export type EgressDisclosure = {
  id: string;
  correlation_id: string;
  timestamp: string;
  purpose: string;
  provider: string;
  model: string;
  transformation_profile: string;
  payload_field_summary: Record<string, unknown>;
  payload_hash: string;
  byte_count: number;
  blocked: boolean;
  block_reason?: string | null;
  classification: string;
  prompt_tokens: number;
  completion_tokens: number;
  outbound_payload?: Record<string, unknown> | null;
  provider_response?: Record<string, unknown> | null;
  transport_endpoint?: string | null;
  included?: string[];
  excluded?: string[];
  denied_capabilities?: string[];
  tool_trace?: ToolTraceHop[];
  enigma_actions?: EnigmaAction[];
};
