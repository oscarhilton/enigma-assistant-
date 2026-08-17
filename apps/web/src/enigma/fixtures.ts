import type { AttentionState, ConversationItem, EgressDisclosure, LlmTrace } from "./types";

export const MOCK_ATTENTION_JAN19: AttentionState = {
  simulated_time: "2026-01-19T10:00:00+00:00",
  checkpoint_id: "cp-2026-01-19T10:00",
  needs_you: [],
  context: [
    {
      id: "item-obligation_token_audit",
      title: "Draft colour + spacing token inventory",
      explanation: "Unblocked now — you could move this forward when you have a moment.",
      policy_decision: "context",
      bucket: "context",
      rank: 1,
      composite_score: 0.6725,
      actionability_now: 0.9,
      reasons: [{ code: "UNBLOCKED", label: "Unblocked" }],
      evidence_ids: ["mail-jordan-tokens"],
    },
  ],
  next_actions: [
    {
      id: "next-item-obligation_token_audit",
      title: "Draft colour + spacing token inventory",
      reason: "Unblocked now",
      optional: true,
      source_candidate_id: "item-obligation_token_audit",
    },
  ],
  can_wait_summary: { total_suppressed: 1, sample_titles: [] },
  presentation: {
    chat_opening_count: 0,
    notification_slot_count: 0,
    proactive_silence: true,
  },
};

export const MOCK_CONVERSATION: ConversationItem[] = [
  {
    kind: "enigma_message",
    text: "Ask Enigma what needs you — world state drives the answer, not chat history.",
    at: "2026-01-19T10:00:00+00:00",
  },
];

export const C09_TOOL_NAMES = [
  "attention.get_current",
  "next_action.get",
  "next_action.get_alternatives",
  "next_action.reject",
  "referent.get_duration",
  "availability.check",
  "world.get_changes",
  "world.get_blockers",
  "world.explain",
  "assist.propose",
  "assist.approve",
] as const;

export const DENIED_REMOTE_CAPABILITIES = [
  "gmail.search",
  "gmail.send",
  "arbitrary filesystem",
  "arbitrary network",
] as const;

const C09_TOOLS = C09_TOOL_NAMES.map((name) => ({
  type: "function",
  function: { name, parameters: { type: "object", properties: {} } },
}));

const ORCHESTRATE_USER_CONTENT = {
  user_message: "Why do I need to do this?",
  conversation: {
    current_subject_id: "item-obligation_token_audit",
    current_subject_kind: "next_action",
  },
  simulated_time: "2026-01-19T10:00:00+00:00",
  attention_count: 1,
};

const ORCHESTRATE_OUTBOUND = {
  model: "accounts/fireworks/models/gpt-oss-120b",
  messages: [
    {
      role: "system",
      content: "You are Enigma's conversational orchestrator for a demo assistant.",
    },
    { role: "user", content: JSON.stringify(ORCHESTRATE_USER_CONTENT) },
  ],
  tools: C09_TOOLS,
  tool_choice: "auto",
  max_tokens: 1024,
};

export const MOCK_DISCLOSURES: EgressDisclosure[] = [
  {
    id: "disc-mock-orchestrate",
    correlation_id: "corr-demo-orchestrate-001",
    timestamp: "2026-01-19T10:05:12+00:00",
    purpose: "conversation.orchestrate",
    provider: "fireworks",
    model: "accounts/fireworks/models/gpt-oss-120b",
    transformation_profile: "conversation_orchestrator_v1",
    payload_field_summary: {
      message_word_count: 7,
      context_keys: ["current_subject_id", "current_subject_kind"],
      tool_count: C09_TOOL_NAMES.length,
      tool_names: [...C09_TOOL_NAMES],
      simulated_time: "2026-01-19T10:00:00+00:00",
      attention_count: 1,
    },
    payload_hash: "sha256:7f3c9a2e1b8d4f6a0c5e3d2b1a9f8e7d6c5b4a39281706152433425161708",
    byte_count: 1842,
    blocked: false,
    block_reason: null,
    classification: "remote_safe",
    prompt_tokens: 312,
    completion_tokens: 28,
    outbound_payload: ORCHESTRATE_OUTBOUND,
    provider_response: {
      text: JSON.stringify({
        role: "assistant",
        tool_calls: [{ function: { name: "world.explain", arguments: "{}" } }],
      }),
      model: "accounts/fireworks/models/gpt-oss-120b",
      blocked: false,
    },
    transport_endpoint: "https://api.fireworks.ai/inference/v1/chat/completions",
    included: [
      "current user message",
      "simulated time",
      "attention count",
      "permitted tool schemas",
    ],
    excluded: [
      "PRIVATE_RAW",
      "raw email bodies",
      "calendar event descriptions",
      "contact identities",
      "source records",
      "attachments",
      "private memory",
    ],
    denied_capabilities: [...DENIED_REMOTE_CAPABILITIES],
    tool_trace: [
      {
        request: { name: "world.explain", arguments: {} },
        result: { name: "world.explain", ok: true, data: { subject_id: "item-obligation_token_audit" } },
      },
    ],
    enigma_actions: [
      { name: "world.explain", effect: "allowed", side_effect: false, ok: true },
    ],
  },
  {
    id: "disc-mock-blocked",
    correlation_id: "corr-reasoning-judge-002",
    timestamp: "2026-01-19T09:58:44+00:00",
    purpose: "reasoning.semantic_judge",
    provider: "none",
    model: "none",
    transformation_profile: "blocked",
    payload_field_summary: {
      rejected_type: "PrivateRaw",
    },
    payload_hash: "sha256:2a4b6c8d0e1f3a5b7c9d1e3f5a7b9c1d3e5f7a9b1c3d5e7f9a1b3c5d7e9f1a3",
    byte_count: 0,
    blocked: true,
    block_reason: "Remote inference disabled (ENIGMA_REMOTE_INFERENCE=0)",
    classification: "unclassified",
    prompt_tokens: 0,
    completion_tokens: 0,
    outbound_payload: {},
    included: [],
    excluded: [
      "PRIVATE_RAW",
      "raw email bodies",
      "calendar event descriptions",
      "contact identities",
      "source records",
      "attachments",
      "private memory",
    ],
    denied_capabilities: [...DENIED_REMOTE_CAPABILITIES],
    tool_trace: [],
    enigma_actions: [],
  },
];

export const MOCK_LLM_TRACE_ROUTER: LlmTrace = {
  path: "intent_router",
  planner: "intent_router",
  user_message: "What should I do next?",
  conversation_state: {
    current_subject_id: "item-obligation_token_audit",
    current_subject_kind: "next_action",
  },
  tools_available: [...C09_TOOL_NAMES],
  remote_context_sent: null,
  model_tool_request: [],
  tool_results: [],
  model_response: [{ kind: "next_action", text: "Draft colour + spacing token inventory" }],
  intent_name: "next_action_query",
  router_fallback: true,
  disclosure_id: null,
  disclosure: null,
  included: [],
  excluded: [
    "PRIVATE_RAW",
    "raw email bodies",
    "calendar event descriptions",
    "contact identities",
    "source records",
    "attachments",
    "private memory",
  ],
  correlation_id: "corr-router-001",
};

export const MOCK_LLM_TRACE_LLM: LlmTrace = {
  path: "llm",
  planner: "EgressConversationLLM",
  user_message: "Why do I need to do this?",
  conversation_state: {
    current_subject_id: "item-obligation_token_audit",
    current_subject_kind: "next_action",
  },
  tools_available: [...C09_TOOL_NAMES],
  remote_context_sent: {
    user_message: "Why do I need to do this?",
    conversation: {
      current_subject_id: "item-obligation_token_audit",
      current_subject_kind: "next_action",
    },
    simulated_time: "2026-01-19T10:00:00+00:00",
    attention_count: 1,
  },
  model_tool_request: [{ name: "world.explain", arguments: {} }],
  tool_results: [
    {
      name: "world.explain",
      ok: true,
      data: { subject_id: "item-obligation_token_audit" },
    },
  ],
  model_response: [{ kind: "attention_item", text: "Draft colour + spacing token inventory" }],
  intent_name: "why_query",
  router_fallback: false,
  disclosure_id: "disc-mock-orchestrate",
  disclosure: {
    id: "disc-mock-orchestrate",
    provider: "fireworks",
    purpose: "conversation.orchestrate",
    model: "accounts/fireworks/models/gpt-oss-120b",
    payload_hash: "sha256:7f3c9a2e1b8d4f6a0c5e3d2b1a9f8e7d6c5b4a39281706152433425161708",
    payload_field_summary: {
      message_word_count: 7,
      tool_count: C09_TOOL_NAMES.length,
    },
    blocked: false,
    included: [
      "current user message",
      "simulated time",
      "attention count",
      "permitted tool schemas",
    ],
    excluded: [
      "PRIVATE_RAW",
      "raw email bodies",
      "calendar event descriptions",
      "contact identities",
      "source records",
      "attachments",
      "private memory",
    ],
    outbound_payload: ORCHESTRATE_OUTBOUND,
    transport_endpoint: "https://api.fireworks.ai/inference/v1/chat/completions",
  },
  included: [
    "current user message",
    "simulated time",
    "attention count",
    "permitted tool schemas",
  ],
  excluded: [
    "raw email bodies",
    "calendar event descriptions",
    "contact identities",
    "source records",
    "attachments",
    "private memory",
  ],
  correlation_id: "corr-demo-orchestrate-001",
};
