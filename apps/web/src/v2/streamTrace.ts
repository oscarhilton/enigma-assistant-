import type { AgentWorkPhase } from "../enigma/goosePixels";
import type { ConversationStreamEvent } from "./streamTypes";

/** Product copy for the AGENT WORK lane — mapped from captured SSE phases only. */
export type AgentWorkLaneStep =
  | "investigating"
  | "advancing"
  | "waiting / verifying"
  | "handled";

export type ProseLaneStep = "chunk" | "complete";

export type StreamTimelineKind = "WORK" | "PROSE" | "TURN" | "ERROR";

export type StreamTimelineEntry = {
  capturedAt: number;
  kind: StreamTimelineKind;
  detail: string;
};

export type CapturedStreamEvent = {
  capturedAt: number;
  event: ConversationStreamEvent;
};

export type StreamingTraceProjection = {
  prose: { steps: ProseLaneStep[] };
  agentWork: { steps: AgentWorkLaneStep[] };
  timeline: StreamTimelineEntry[];
  formatted: string;
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

function timelineDetail(event: ConversationStreamEvent): StreamTimelineEntry["detail"] | null {
  if (event.type === "agent_work") {
    return event.data.phase ?? "unknown";
  }
  if (event.type === "prose") {
    return JSON.stringify(event.data.delta);
  }
  if (event.type === "turn_complete") {
    return "complete";
  }
  if (event.type === "error") {
    return event.data.message;
  }
  return null;
}

function timelineKind(event: ConversationStreamEvent): StreamTimelineKind | null {
  if (event.type === "agent_work") {
    return "WORK";
  }
  if (event.type === "prose") {
    return "PROSE";
  }
  if (event.type === "turn_complete") {
    return "TURN";
  }
  if (event.type === "error") {
    return "ERROR";
  }
  return null;
}

export function formatCaptureTimestamp(capturedAt: number): string {
  const date = new Date(capturedAt);
  const hh = String(date.getHours()).padStart(2, "0");
  const mm = String(date.getMinutes()).padStart(2, "0");
  const ss = String(date.getSeconds()).padStart(2, "0");
  const ms = String(date.getMilliseconds()).padStart(3, "0");
  return `${hh}:${mm}:${ss}.${ms}`;
}

export function formatTimelineLine(entry: StreamTimelineEntry): string {
  const timestamp = formatCaptureTimestamp(entry.capturedAt);
  const kind = entry.kind.padEnd(7);
  return `${timestamp}  ${kind}${entry.detail}`;
}

export function formatStreamTimeline(timeline: StreamTimelineEntry[]): string {
  if (timeline.length === 0) {
    return "";
  }
  const lines = ["STREAM TRACE", "─────────────────────────────", ""];
  for (const entry of timeline) {
    lines.push(formatTimelineLine(entry));
  }
  return lines.join("\n");
}

/**
 * Project captured SSE events into independent lanes plus a unified chronological timeline.
 * Returns null when no stream events were captured — never inferred from assistant text.
 */
export function projectStreamTrace(
  captured: CapturedStreamEvent[],
): StreamingTraceProjection | null {
  if (captured.length === 0) {
    return null;
  }
  const prose: ProseLaneStep[] = [];
  const agentWork: AgentWorkLaneStep[] = [];
  const timeline: StreamTimelineEntry[] = [];
  let sawInFlight = false;
  for (const { capturedAt, event } of captured) {
    const kind = timelineKind(event);
    const detail = timelineDetail(event);
    if (kind && detail) {
      timeline.push({ capturedAt, kind, detail });
    }
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
  return {
    prose: { steps: prose },
    agentWork: { steps: agentWork },
    timeline,
    formatted: formatStreamTimeline(timeline),
  };
}

export function formatLane(steps: string[]): string {
  return steps.length > 0 ? steps.join(" → ") : "—";
}
