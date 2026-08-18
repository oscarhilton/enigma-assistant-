import type { ConversationItem } from "./types";
import { threadActivityFromTrace, type EnigmaActivityEvent } from "./activity";

export type GooseMotion = "absent" | "idle" | "walk" | "return";
export type GooseExpressiveness = "restrained" | "playful";
export type AgentWorkPhase = "in_flight" | "waiting" | "complete";
export type VisibilityLayer = "surface" | "inspectable" | "forensic";

export type AgentWorkSnapshot = {
  exists: boolean;
  phase: AgentWorkPhase | null;
  semanticToken: string;
  inspectTarget: string | null;
  inspectLabels: string[];
};

export type GoosePixelLicence = {
  motion: GooseMotion;
  expressiveness: GooseExpressiveness;
  layer: "surface";
  grantsAuthority: false;
  isEvidence: false;
  inspectTarget: string | null;
  inspectLabels: string[];
  workSemanticToken: string;
};

const PHASE_MOTION: Record<AgentWorkPhase, GooseMotion> = {
  in_flight: "walk",
  waiting: "idle",
  complete: "return",
};

export function emptyWorkSnapshot(): AgentWorkSnapshot {
  return {
    exists: false,
    phase: null,
    semanticToken: "",
    inspectTarget: null,
    inspectLabels: [],
  };
}

export function motionFromWork(work: AgentWorkSnapshot | null): GooseMotion {
  if (!work?.exists || work.phase === null) {
    return "absent";
  }
  return PHASE_MOTION[work.phase];
}

export function expressivenessFromRemoteContext(remote: unknown): GooseExpressiveness {
  if (!remote || typeof remote !== "object") {
    return "restrained";
  }
  const bootstrap = (remote as { relational_bootstrap?: unknown }).relational_bootstrap;
  if (!bootstrap || typeof bootstrap !== "object") {
    return "restrained";
  }
  const continuation = (bootstrap as { continuation?: unknown }).continuation;
  if (!continuation || typeof continuation !== "object") {
    return "restrained";
  }
  return (continuation as { culture_palette_available?: unknown }).culture_palette_available === true
    ? "playful"
    : "restrained";
}

export function licenseGoosePixels(
  work: AgentWorkSnapshot | null,
  expressiveness: GooseExpressiveness,
): GoosePixelLicence {
  const motion = motionFromWork(work);
  if (motion === "absent" || !work) {
    return {
      motion: "absent",
      expressiveness: "restrained",
      layer: "surface",
      grantsAuthority: false,
      isEvidence: false,
      inspectTarget: null,
      inspectLabels: [],
      workSemanticToken: "",
    };
  }
  return {
    motion,
    expressiveness,
    layer: "surface",
    grantsAuthority: false,
    isEvidence: false,
    inspectTarget: work.inspectTarget,
    inspectLabels: work.inspectLabels,
    workSemanticToken: work.semanticToken,
  };
}

export function pixelsAllowedOn(layer: VisibilityLayer, licence: GoosePixelLicence): boolean {
  return layer === "surface" && licence.motion !== "absent";
}

export function latestThreadActivities(items: ConversationItem[]): EnigmaActivityEvent[] {
  for (let index = items.length - 1; index >= 0; index -= 1) {
    const item = items[index];
    const trace = item?.llm_trace;
    if (trace) {
      return threadActivityFromTrace(trace, { at: item.at });
    }
  }
  return [];
}

export function latestRemoteContext(items: ConversationItem[]): unknown {
  for (let index = items.length - 1; index >= 0; index -= 1) {
    const remote = items[index]?.llm_trace?.remote_context_sent;
    if (remote !== undefined && remote !== null) {
      return remote;
    }
  }
  return null;
}

export function workSnapshotFromConversation(input: {
  items: ConversationItem[];
  busy: boolean;
  loading: boolean;
}): AgentWorkSnapshot {
  const activities = latestThreadActivities(input.items);
  const labels = activities.map((event) => event.label);
  const inspectTarget = activities.find((event) => event.subject_id)?.subject_id ?? null;
  const pendingAssist = input.items.some((item) => item.kind === "assist_proposal")
    && !input.items.some((item) => item.kind === "assist_result");

  if (input.busy || input.loading) {
    return {
      exists: true,
      phase: "in_flight",
      semanticToken: activities[0]?.id ?? "in-flight",
      inspectTarget,
      inspectLabels: labels,
    };
  }

  if (pendingAssist) {
    const proposal = [...input.items]
      .reverse()
      .find((item): item is Extract<ConversationItem, { kind: "assist_proposal" }> => {
        return item.kind === "assist_proposal";
      });
    return {
      exists: true,
      phase: "waiting",
      semanticToken: proposal?.proposal.id ?? "assist-waiting",
      inspectTarget,
      inspectLabels: proposal ? [proposal.proposal.title] : ["Prepared an action"],
    };
  }

  if (activities.length > 0) {
    return {
      exists: true,
      phase: "complete",
      semanticToken: activities.map((event) => event.id).join("|"),
      inspectTarget,
      inspectLabels: labels,
    };
  }

  return emptyWorkSnapshot();
}

export function licenceFromConversation(input: {
  items: ConversationItem[];
  busy: boolean;
  loading: boolean;
}): GoosePixelLicence {
  return licenseGoosePixels(
    workSnapshotFromConversation(input),
    expressivenessFromRemoteContext(latestRemoteContext(input.items)),
  );
}
