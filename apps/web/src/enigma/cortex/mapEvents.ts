import type { EnigmaEvent } from "../events";
import type { DemoEvent, EgressDisclosure } from "../types";
import type { BrainEvent } from "./events";

let sequence = 0;

function brainId(prefix: string): string {
  sequence += 1;
  return `${prefix}-${sequence}`;
}

export function projectDemoEvent(event: DemoEvent): BrainEvent[] {
  const base = {
    at: event.at,
    checkpoint_id: event.checkpoint_id ?? null,
  };

  switch (event.kind) {
    case "checkpoint_loaded":
    case "checkpoint_jump":
      return [
        {
          type: "world_state_changed",
          region: "centre",
          id: brainId("world"),
          summary: event.kind,
          ...base,
        },
      ];
    case "attention_surfaced":
      return [
        {
          type: "attention_qualified",
          region: "upper",
          id: brainId("attention"),
          policy_decision: "surface",
          needs_you_count: event.needs_you_count ?? null,
          proactive_silence: false,
          ...base,
        },
      ];
    case "proactive_silence":
      return [
        {
          type: "attention_qualified",
          region: "upper",
          id: brainId("attention"),
          policy_decision: "suppress",
          needs_you_count: event.needs_you_count ?? null,
          proactive_silence: true,
          ...base,
        },
      ];
    default:
      return [
        {
          type: "world_state_changed",
          region: "centre",
          id: brainId("world"),
          summary: event.kind,
          ...base,
        },
      ];
  }
}

export function projectEnigmaEvent(event: EnigmaEvent): BrainEvent[] {
  if (event.type === "demo_event") {
    return projectDemoEvent(event.event);
  }
  if (event.type === "attention_changed") {
    return [
      {
        type: "world_state_changed",
        region: "centre",
        id: brainId("world"),
        at: new Date().toISOString(),
        checkpoint_id: event.checkpoint_id,
        summary: "attention_changed",
      },
    ];
  }
  return [];
}

export function projectEgressDisclosure(disclosure: EgressDisclosure): BrainEvent {
  if (disclosure.blocked) {
    return {
      type: "privacy_transform",
      region: "membrane",
      id: brainId("privacy"),
      at: disclosure.timestamp,
      purpose: disclosure.purpose,
      provider: disclosure.provider,
      blocked: true,
      block_reason: disclosure.block_reason ?? null,
    };
  }
  return {
    type: "egress",
    region: "membrane",
    id: brainId("egress"),
    at: disclosure.timestamp,
    purpose: disclosure.purpose,
    provider: disclosure.provider,
    model: disclosure.model,
    byte_count: disclosure.byte_count,
    payload_hash: disclosure.payload_hash,
    request_profile: disclosure.context_manifest?.profile ?? null,
  };
}

export function projectDemoEvents(events: DemoEvent[]): BrainEvent[] {
  return events.flatMap(projectDemoEvent);
}

export function mergeBrainEvents(...groups: BrainEvent[][]): BrainEvent[] {
  const seen = new Set<string>();
  const merged: BrainEvent[] = [];
  for (const group of groups) {
    for (const event of group) {
      const key = `${event.type}:${event.at}:${event.id}`;
      if (seen.has(key)) {
        continue;
      }
      seen.add(key);
      merged.push(event);
    }
  }
  return merged.sort((a, b) => a.at.localeCompare(b.at));
}

/** Test helper — reset monotonic id sequence. */
export function resetBrainEventIdsForTests(): void {
  sequence = 0;
}
