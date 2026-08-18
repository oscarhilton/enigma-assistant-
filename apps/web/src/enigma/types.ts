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
export type BuildIdentity = {
  name: string;
  app_version: string;
  git_sha?: string | null;
  branch?: string | null;
  dirty?: boolean;
  patch_hash?: string | null;
  build_fingerprint?: string | null;
};

export type ForensicContracts = {
  trace_schema: number;
  compiler: string;
  capsule: string;
  prompt_bundle?: string | null;
  tool_registry?: string | null;
  feature_flags?: string[];
};

export type ForensicRuntime = {
  environment?: string | null;
  session_started?: string | null;
  model?: string | null;
  world_checkpoint?: string | null;
  fixture?: string | null;
};

export type ForensicProvenance = {
  build: BuildIdentity;
  contracts: ForensicContracts;
  runtime: ForensicRuntime;
};

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
  evidence_bundle?: EvidenceBundle | null;
  forensic_provenance?: ForensicProvenance | null;
};

export type SourceName =
  | "calendar"
  | "attention"
  | "next_actions"
  | "world_changes"
  | "world_blockers"
  | "sources_email"
  | "sources_chat"
  | "weather"
  | "news"
  | "general_knowledge";

export type CourierState =
  | "resting"
  | "fetching"
  | "returned"
  | "empty_pawed"
  | "partially_returned"
  | "confused"
  | "blocked";

export type GooseState =
  | "idle"
  | "leaving"
  | "searching"
  | "waiting"
  | "returning"
  | "presenting"
  | "huffing"
  | "empty_beaked"
  | "verifying"
  | "pleased";

export type FetchMission = {
  question: string;
  request_kind?: string | null;
  scope?: "work" | "personal" | null;
  time_range?: string | null;
  authority?: string;
  planned_tools?: string[];
};

export type EvidenceItem = {
  source: SourceName;
  evidence_ids: string[];
  summary?: string | null;
};

export type GroundedAssertion = {
  id: string;
  kind?: "fact" | "hypothesis" | "pattern" | "preference" | "delegation";
  subject: string;
  predicate: string;
  value: unknown;
  scope?: string | null;
  epistemic_status:
    | "user_reported"
    | "user_confirmed"
    | "source_observed"
    | "externally_verified"
    | "system_verified"
    | "deterministically_derived"
    | "user_uncertain"
    | "model_inferred"
    | "conflicted"
    | "stale"
    | "unknown";
  confidence?: number | null;
  evidence_refs?: string[];
  observed_at?: string | null;
  valid_from?: string | null;
  valid_until?: string | null;
  temporal_scope?: string | null;
  validity_kind?: "stable" | "ttl" | "until_event" | "source_lifetime" | "derived_lifetime";
  sensitivity?: "low" | "personal" | "high";
  purpose_tags?: string[];
  retention_class?:
    | "active_until_resolved"
    | "ephemeral_answer_only"
    | "expire_with_source"
    | "durable_shadow";
  egress_class?: "remote_safe" | "local_only";
  derived_from?: string[];
  derivation_kind?:
    | "direct_observation"
    | "user_confirmation"
    | "source_confirmation"
    | "deterministic_rule"
    | "inference"
    | "semantic_similarity"
    | "dialogue_history"
    | "high_confidence"
    | null;
  supersedes?: string[];
  invalidated_by?: string[];
};

export type EvidenceUnknown = {
  subject: string;
  predicate: string;
  reason:
    | "missing_evidence"
    | "conflicting_evidence"
    | "unresolved_referent"
    | "unavailable_capability"
    | "stale";
  missing_sources: string[];
};

export type AssertionChallenge = {
  claim_id?: string | null;
  related_assertion_ids: string[];
  subject: string;
  predicate: string;
  disposition: "confirms" | "qualifies" | "conflicts" | "does_not_address";
  summary: string;
  evidence_refs: string[];
  unresolved?: boolean;
};

export type EvidenceBundle = {
  mission: FetchMission;
  searched_sources: SourceName[];
  empty_sources: SourceName[];
  unsearched_sources: SourceName[];
  unavailable_sources: SourceName[];
  evidence: EvidenceItem[];
  grounded_assertions: GroundedAssertion[];
  unknowns: EvidenceUnknown[];
  unresolved_referents: string[];
  conflicts: { field: string; values: string[]; source_ids: string[] }[];
  challenges: AssertionChallenge[];
  coverage_adequate: boolean;
  courier_state: CourierState;
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
  | ({ kind: "status"; text: string } & ConversationStamp)
  | ({ kind: "source_quote"; text: string; source_id?: string } & ConversationStamp);

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
  forensic_provenance?: ForensicProvenance;
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

/** Why a context module was fetched or withheld — audit, not prompt (ADR-029). */
export type ContextModuleDecision = {
  include: boolean;
  justification: string;
  max_turns?: number | null;
  remote_safe_only?: boolean | null;
  max_bytes?: number | null;
};

export type CompiledTurnManifest = {
  profile: string;
  speech_act?: string | null;
  context: Record<string, ContextModuleDecision>;
  tools: string[];
  excluded_tools: string[];
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
  context_manifest?: CompiledTurnManifest | null;
};
