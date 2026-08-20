import { threadActivityFromTrace } from "../../enigma/activity";
import { tracesFromItems } from "../../enigma/forensicDump";
import { emptyWorkSnapshot, workSnapshotFromConversation } from "../../enigma/goosePixels";
import type { AttentionState, ConversationItem, LlmTrace, ProvenanceView } from "../../enigma/types";
import { WORLD_LABELS, type WorldId } from "../../pilot/types";
import { buildCommitLabel } from "../buildIdentity";
import type { ForensicTurnBinding } from "./forensicTurn";
import { streamTraceHasTurnComplete } from "./forensicTurn";
import type { ForensicModel, ForensicSection } from "./types";
import type { StreamingTraceProjection } from "../streamTrace";

function lastUserMessage(items: ConversationItem[]): { text: string | null; at: string | null } {
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

function namedProjection(remote: unknown, key: string): Record<string, unknown> | null {
  return readRecord(readRecord(remote)?.[key]);
}

function evidenceIdsFromAttention(attention: AttentionState | null): string[] {
  if (!attention) {
    return [];
  }
  const ids = new Set<string>();
  for (const item of [...attention.needs_you, ...attention.context]) {
    for (const evidenceId of item.evidence_ids) {
      ids.add(evidenceId);
    }
  }
  return [...ids];
}

function capturedOrUnavailable(record: Record<string, unknown> | null): ForensicSection<Record<string, unknown> | null> {
  if (record) {
    return { status: "wired", data: record };
  }
  return { status: "unavailable", data: null };
}

function authorityFromTrace(trace: LlmTrace | null): Record<string, unknown> | null {
  const remoteAuthority = namedProjection(trace?.remote_context_sent ?? null, "authority");
  if (remoteAuthority) {
    return remoteAuthority;
  }
  const state = readRecord(trace?.conversation_state);
  if (!state) {
    return null;
  }
  const authorityCeiling = state.authority_ceiling;
  const capabilityContract = state.capability_contract;
  if (typeof authorityCeiling !== "string" && !capabilityContract) {
    return null;
  }
  return {
    ...(typeof authorityCeiling === "string" ? { authority_ceiling: authorityCeiling } : {}),
    ...(capabilityContract ? { capability_contract: capabilityContract } : {}),
  };
}

export function buildForensicModel(input: {
  items: ConversationItem[];
  attention: AttentionState | null;
  busy: boolean;
  loading: boolean;
  world: WorldId;
  provenance: ProvenanceView | null;
  streamingTrace?: StreamingTraceProjection | null;
  forensicTurn?: ForensicTurnBinding | null;
}): ForensicModel {
  const boundTurn =
    input.forensicTurn && streamTraceHasTurnComplete(input.streamingTrace)
      ? input.forensicTurn
      : null;
  const forensicItems = boundTurn?.items ?? input.items;
  const traces = tracesFromItems(forensicItems);
  const trace: LlmTrace | null = boundTurn?.llmTrace ?? traces.at(-1) ?? null;
  const turnCount = boundTurn?.turnCount ?? traces.length;
  const turnIndex = boundTurn?.turnIndex ?? (turnCount > 0 ? turnCount : 0);
  const remote = trace?.remote_context_sent ?? null;
  const activities = trace
    ? threadActivityFromTrace(trace, { at: forensicItems.at(-1)?.at ?? "" })
    : [];
  const conversationWork = workSnapshotFromConversation({
    items: forensicItems,
    busy: boundTurn ? false : input.busy,
    loading: boundTurn ? false : input.loading,
  });
  const agentWork =
    boundTurn?.agentWork?.exists === true
      ? boundTurn.agentWork
      : conversationWork.exists
        ? conversationWork
        : emptyWorkSnapshot();
  const userInput = boundTurn?.userInput ?? lastUserMessage(forensicItems);
  const canWait = input.attention?.can_wait_summary ?? null;
  const calendarNegativeEvidence = boundTurn?.calendarNegativeEvidence ?? null;
  const hasEvidence =
    Boolean(input.provenance) ||
    evidenceIdsFromAttention(input.attention).length > 0 ||
    calendarNegativeEvidence !== null ||
    (boundTurn?.calendarFactsUsed.length ?? 0) > 0;

  return {
    snapshot: {
      buildCommit: buildCommitLabel(),
      world: input.world,
      worldLabel: WORLD_LABELS[input.world],
      simulatedTime: input.attention?.simulated_time ?? userInput.at,
      turnIndex,
      turnCount,
      correlationId: trace?.correlation_id ?? null,
      path: trace?.path ?? null,
    },
    userInput: {
      status: userInput.text ? "wired" : "empty",
      data: userInput,
    },
    turnContract: capturedOrUnavailable(namedProjection(remote, "turn_contract")),
    evidence: {
      status: hasEvidence ? "wired" : "empty",
      data: {
        provenance: input.provenance,
        evidenceIds: evidenceIdsFromAttention(input.attention),
        activityLabels: activities.map((event) => event.label),
        calendarFactsUsed: boundTurn?.calendarFactsUsed ?? [],
        calendarNegativeEvidence,
      },
    },
    notDisclosed: {
      status: trace ? "wired" : "empty",
      data: {
        excluded: trace?.disclosure?.excluded ?? trace?.excluded ?? [],
        blocked: trace?.disclosure?.blocked ?? false,
        blockReason: trace?.disclosure?.block_reason ?? null,
      },
    },
    relationalBootstrap: capturedOrUnavailable(namedProjection(remote, "relational_bootstrap")),
    handoff: capturedOrUnavailable(namedProjection(remote, "handoff")),
    agentWork: {
      status: agentWork.exists ? "wired" : "empty",
      data: agentWork,
    },
    authority: capturedOrUnavailable(authorityFromTrace(trace)),
    remotePayload: {
      status: remote || trace?.disclosure ? "wired" : "empty",
      data: {
        sent: remote,
        disclosure: trace?.disclosure ?? null,
      },
    },
    streamingTrace: input.streamingTrace
      ? { status: "wired", data: input.streamingTrace }
      : { status: "unavailable", data: null },
    memory: { status: "unavailable", data: null },
    whyNot: canWait
      ? {
          status: "wired",
          data: {
            source: "can_wait_summary",
            total_suppressed: canWait.total_suppressed,
            sample_titles: canWait.sample_titles,
          },
        }
      : { status: "unavailable", data: null },
    trace,
    attention: input.attention,
  };
}
