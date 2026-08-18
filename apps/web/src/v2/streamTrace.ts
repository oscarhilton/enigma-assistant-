import type { AgentWorkPhase } from "../enigma/goosePixels";
import type { ConversationStreamEvent } from "./streamTypes";

/** Product copy for the AGENT WORK lane — mapped from captured SSE phases only. */
export type AgentWorkLaneStep =
  | "investigating"
  | "advancing"
  | "waiting / verifying"
  | "handled";

export type ProseLaneStep = "chunk" | "complete";

export type StreamingTraceProjection = {
  prose: { steps: ProseLaneStep[] };
  agentWork: { steps: AgentWorkLaneStep[] };
};

function workStep(phase: AgentWorkPhase | null, sawInFlight: boolean): AgentWorkLaneStep | null {
  if (phase === "in_flight") {
    return sawInFlight ? "advancing" : "investigating";
  }
  if (phase === "waiting") {
    return "waiting / verifying";
  }
  if (phase === "complete") {
    return "handled";
  }
  return null;
}

/**
 * Project captured SSE events into two independent lanes.
 * Returns null when no stream events were captured — never inferred from assistant text.
 */
export function projectStreamTrace(
  events: ConversationStreamEvent[],
): StreamingTraceProjection | null {
  if (events.length === 0) {
    return null;
  }
  const prose: ProseLaneStep[] = [];
  const agentWork: AgentWorkLaneStep[] = [];
  let sawInFlight = false;
  for (const event of events) {
    if (event.type === "prose") {
      prose.push("chunk");
    } else if (event.type === "agent_work") {
      const step = workStep(event.data.phase, sawInFlight);
      if (event.data.phase === "in_flight") {
        sawInFlight = true;
      }
      if (step) {
        agentWork.push(step);
      }
    } else if (event.type === "turn_complete") {
      prose.push("complete");
    }
  }
  return { prose: { steps: prose }, agentWork: { steps: agentWork } };
}

export function formatLane(steps: string[]): string {
  return steps.length > 0 ? steps.join(" → ") : "—";
}
