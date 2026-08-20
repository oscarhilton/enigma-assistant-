import { stitchLlmTrace, tracesFromItems } from "../../enigma/forensicDump";
import type { AgentWorkSnapshot } from "../../enigma/goosePixels";
import type { ConversationItem, LlmTrace } from "../../enigma/types";
import type { CapturedStreamEvent, StreamingTraceProjection } from "../streamTrace";

export type ForensicUserInput = {
  text: string | null;
  at: string | null;
};

export type CalendarNegativeEvidence = {
  checked: true;
  scope: string;
  resultCount: number;
  source: string;
};

export type ForensicTurnBinding = {
  userInput: ForensicUserInput;
  items: ConversationItem[];
  llmTrace: LlmTrace | null;
  agentWork: AgentWorkSnapshot | null;
  calendarFactsUsed: Record<string, unknown>[];
  calendarNegativeEvidence: CalendarNegativeEvidence | null;
  turnIndex: number;
  turnCount: number;
};

const CALENDAR_TOOLS = new Set([
  "availability.check",
  "agenda.get",
  "briefing.read",
  "calendar.agenda.get",
  "world.explain",
]);

function lastUserInput(items: ConversationItem[]): ForensicUserInput {
  for (let index = items.length - 1; index >= 0; index -= 1) {
    const item = items[index];
    if (item?.kind === "user_message") {
      return { text: item.text, at: item.at };
    }
  }
  return { text: null, at: null };
}

function readRecord(value: unknown): Record<string, unknown> | null {
  if (!value || typeof value !== "object" || Array.isArray(value)) {
    return null;
  }
  return value as Record<string, unknown>;
}

function calendarItemsFromToolResult(result: Record<string, unknown>): unknown[] {
  const nested = readRecord(result.data)?.calendar_items;
  if (Array.isArray(nested)) {
    return nested;
  }
  const topLevel = result.calendar_items;
  return Array.isArray(topLevel) ? topLevel : [];
}

function periodFromToolResult(
  result: Record<string, unknown>,
  executed: LlmTraceToolCall[] | undefined,
): string | null {
  const nested = readRecord(result.data)?.period;
  if (typeof nested === "string" && nested.length > 0) {
    return nested;
  }
  const topLevel = result.period;
  if (typeof topLevel === "string" && topLevel.length > 0) {
    return topLevel;
  }
  const request = executed?.find((call) => call.name === result.name);
  const argumentPeriod = request?.arguments?.period;
  return typeof argumentPeriod === "string" && argumentPeriod.length > 0 ? argumentPeriod : null;
}

type LlmTraceToolCall = NonNullable<LlmTrace["executed_tool_request"]>[number];

export function calendarNegativeEvidenceFromTurn(input: {
  calendarFactsUsed: Record<string, unknown>[];
  llmTrace: LlmTrace | null;
}): CalendarNegativeEvidence | null {
  const toolResults = input.llmTrace?.tool_results ?? [];
  for (const rawResult of toolResults) {
    const result = readRecord(rawResult);
    if (!result || typeof result.name !== "string" || !CALENDAR_TOOLS.has(result.name)) {
      continue;
    }
    const calendarItems = calendarItemsFromToolResult(result);
    const factCount = input.calendarFactsUsed.length;
    const resultCount = calendarItems.length > 0 ? calendarItems.length : factCount;
    const scope =
      periodFromToolResult(result, input.llmTrace?.executed_tool_request) ??
      (resultCount === 0 ? "unknown" : "unknown");
    return {
      checked: true,
      scope,
      resultCount,
      source: result.name,
    };
  }
  if (input.calendarFactsUsed.length === 0 && input.llmTrace?.executed_tool_request) {
    const calendarCall = input.llmTrace.executed_tool_request.find((call) =>
      CALENDAR_TOOLS.has(call.name),
    );
    if (calendarCall) {
      const argumentPeriod = calendarCall.arguments?.period;
      return {
        checked: true,
        scope: typeof argumentPeriod === "string" ? argumentPeriod : "unknown",
        resultCount: 0,
        source: calendarCall.name,
      };
    }
  }
  return null;
}

export function streamTraceHasTurnComplete(
  trace: StreamingTraceProjection | null | undefined,
): boolean {
  return trace?.timeline.some((entry) => entry.kind === "TURN" && entry.detail === "complete") ?? false;
}

/** Bind forensic identity from a completed stream turn — not live UI state. */
export function bindForensicTurn(
  captured: CapturedStreamEvent[],
  provisionalUserInput?: ForensicUserInput | null,
): ForensicTurnBinding | null {
  const turnComplete = [...captured]
    .reverse()
    .find((entry) => entry.event.type === "turn_complete");
  if (!turnComplete || turnComplete.event.type !== "turn_complete") {
    return null;
  }

  const payload = turnComplete.event.data;
  const rawItems = payload.conversation?.items ?? payload.items ?? [];
  const items = payload.llm_trace ? stitchLlmTrace(rawItems, payload.llm_trace) : rawItems;
  const traces = tracesFromItems(items);
  const llmTrace = payload.llm_trace ?? traces.at(-1) ?? null;
  const userInput = lastUserInput(items);
  const resolvedUserInput =
    userInput.text || userInput.at
      ? userInput
      : (provisionalUserInput ?? { text: null, at: null });

  const lastAgentWork = [...captured]
    .reverse()
    .find((entry) => entry.event.type === "agent_work");
  const agentWork =
    lastAgentWork?.event.type === "agent_work" ? lastAgentWork.event.data : null;

  const calendarFactsUsed = payload.calendar_facts_used ?? [];
  const turnCount = traces.length > 0 ? traces.length : resolvedUserInput.text ? 1 : 0;
  const turnIndex = turnCount;

  return {
    userInput: resolvedUserInput,
    items,
    llmTrace,
    agentWork,
    calendarFactsUsed,
    calendarNegativeEvidence: calendarNegativeEvidenceFromTurn({
      calendarFactsUsed,
      llmTrace,
    }),
    turnIndex,
    turnCount,
  };
}
