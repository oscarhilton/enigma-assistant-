import type { AgentWorkSnapshot } from "../enigma/goosePixels";
import type { ConversationItem, LlmTrace } from "../enigma/types";

/** Wire event from POST /worlds/my_enigma/conversation/message/stream. */
export type AgentWorkStreamEvent = AgentWorkSnapshot;

export type ProseStreamEvent = {
  delta: string;
};

export type TurnCompleteStreamEvent = {
  items: ConversationItem[];
  conversation?: { items: ConversationItem[] };
  llm_trace?: LlmTrace;
  calendar_facts_used?: Record<string, unknown>[];
};

export type ErrorStreamEvent = {
  message: string;
};

export type ConversationStreamEvent =
  | { type: "agent_work"; data: AgentWorkStreamEvent }
  | { type: "prose"; data: ProseStreamEvent }
  | { type: "turn_complete"; data: TurnCompleteStreamEvent }
  | { type: "error"; data: ErrorStreamEvent };
