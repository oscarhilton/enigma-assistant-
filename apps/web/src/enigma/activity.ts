import type { LlmTrace, LlmTraceToolResult } from "./types";

/** Canonical conversation-activity kinds (product vocabulary). */
export const CANONICAL_ACTIVITY_KINDS = [
  "availability.checked",
  "attention.queried",
  "referent.resolved",
  "world.explained",
  "assist.proposed",
  "assist.approved",
  "assist.executing",
  "assist.verified",
  "egress.allowed",
] as const;

/** Extra kinds for C09 tools that are real hops but not in the short product list. */
export const EXTENDED_ACTIVITY_KINDS = [
  "agenda.queried",
  "next_action.queried",
  "next_action.alternatives",
  "next_action.rejected",
  "duration.checked",
  "world.changes",
  "world.waiting",
] as const;

export type CanonicalActivityKind = (typeof CANONICAL_ACTIVITY_KINDS)[number];
export type ExtendedActivityKind = (typeof EXTENDED_ACTIVITY_KINDS)[number];
export type ActivityKind = CanonicalActivityKind | ExtendedActivityKind;

export type ActivityPhase = "started" | "done";

/**
 * One Core hop, projected three ways (NORMAL / CURIOUS / FORENSIC).
 * Not a parallel cognition log — derived from llm_trace / items / disclosures.
 */
export type EnigmaActivityEvent = {
  id: string;
  kind: ActivityKind;
  at: string;
  phase: ActivityPhase;
  label: string;
  source_tool?: string | null;
  subject_id?: string | null;
  forensic_only?: boolean;
};

export type ConversationTurnPartKind =
  | "user"
  | "activity"
  | "prose"
  | "next_action"
  | "assist"
  | "collapsed_activity";

type ToolActivitySpec = {
  kind: ActivityKind;
  label: string;
  forensic_only?: boolean;
  assist_card?: boolean;
};

const TOOL_ACTIVITY: Record<string, ToolActivitySpec> = {
  "availability.check": { kind: "availability.checked", label: "Checked your calendar" },
  "availability.time_fit": { kind: "availability.checked", label: "Checked your calendar" },
  "agenda.get": { kind: "agenda.queried", label: "Checked your week" },
  "briefing.read": { kind: "agenda.queried", label: "Checked your week" },
  "calendar.agenda.get": { kind: "agenda.queried", label: "Checked your calendar" },
  "attention.get_current": { kind: "attention.queried", label: "Checked what needs you" },
  "context.resolve_referent": {
    kind: "referent.resolved",
    label: "Matched this to the token inventory",
  },
  "world.explain": { kind: "world.explained", label: "Checked why this matters" },
  "attention.explain_why": { kind: "world.explained", label: "Checked why this matters" },
  "world.get_changes": { kind: "world.changes", label: "Checked what changed" },
  "world.get_blockers": { kind: "world.waiting", label: "Checked what you're waiting on" },
  "next_action.get": { kind: "next_action.queried", label: "Checked what's worth doing" },
  "next_action.get_alternatives": {
    kind: "next_action.alternatives",
    label: "Looked for something else",
  },
  "next_action.reject": { kind: "next_action.rejected", label: "Noted you'd rather not" },
  "referent.get_duration": { kind: "duration.checked", label: "Checked how long this takes" },
  "assist.propose": { kind: "assist.proposed", label: "Prepared an action", assist_card: true },
  "assist.approve": { kind: "assist.approved", label: "Approved", assist_card: true },
  "assist.execute": { kind: "assist.executing", label: "Sending the note", assist_card: true },
  "assist.verify": { kind: "assist.verified", label: "Checking whether the note sent" },
};

export function isAssistCardKind(kind: ActivityKind): boolean {
  return (
    kind === "assist.proposed" ||
    kind === "assist.approved" ||
    kind === "assist.executing" ||
    kind === "assist.verified"
  );
}

export function isThreadActivity(event: EnigmaActivityEvent): boolean {
  return !event.forensic_only && !isAssistCardKind(event.kind);
}

function subjectIdFromResult(result: LlmTraceToolResult): string | null {
  const data = result.data;
  if (!data || typeof data !== "object") {
    return null;
  }
  const value = data.subject_id ?? data.current_subject_id;
  return typeof value === "string" ? value : null;
}

export function projectActivityFromTrace(
  trace: LlmTrace,
  options?: { at?: string },
): EnigmaActivityEvent[] {
  const at = options?.at ?? new Date().toISOString();
  const events: EnigmaActivityEvent[] = [];

  trace.tool_results.forEach((result, index) => {
    const spec = TOOL_ACTIVITY[result.name];
    if (!spec || !result.ok) {
      return;
    }
    events.push({
      id: `${trace.correlation_id ?? "turn"}-${result.name}-${index}`,
      kind: spec.kind,
      at,
      phase: "done",
      label: spec.label,
      source_tool: result.name,
      subject_id:
        subjectIdFromResult(result) ?? trace.conversation_state?.current_subject_id ?? null,
      forensic_only: spec.forensic_only ?? false,
    });
  });

  if (trace.disclosure && !trace.disclosure.blocked) {
    events.push({
      id: `${trace.disclosure.id}-egress`,
      kind: "egress.allowed",
      at,
      phase: "done",
      label: "Remote inference allowed",
      source_tool: null,
      subject_id: trace.conversation_state?.current_subject_id ?? null,
      forensic_only: true,
    });
  }

  return events;
}

export function threadActivityFromTrace(
  trace: LlmTrace,
  options?: { at?: string },
): EnigmaActivityEvent[] {
  return projectActivityFromTrace(trace, options).filter(isThreadActivity);
}
