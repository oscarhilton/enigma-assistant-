import type { AgentWorkSnapshot } from "../../enigma/goosePixels";
import type {
  AttentionState,
  EgressDisclosure,
  LlmTrace,
  ProvenanceView,
} from "../../enigma/types";
import type { WorldId } from "../../pilot/types";

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

export type ForensicSectionStatus = "wired" | "stub" | "empty";

export type ForensicSection<T = unknown> = {
  status: ForensicSectionStatus;
  data: T;
};

export type ForensicModel = {
  snapshot: TurnSnapshot;
  userInput: ForensicSection<{ text: string | null; at: string | null }>;
  turnContract: ForensicSection<Record<string, unknown>>;
  evidence: ForensicSection<{
    provenance: ProvenanceView | null;
    evidenceIds: string[];
    activityLabels: string[];
  }>;
  notDisclosed: ForensicSection<{ excluded: string[]; blocked: boolean; blockReason: string | null }>;
  relationalBootstrap: ForensicSection<Record<string, unknown> | null>;
  handoff: ForensicSection<Record<string, unknown>>;
  agentWork: ForensicSection<AgentWorkSnapshot>;
  authority: ForensicSection<{
    grantsAuthority: boolean;
    enigmaActions: EgressDisclosure["enigma_actions"];
  }>;
  remotePayload: ForensicSection<{
    sent: Record<string, unknown> | null;
    disclosure: LlmTrace["disclosure"];
  }>;
  streamingTrace: ForensicSection<{ note: string }>;
  memory: ForensicSection<{ note: string }>;
  whyNot: ForensicSection<{
    suppressedCount: number;
    sampleTitles: string[];
    note: string;
  }>;
  trace: LlmTrace | null;
  attention: AttentionState | null;
};

export type CopyTier = "safe" | "detailed" | "local";
