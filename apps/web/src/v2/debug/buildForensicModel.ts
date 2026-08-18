import { threadActivityFromTrace } from "../../enigma/activity";
import { tracesFromItems } from "../../enigma/forensicDump";
import { workSnapshotFromConversation } from "../../enigma/goosePixels";
import type {
  AttentionState,
  ConversationItem,
  EgressDisclosure,
  LlmTrace,
  ProvenanceView,
} from "../../enigma/types";
import type { WorldId } from "../../pilot/types";
import { buildCommitLabel } from "../buildIdentity";
import { WORLD_LABELS } from "../../pilot/types";
import type { ForensicModel } from "./types";

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

function turnContractFromRemote(remote: unknown): Record<string, unknown> | null {
  const record = readRecord(remote);
  const contract = record?.turn_contract;
  return readRecord(contract);
}

function handoffFromRemote(remote: unknown): Record<string, unknown> | null {
  const record = readRecord(remote);
  const handoff = record?.handoff;
  return readRecord(handoff);
}

function relationalBootstrapFromRemote(remote: unknown): Record<string, unknown> | null {
  const record = readRecord(remote);
  const bootstrap = record?.relational_bootstrap;
  return readRecord(bootstrap);
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

function disclosureForTrace(
  trace: LlmTrace | null,
  disclosures: EgressDisclosure[],
): EgressDisclosure | null {
  if (!trace?.correlation_id) {
    return null;
  }
  return disclosures.find((row) => row.correlation_id === trace.correlation_id) ?? null;
}

export function buildForensicModel(input: {
  items: ConversationItem[];
  attention: AttentionState | null;
  busy: boolean;
  loading: boolean;
  world: WorldId;
  provenance: ProvenanceView | null;
  disclosures: EgressDisclosure[];
}): ForensicModel {
  const traces = tracesFromItems(input.items);
  const trace = traces.at(-1) ?? null;
  const turnCount = traces.length;
  const turnIndex = turnCount > 0 ? turnCount : 0;
  const remote = trace?.remote_context_sent ?? null;
  const disclosureRow = disclosureForTrace(trace, input.disclosures);
  const activities = trace ? threadActivityFromTrace(trace, { at: input.items.at(-1)?.at ?? "" }) : [];
  const agentWork = workSnapshotFromConversation({
    items: input.items,
    busy: input.busy,
    loading: input.loading,
  });
  const userInput = lastUserMessage(input.items);
  const turnContract = turnContractFromRemote(remote);
  const handoff = handoffFromRemote(remote);
  const relationalBootstrap = relationalBootstrapFromRemote(remote);

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
    turnContract: {
      status: turnContract ? "wired" : "stub",
      data: turnContract ?? {
        note: "Turn contract projection not present on this turn — API wiring pending.",
      },
    },
    evidence: {
      status: input.provenance || evidenceIdsFromAttention(input.attention).length > 0 ? "wired" : "empty",
      data: {
        provenance: input.provenance,
        evidenceIds: evidenceIdsFromAttention(input.attention),
        activityLabels: activities.map((event) => event.label),
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
    relationalBootstrap: {
      status: relationalBootstrap ? "wired" : "stub",
      data: relationalBootstrap,
    },
    handoff: {
      status: handoff ? "wired" : "stub",
      data: handoff ?? { note: "Handoff projection not present on this turn — API wiring pending." },
    },
    agentWork: {
      status: agentWork.exists ? "wired" : "empty",
      data: agentWork,
    },
    authority: {
      status: disclosureRow?.enigma_actions?.length ? "wired" : "stub",
      data: {
        grantsAuthority: false,
        enigmaActions: disclosureRow?.enigma_actions ?? [],
      },
    },
    remotePayload: {
      status: remote || trace?.disclosure ? "wired" : "empty",
      data: {
        sent: remote,
        disclosure: trace?.disclosure ?? null,
      },
    },
    streamingTrace: {
      status: "stub",
      data: { note: "Streaming trace channel pending UI2-02 — read-model projection only." },
    },
    memory: {
      status: "stub",
      data: { note: "Memory impact projection pending Memory Explorer wiring." },
    },
    whyNot: {
      status: input.attention?.can_wait_summary ? "wired" : "stub",
      data: {
        suppressedCount: input.attention?.can_wait_summary?.total_suppressed ?? 0,
        sampleTitles: input.attention?.can_wait_summary?.sample_titles ?? [],
        note: "Explainer for suppressed or absent actions — read-model only, not chain-of-thought.",
      },
    },
    trace,
    attention: input.attention,
  };
}
