import { MOCK_ATTENTION_JAN19 } from "../enigma/fixtures";
import type {
  AssistProposal,
  AttentionState,
  ConversationItem,
  LlmTrace,
  ProvenanceView,
} from "../enigma/types";

export const MONDAY_CHECKPOINT_ID = MOCK_ATTENTION_JAN19.checkpoint_id ?? "cp-2026-01-19T10:00";
const BRUNCH_CHECKPOINT_ID = "cp-2026-01-20T11:00";

/** P02b — monday_maya.yaml */
export const MAYA_BIRTHDAY_CASE_ID = "item-context_maya_birthday";
export const MAYA_BIRTHDAY_TITLE = "Sort something for Maya's birthday";
export const MAYA_OPENING_PROMPT =
  "I've got work Monday, so Sunday's probably my only chance to sort Maya's birthday.";
export const MAYA_OPENING_REPLY =
  "I checked your calendar. Monday 26 Jan is a bank holiday here — that does not mean you are off work. Maya's birthday is 24 Feb (mail-maya-birthday), so this Sunday is not your only window.";
export const MAYA_CONTINUE_PROMPT = "So Sunday is still my best shot though?";
export const MAYA_CONTINUE_REPLY =
  "Sunday 25 Jan could work for planning — but being wrong about Monday 26 changes the plan. The bank holiday is on the calendar; your work pattern is not.";

/** P02c — honk_honk.yaml */
export const HONK_ESTABLISH_PROMPT = "Hey — still here if you need me.";
export const HONK_PROMPT = "honk honk";
export const HONK_REPLY = "honk honk — got it.";
export const HONK_SERIOUS_PROMPT = "Actually, something serious has happened.";
export const HONK_SERIOUS_REPLY =
  "I hear you. Tell me what happened — I'll stay direct and leave the playful register out of this.";
export const HONK_RECOVERY_PROMPT = "honk honk";
export const HONK_RECOVERY_REPLY = "honk — I'm still with you.";

/** P02d — verification_failure.yaml */
export const NOTIFY_TEAM_CASE_ID = "item-notify-team";
export const NOTIFY_TEAM_TITLE = "Send the team note";
export const NOTIFY_TEAM_PROPOSAL_ID = "assist-notify-team";
export const VERIFICATION_PREPARE_PROMPT = "Can you help me send the team note?";
export const VERIFICATION_APPROVE_PROMPT = "Go on then.";
export const VERIFICATION_CHECK_PROMPT = "Did you actually do it?";
export const VERIFICATION_OUTCOME_PROMPT = "So... did it work?";
export const VERIFICATION_ACTING_REPLY = "Sending the note now.";
export const VERIFICATION_VERIFYING_REPLY =
  "Checking whether the note actually sent — verification is separate from acting.";
export const VERIFICATION_FAILURE_REPLY =
  "I could not verify that the note sent. Nothing was recorded as completed.";
export const VERIFICATION_FAILURE_RESULT =
  "Could not verify that the note sent — the assist did not succeed.";

/** P02e — forget.yaml */
export const FORGET_RETAIN_PROMPT = "Maya mentioned she likes ceramics.";
export const FORGET_RETAIN_ACK = "Got it — I'll remember Maya likes ceramics for gift ideas.";
export const FORGET_RECALL_PROMPT = "What does Maya like?";
export const FORGET_RECALL_REPLY = "Maya likes ceramics — you mentioned that earlier.";
export const FORGET_PROMPT = "Forget that.";
export const FORGET_ACK = "Okay — I will drop that retained memory from what I use now.";
export const FORGET_AFTER_RECALL_REPLY =
  "I do not have that retained memory anymore. I am not claiming it was deleted everywhere yet — ask again later if you want to re-establish it.";

const PLAYFUL_BOOTSTRAP = {
  relational_bootstrap: {
    kind: "relational_bootstrap",
    continuation: { culture_palette_available: true },
  },
};

const RESTRAINED_BOOTSTRAP = {
  relational_bootstrap: {
    kind: "relational_bootstrap",
    continuation: { culture_palette_available: false },
  },
};

const MONDAY_ATTENTION: AttentionState = {
  ...MOCK_ATTENTION_JAN19,
  context: [
    ...MOCK_ATTENTION_JAN19.context,
    {
      id: MAYA_BIRTHDAY_CASE_ID,
      title: MAYA_BIRTHDAY_TITLE,
      explanation: "Maya's birthday is 24 Feb — relevant, not urgent today.",
      policy_decision: "context",
      bucket: "context",
      rank: 2,
      composite_score: 0.55,
      actionability_now: 0.4,
      reasons: [{ code: "RELATIONSHIP", label: "Relationship context" }],
      evidence_ids: ["mail-maya-birthday"],
    },
    {
      id: NOTIFY_TEAM_CASE_ID,
      title: NOTIFY_TEAM_TITLE,
      explanation: "You wanted to notify the team — still open.",
      policy_decision: "context",
      bucket: "context",
      rank: 3,
      composite_score: 0.5,
      actionability_now: 0.6,
      reasons: [{ code: "USER_COMMITMENT", label: "You committed" }],
      evidence_ids: ["mail-team-note"],
    },
  ],
};

const MAYA_PROVENANCE: ProvenanceView = {
  item_id: MAYA_BIRTHDAY_CASE_ID,
  headline: "WHY ENIGMA HOLDS THIS",
  evidence: ["mail-maya-birthday", "cal-bank-holiday-2026-01-26"],
  inference: [
    "mail-maya-birthday places Maya's birthday on 24 Feb.",
    "cal-bank-holiday-2026-01-26 is a calendar fact — not a work schedule rule.",
  ],
  decision: ["QUALIFIES the Sunday-only premise; does not invent user time off."],
  why_now: [
    "Bank holiday Monday 26 Jan is on the calendar; that is not the same as knowing you are off work.",
  ],
  reason_codes: ["RELATIONSHIP", "CALENDAR_PROXIMITY"],
};

const FORGET_PROVENANCE_ACTIVE: ProvenanceView = {
  item_id: "memory-maya-ceramics",
  headline: "WHY ENIGMA HOLDS THIS",
  evidence: ["retained-memory-maya-ceramics"],
  inference: ["User reported Maya likes ceramics in this session."],
  decision: ["Available for semantic recall until forget."],
  why_now: ["Retained memory — not a source deletion."],
  reason_codes: ["USER_REPORTED"],
};

const FORGET_PROVENANCE_AFTER: ProvenanceView = {
  item_id: "memory-maya-ceramics",
  headline: "WHY ENIGMA HOLDS THIS",
  evidence: [],
  inference: ["Forget was requested — propagation may still be in flight."],
  decision: ["Do not claim deletion completed before propagation."],
  why_now: ["Memory dropped from assistant surface; stale vectors must not resurrect it."],
  reason_codes: ["USER_REPORTED"],
};

function baseTrace(userMessage: string, subjectId: string | null = null): LlmTrace {
  return {
    path: "llm",
    planner: "EgressConversationLLM",
    user_message: userMessage,
    conversation_state: {
      current_subject_id: subjectId,
      current_subject_kind: subjectId ? "attention_item" : null,
    },
    tools_available: [
      "agenda.get",
      "availability.check",
      "world.explain",
      "assist.propose",
      "assist.approve",
      "assist.execute",
      "assist.verify",
    ],
    remote_context_sent: null,
    model_tool_request: [],
    tool_results: [],
    model_response: [],
    intent_name: "life_script",
    router_fallback: false,
    disclosure_id: null,
    disclosure: null,
    included: ["simulated time"],
    excluded: ["PRIVATE_RAW", "raw email bodies"],
    correlation_id: `corr-life-${userMessage.length}`,
  };
}

export function traceForMayaOpening(): LlmTrace {
  return {
    ...baseTrace(MAYA_OPENING_PROMPT, MAYA_BIRTHDAY_CASE_ID),
    remote_context_sent: { simulated_time: MONDAY_ATTENTION.simulated_time },
    tool_results: [
      {
        name: "agenda.get",
        ok: true,
        data: {
          subject_id: MAYA_BIRTHDAY_CASE_ID,
          bank_holiday: "2026-01-26",
          birthday: "2026-02-24",
        },
      },
    ],
  };
}

export function traceForMayaContinue(): LlmTrace {
  return {
    ...baseTrace(MAYA_CONTINUE_PROMPT, MAYA_BIRTHDAY_CASE_ID),
    tool_results: [
      {
        name: "availability.check",
        ok: true,
        data: { subject_id: MAYA_BIRTHDAY_CASE_ID, period: "this_weekend" },
      },
    ],
  };
}

export function traceForHonk(playful: boolean): LlmTrace {
  return {
    ...baseTrace(HONK_PROMPT),
    remote_context_sent: playful ? PLAYFUL_BOOTSTRAP : RESTRAINED_BOOTSTRAP,
    tool_results: [
      {
        name: "world.explain",
        ok: true,
        data: { subject_id: MAYA_BIRTHDAY_CASE_ID },
      },
    ],
  };
}

export function traceForHonkSerious(): LlmTrace {
  return {
    ...baseTrace(HONK_SERIOUS_PROMPT),
    remote_context_sent: RESTRAINED_BOOTSTRAP,
    tool_results: [
      {
        name: "world.explain",
        ok: true,
        data: { subject_id: MAYA_BIRTHDAY_CASE_ID },
      },
    ],
  };
}

export function traceForHonkRecovery(): LlmTrace {
  return {
    ...baseTrace(HONK_RECOVERY_PROMPT),
    remote_context_sent: PLAYFUL_BOOTSTRAP,
    tool_results: [
      {
        name: "world.explain",
        ok: true,
        data: { subject_id: MAYA_BIRTHDAY_CASE_ID },
      },
    ],
  };
}

export function traceForVerificationPrepare(): LlmTrace {
  return {
    ...baseTrace(VERIFICATION_PREPARE_PROMPT, NOTIFY_TEAM_CASE_ID),
    tool_results: [
      {
        name: "assist.propose",
        ok: true,
        data: { subject_id: NOTIFY_TEAM_CASE_ID },
      },
    ],
  };
}

export function traceForVerificationActing(): LlmTrace {
  return {
    ...baseTrace(VERIFICATION_APPROVE_PROMPT, NOTIFY_TEAM_CASE_ID),
    tool_results: [
      {
        name: "assist.execute",
        ok: true,
        data: { subject_id: NOTIFY_TEAM_CASE_ID },
      },
      {
        name: "world.explain",
        ok: true,
        data: { subject_id: NOTIFY_TEAM_CASE_ID },
      },
    ],
  };
}

export function traceForVerificationChecking(): LlmTrace {
  return {
    ...baseTrace(VERIFICATION_CHECK_PROMPT, NOTIFY_TEAM_CASE_ID),
    tool_results: [
      {
        name: "assist.verify",
        ok: true,
        data: { subject_id: NOTIFY_TEAM_CASE_ID },
      },
      {
        name: "world.explain",
        ok: true,
        data: { subject_id: NOTIFY_TEAM_CASE_ID },
      },
    ],
  };
}

export function traceForVerificationFailure(): LlmTrace {
  return {
    ...baseTrace(VERIFICATION_OUTCOME_PROMPT, NOTIFY_TEAM_CASE_ID),
    tool_results: [
      {
        name: "assist.verify",
        ok: false,
        data: { subject_id: NOTIFY_TEAM_CASE_ID, verified: false },
      },
      {
        name: "world.explain",
        ok: true,
        data: { subject_id: NOTIFY_TEAM_CASE_ID },
      },
    ],
  };
}

export function notifyTeamProposal(at: string): ConversationItem {
  const proposal: AssistProposal = {
    id: NOTIFY_TEAM_PROPOSAL_ID,
    title: NOTIFY_TEAM_TITLE,
    description: "I'll send a synthetic demo note to the team channel.",
    action_label: "Approve",
  };
  return {
    kind: "assist_proposal",
    at,
    proposal,
    llm_trace: traceForVerificationPrepare(),
  };
}

export function mondayAttentionState(): AttentionState {
  return structuredClone(MONDAY_ATTENTION);
}

export function mondayOpeningConversation(): ConversationItem[] {
  return [
    {
      kind: "attention_summary",
      at: MONDAY_ATTENTION.simulated_time,
      state: mondayAttentionState(),
    },
  ];
}

export function provenanceForItem(
  itemId: string,
  options?: { ceramicsForgotten?: boolean },
): ProvenanceView | null {
  if (itemId === MAYA_BIRTHDAY_CASE_ID) {
    return structuredClone(MAYA_PROVENANCE);
  }
  if (itemId === "memory-maya-ceramics") {
    return structuredClone(
      options?.ceramicsForgotten ? FORGET_PROVENANCE_AFTER : FORGET_PROVENANCE_ACTIVE,
    );
  }
  return null;
}

export function isMondayCheckpoint(checkpointId: string | null | undefined): boolean {
  return checkpointId === MONDAY_CHECKPOINT_ID;
}

export function isBrunchCheckpoint(checkpointId: string | null | undefined): boolean {
  return checkpointId === BRUNCH_CHECKPOINT_ID;
}

export type LifeScriptSession = {
  honkSerious: boolean;
  verificationApproved: boolean;
  retainedCeramics: boolean;
  ceramicsForgotten: boolean;
};

export function freshLifeScriptSession(): LifeScriptSession {
  return {
    honkSerious: false,
    verificationApproved: false,
    retainedCeramics: false,
    ceramicsForgotten: false,
  };
}
