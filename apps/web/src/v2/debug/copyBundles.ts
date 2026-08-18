import { NOT_CAPTURED, type CopyTier, type ForensicModel, type ForensicSection } from "./types";

const PRIVATE_KEYS = new Set([
  "privateperson",
  "private_person",
  "notes",
  "wholesale_notes",
  "raw_email",
  "contact_identities",
]);

const PRIVACY_LEVEL: Record<CopyTier, string> = {
  safe: "SAFE",
  detailed: "DETAILED",
  local: "LOCAL",
};

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

function capturedOrNot<T>(section: ForensicSection<T>): unknown {
  if (section.status === "wired") {
    return section.data;
  }
  return NOT_CAPTURED;
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

function bundleHeader(model: ForensicModel, tier: CopyTier): string {
  const turn =
    model.snapshot.turnIndex > 0 ? `${model.snapshot.turnIndex} / ${model.snapshot.turnCount}` : "none";
  return [
    "ENIGMA FORENSIC SNAPSHOT",
    `Build: ${model.snapshot.buildCommit}`,
    `World: ${model.snapshot.worldLabel} (${model.snapshot.world})`,
    `Turn: ${turn}`,
    `Privacy level: ${PRIVACY_LEVEL[tier]}`,
    "",
  ].join("\n");
}

function withHeader(model: ForensicModel, tier: CopyTier, body: unknown): string {
  return `${bundleHeader(model, tier)}${JSON.stringify(body, null, 2)}\n`;
}

export function buildCopyBundle(model: ForensicModel, tier: CopyTier): string {
  if (tier === "safe") {
    return withHeader(
      model,
      tier,
      stripPrivate({
        tier: "safe",
        snapshot: model.snapshot,
        sections: sectionSummary(model),
        why_not: capturedOrNot(model.whyNot),
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
    );
  }

  if (tier === "detailed") {
    return withHeader(
      model,
      tier,
      stripPrivate({
        tier: "detailed",
        snapshot: model.snapshot,
        user_input: model.userInput.data,
        turn_contract: capturedOrNot(model.turnContract),
        evidence: {
          provenance_headline: model.evidence.data.provenance?.headline ?? null,
          evidence_ids: model.evidence.data.evidenceIds,
          activity_labels: model.evidence.data.activityLabels,
        },
        not_disclosed: model.notDisclosed.data,
        relational_bootstrap: capturedOrNot(model.relationalBootstrap),
        handoff: capturedOrNot(model.handoff),
        agent_work: model.agentWork.data,
        authority: capturedOrNot(model.authority),
        remote_payload: {
          payload_hash: model.remotePayload.data.disclosure?.payload_hash ?? null,
          purpose: model.remotePayload.data.disclosure?.purpose ?? null,
          provider: model.remotePayload.data.disclosure?.provider ?? null,
          included: model.remotePayload.data.disclosure?.included ?? [],
          excluded: model.remotePayload.data.disclosure?.excluded ?? model.notDisclosed.data.excluded,
          field_summary: model.remotePayload.data.disclosure?.payload_field_summary ?? null,
        },
        streaming_trace: capturedOrNot(model.streamingTrace),
        memory: capturedOrNot(model.memory),
        why_not: capturedOrNot(model.whyNot),
      }),
    );
  }

  return withHeader(model, tier, {
    tier: "local_forensic",
    warning: "Local forensic bundle — may contain user text. Do not share without review.",
    model,
    trace: model.trace,
    attention: model.attention,
  });
}

export function parseCopyBundle(text: string): unknown {
  const jsonStart = text.indexOf("{");
  if (jsonStart < 0) {
    throw new Error("Copy bundle has no JSON body");
  }
  return JSON.parse(text.slice(jsonStart)) as unknown;
}
