import type {
  AgentWorkPhase,
  GooseExpressiveness,
  GooseMotion,
  GoosePixelLicence,
} from "./goosePixels";

export const GOOSE_TELEMETRY_EVENTS = [
  "goose_became_visible",
  "goose_motion_started",
  "goose_returned",
  "goose_inspected",
  "agent_work_changed",
  "frame_expression_changed",
] as const;

export type GooseTelemetryName = (typeof GOOSE_TELEMETRY_EVENTS)[number];

export const FORBIDDEN_GOOSE_TELEMETRY_EVENTS = [
  "goose_clicked_17_times",
  "goose_engagement_score",
  "user_affection",
  "daily_goose_retention",
] as const;

export type GooseTelemetryEvent = {
  name: GooseTelemetryName;
  motion: GooseMotion;
  previousMotion: GooseMotion | null;
  workPhase: AgentWorkPhase | null;
  workSemanticToken: string;
  expressiveness: GooseExpressiveness;
  inspectTarget: string | null;
  inspectLabels: string[];
  impliedMeaning: string;
};

const MOTION_INTERPRETATION: Record<GooseMotion, string> = {
  absent: "not present",
  idle: "looks finished",
  walk: "actively working",
  return: "returned with a result",
};

export function impliedMeaning(motion: GooseMotion): string {
  return MOTION_INTERPRETATION[motion];
}

export function isForbiddenGooseTelemetry(name: string): boolean {
  return (FORBIDDEN_GOOSE_TELEMETRY_EVENTS as readonly string[]).includes(name);
}

export function isAllowedGooseTelemetry(name: string): name is GooseTelemetryName {
  return (GOOSE_TELEMETRY_EVENTS as readonly string[]).includes(name);
}

function workIdentity(licence: GoosePixelLicence | null): string {
  if (!licence || licence.motion === "absent") {
    return "absent";
  }
  return `${licence.motion}|${licence.workSemanticToken}`;
}

function phaseFromMotion(motion: GooseMotion): AgentWorkPhase | null {
  if (motion === "walk") {
    return "in_flight";
  }
  if (motion === "idle") {
    return "waiting";
  }
  if (motion === "return") {
    return "complete";
  }
  return null;
}

function event(
  name: GooseTelemetryName,
  licence: GoosePixelLicence,
  previousMotion: GooseMotion | null,
): GooseTelemetryEvent {
  return {
    name,
    motion: licence.motion,
    previousMotion,
    workPhase: phaseFromMotion(licence.motion),
    workSemanticToken: licence.workSemanticToken,
    expressiveness: licence.expressiveness,
    inspectTarget: licence.inspectTarget,
    inspectLabels: licence.inspectLabels,
    impliedMeaning: impliedMeaning(licence.motion),
  };
}

export function projectGooseEvents(
  previous: GoosePixelLicence | null,
  next: GoosePixelLicence,
): GooseTelemetryEvent[] {
  const events: GooseTelemetryEvent[] = [];
  const prevMotion: GooseMotion = previous?.motion ?? "absent";
  const previousMotion = previous ? prevMotion : null;

  if (workIdentity(previous) !== workIdentity(next)) {
    events.push(event("agent_work_changed", next, previousMotion));
  }
  if (
    previous
    && previous.expressiveness !== next.expressiveness
    && previous.workSemanticToken === next.workSemanticToken
    && next.workSemanticToken !== ""
  ) {
    events.push(event("frame_expression_changed", next, previousMotion));
  }
  if (prevMotion === "absent" && next.motion !== "absent") {
    events.push(event("goose_became_visible", next, previousMotion));
  }
  if (next.motion !== prevMotion && next.motion !== "absent") {
    events.push(event("goose_motion_started", next, previousMotion));
  }
  if (next.motion === "return" && prevMotion !== "return") {
    events.push(event("goose_returned", next, previousMotion));
  }
  return events;
}

export function inspectGooseEvent(licence: GoosePixelLicence): GooseTelemetryEvent {
  return event("goose_inspected", licence, licence.motion);
}

let sink: GooseTelemetryEvent[] | null = null;

export function installGooseTelemetrySink(target: GooseTelemetryEvent[] | null): void {
  sink = target;
}

export function recordGooseTelemetry(events: GooseTelemetryEvent[]): void {
  for (const item of events) {
    if (isForbiddenGooseTelemetry(item.name)) {
      throw new Error(`engagement telemetry is forbidden: ${item.name}`);
    }
    if (!isAllowedGooseTelemetry(item.name)) {
      throw new Error(`unknown goose telemetry event: ${item.name}`);
    }
  }
  sink?.push(...events);
}
