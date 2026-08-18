import type { AgentWorkSnapshot } from "../../enigma/goosePixels";
import type { AttentionState, LlmTrace, ProvenanceView } from "../../enigma/types";
import type { WorldId } from "../../pilot/types";
import type { StreamingTraceProjection } from "../streamTrace";

export type TurnSnapshot = {
  buildCommit: string;
  world: WorldId;
  worldLabel: string;
  simulatedTime: string | null;
  turnIndex: number;
  turnCount: number;
  correlationId: string | null;
  path: string | null;
};

export type ForensicSectionStatus = "wired" | "unavailable" | "empty";

export type ForensicSection<T = unknown> = {
  status: ForensicSectionStatus;
  data: T;
};

export type ForensicModel = {
  snapshot: TurnSnapshot;
  userInput: ForensicSection<{ text: string | null; at: string | null }>;
  turnContract: ForensicSection<Record<string, unknown> | null>;
  evidence: ForensicSection<{
    provenance: ProvenanceView | null;
    evidenceIds: string[];
    activityLabels: string[];
  }>;
  notDisclosed: ForensicSection<{ excluded: string[]; blocked: boolean; blockReason: string | null }>;
  relationalBootstrap: ForensicSection<Record<string, unknown> | null>;
  handoff: ForensicSection<Record<string, unknown> | null>;
  agentWork: ForensicSection<AgentWorkSnapshot>;
  authority: ForensicSection<Record<string, unknown> | null>;
  remotePayload: ForensicSection<{
    sent: Record<string, unknown> | null;
    disclosure: LlmTrace["disclosure"];
  }>;
  streamingTrace: ForensicSection<StreamingTraceProjection | null>;
  memory: ForensicSection<null>;
  whyNot: ForensicSection<{
    source: "can_wait_summary";
    total_suppressed: number;
    sample_titles: string[];
  } | null>;
  trace: LlmTrace | null;
  attention: AttentionState | null;
};

export type CopyTier = "safe" | "detailed" | "local";

export const NOT_CAPTURED = "Not captured for this turn";
