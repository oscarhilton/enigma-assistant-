/** Cortex observability events — projected from audit/state feeds, never written back to Core. */

export type BrainRegion = "input" | "centre" | "upper" | "right" | "membrane" | "shadow";

export const BRAIN_REGION_LABELS: Record<
  BrainRegion,
  { title: string; description: string; layout: "left" | "centre" | "upper" | "right" | "lower" | "shadow" }
> = {
  input: {
    title: "Input",
    description: "Sources — email, calendar, messages",
    layout: "left",
  },
  centre: {
    title: "Centre",
    description: "Identity, entities, world model, relationships, commitments",
    layout: "centre",
  },
  upper: {
    title: "Upper",
    description: "Attention, urgency, opportunity",
    layout: "upper",
  },
  right: {
    title: "Right",
    description: "Support, next actions, assists",
    layout: "right",
  },
  membrane: {
    title: "Membrane",
    description: "Privacy transform, egress, audit",
    layout: "lower",
  },
  shadow: {
    title: "Shadow",
    description: "Abstract retained state after decay / forget",
    layout: "shadow",
  },
};

export type BrainEventBase = {
  id: string;
  at: string;
  region: BrainRegion;
  checkpoint_id?: string | null;
};

export type SourceIngestedEvent = BrainEventBase & {
  type: "source_ingested";
  region: "input";
  source_kind: string;
  record_id?: string | null;
};

export type WorldStateChangedEvent = BrainEventBase & {
  type: "world_state_changed";
  region: "centre";
  summary: string;
};

export type RelationAddedEvent = BrainEventBase & {
  type: "relation_added";
  region: "centre";
  relation_kind: string;
  from_ref?: string | null;
  to_ref?: string | null;
};

export type AttentionQualifiedEvent = BrainEventBase & {
  type: "attention_qualified";
  region: "upper";
  policy_decision?: "surface" | "context" | "suppress" | null;
  needs_you_count?: number | null;
  proactive_silence?: boolean;
};

export type NextActionCreatedEvent = BrainEventBase & {
  type: "next_action_created";
  region: "right";
  action_id?: string | null;
  title?: string | null;
};

export type PrivacyTransformEvent = BrainEventBase & {
  type: "privacy_transform";
  region: "membrane";
  purpose: string;
  provider: string;
  blocked: boolean;
  block_reason?: string | null;
};

export type EgressEvent = BrainEventBase & {
  type: "egress";
  region: "membrane";
  purpose: string;
  provider: string;
  model: string;
  byte_count: number;
  payload_hash: string;
};

export type MemoryDecayedEvent = BrainEventBase & {
  type: "memory_decayed";
  region: "shadow";
  zone: "active" | "shadow";
  record_ref?: string | null;
};

export type MemoryForgottenEvent = BrainEventBase & {
  type: "memory_forgotten";
  region: "shadow";
  record_ref?: string | null;
};

export type BrainEvent =
  | SourceIngestedEvent
  | WorldStateChangedEvent
  | RelationAddedEvent
  | AttentionQualifiedEvent
  | NextActionCreatedEvent
  | PrivacyTransformEvent
  | EgressEvent
  | MemoryDecayedEvent
  | MemoryForgottenEvent;

export type BrainEventType = BrainEvent["type"];

export type RetentionStage = "source" | "active" | "shadow" | "forgotten";

/** Stub metrics for SEC-07 slider until benchmark report is wired. */
export type RetentionStageMetrics = {
  stage: RetentionStage;
  utility_pct: number;
  reconstructability_pct: number;
};

export const RETENTION_STAGE_METRICS: RetentionStageMetrics[] = [
  { stage: "source", utility_pct: 98, reconstructability_pct: 95 },
  { stage: "active", utility_pct: 92, reconstructability_pct: 55 },
  { stage: "shadow", utility_pct: 88, reconstructability_pct: 4 },
  { stage: "forgotten", utility_pct: 40, reconstructability_pct: 0 },
];

export function formatBrainEventLabel(event: BrainEvent): string {
  switch (event.type) {
    case "source_ingested":
      return `Source ingested · ${event.source_kind}`;
    case "world_state_changed":
      return `World state · ${event.summary.replace(/_/g, " ")}`;
    case "relation_added":
      return `Relation · ${event.relation_kind}`;
    case "attention_qualified":
      if (event.proactive_silence) {
        return "Attention · proactive silence";
      }
      return `Attention · ${event.policy_decision ?? "evaluated"}${
        event.needs_you_count != null ? ` (${event.needs_you_count} needs you)` : ""
      }`;
    case "next_action_created":
      return `Next action · ${event.title ?? event.action_id ?? "created"}`;
    case "privacy_transform":
      return event.blocked
        ? `Privacy block · ${event.purpose}`
        : `Privacy transform · ${event.purpose}`;
    case "egress":
      return `Egress · ${event.purpose} → ${event.provider}/${event.model}`;
    case "memory_decayed":
      return `Memory decay · ${event.zone}`;
    case "memory_forgotten":
      return `Memory forgotten · ${event.record_ref ?? "record"}`;
    default: {
      const _exhaustive: never = event;
      return String(_exhaustive);
    }
  }
}
