import type { ForensicModel, CopyTier } from "./types";

const PRIVATE_KEYS = new Set([
  "privateperson",
  "private_person",
  "notes",
  "wholesale_notes",
  "raw_email",
  "contact_identities",
]);

function stripPrivate(value: unknown): unknown {
  if (Array.isArray(value)) {
    return value.map(stripPrivate);
  }
  if (!value || typeof value !== "object") {
    return value;
  }
  const next: Record<string, unknown> = {};
  for (const [key, child] of Object.entries(value as Record<string, unknown>)) {
    if (PRIVATE_KEYS.has(key.toLowerCase())) {
      continue;
    }
    next[key] = stripPrivate(child);
  }
  return next;
}

function sectionSummary(model: ForensicModel) {
  return {
    user_input: model.userInput.status === "wired" ? "present" : model.userInput.status,
    turn_contract: model.turnContract.status,
    evidence: model.evidence.status,
    not_disclosed: model.notDisclosed.status,
    relational_bootstrap: model.relationalBootstrap.status,
    handoff: model.handoff.status,
    agent_work: model.agentWork.status,
    authority: model.authority.status,
    remote_payload: model.remotePayload.status,
    streaming_trace: model.streamingTrace.status,
    memory: model.memory.status,
  };
}

export function buildCopyBundle(model: ForensicModel, tier: CopyTier): string {
  if (tier === "safe") {
    return JSON.stringify(
      stripPrivate({
        tier: "safe",
        snapshot: model.snapshot,
        sections: sectionSummary(model),
        why_not: {
          suppressed_count: model.whyNot.data.suppressedCount,
          sample_titles: model.whyNot.data.sampleTitles.slice(0, 3),
        },
        agent_work: {
          exists: model.agentWork.data.exists,
          phase: model.agentWork.data.phase,
          semantic_token: model.agentWork.data.semanticToken,
        },
        egress: {
          blocked: model.notDisclosed.data.blocked,
          excluded_categories: model.notDisclosed.data.excluded,
        },
      }),
      null,
      2,
    );
  }

  if (tier === "detailed") {
    return JSON.stringify(
      stripPrivate({
        tier: "detailed",
        snapshot: model.snapshot,
        user_input: model.userInput.data,
        turn_contract: model.turnContract.data,
        evidence: {
          provenance_headline: model.evidence.data.provenance?.headline ?? null,
          evidence_ids: model.evidence.data.evidenceIds,
          activity_labels: model.evidence.data.activityLabels,
        },
        not_disclosed: model.notDisclosed.data,
        relational_bootstrap: model.relationalBootstrap.data,
        handoff: model.handoff.data,
        agent_work: model.agentWork.data,
        authority: model.authority.data,
        remote_payload: {
          payload_hash: model.remotePayload.data.disclosure?.payload_hash ?? null,
          purpose: model.remotePayload.data.disclosure?.purpose ?? null,
          provider: model.remotePayload.data.disclosure?.provider ?? null,
          included: model.remotePayload.data.disclosure?.included ?? [],
          excluded: model.remotePayload.data.disclosure?.excluded ?? model.notDisclosed.data.excluded,
          field_summary: model.remotePayload.data.disclosure?.payload_field_summary ?? null,
        },
        streaming_trace: model.streamingTrace.data,
        memory: model.memory.data,
        why_not: model.whyNot.data,
      }),
      null,
      2,
    );
  }

  return JSON.stringify(
    {
      tier: "local_forensic",
      warning: "Local forensic bundle — may contain user text. Do not share without review.",
      model,
      trace: model.trace,
      attention: model.attention,
    },
    null,
    2,
  );
}

export function parseCopyBundle(text: string): unknown {
  return JSON.parse(text) as unknown;
}
