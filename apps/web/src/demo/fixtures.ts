import type {
  DemoAttentionItem,
  DemoAttentionPayload,
  DemoMemoryItem,
  DemoStatus,
  DemoWhyPayload,
} from "./types";

export const FIXTURE_STATUS: DemoStatus = {
  active: true,
  mode: "demo",
  banner: "DEMO MODE — FICTIONAL DATA ONLY",
  scenario: "alex-v1",
  simulated_time: "2026-01-01T09:00:00+00:00",
  speed: 1,
  paused: false,
  storage_root: "/tmp/enigma-demo/alex-v1",
  ground_truth_visible: false,
};

export const FIXTURE_DEMO_STATUS = FIXTURE_STATUS;

/** Private UI names on the dashboard (Maya, Atlas) — not PERSON_*. */
export const FIXTURE_ATTENTION: DemoAttentionItem[] = [
  {
    id: "att-atlas-review",
    title: "Review Atlas proposal before Friday",
    when: "Before Friday",
    why_now_glance: "Deadline approaching",
    body: "You said you'd review this before Friday, and it still appears unfinished.",
    kind: "commitment",
    priority: 4,
    confidence: 0.91,
    attention_rank: 0.86,
    evidence_ids: ["ev-mail-1", "ev-cal-1"],
  },
  {
    id: "att-maya-scheduling",
    title: "Follow up with Maya on scheduling",
    when: null,
    why_now_glance: "Thread waiting on you",
    body: "This scheduling thread still appears to be waiting on you.",
    kind: "follow_up",
    priority: 3,
    confidence: 0.72,
    attention_rank: 0.61,
    evidence_ids: ["ev-mail-2"],
  },
];

export const FIXTURE_ATTENTION_PAYLOAD: DemoAttentionPayload = {
  items: FIXTURE_ATTENTION,
  surfaced_count: 2,
  suppressed_count: 47,
  simulated_time: FIXTURE_STATUS.simulated_time,
};

export const FIXTURE_MEMORY: DemoMemoryItem[] = [
  {
    id: "mem-person-a",
    category: "People",
    statement: "PERSON_A is a frequent collaborator on PROJECT_B.",
    confidence: 0.86,
    evidence_count: 4,
    first_observed: "2026-01-10T09:00:00+00:00",
    last_observed: "2026-03-14T10:30:00+00:00",
  },
  {
    id: "mem-project-b",
    category: "Projects",
    statement: "PROJECT_B has an upcoming review milestone.",
    confidence: 0.74,
    evidence_count: 3,
    first_observed: "2026-01-12T11:00:00+00:00",
    last_observed: "2026-03-14T09:03:00+00:00",
  },
  {
    id: "mem-open-loop",
    category: "Open loops",
    statement: "USER committed to review PROJECT_B before Friday.",
    confidence: 0.9,
    evidence_count: 2,
    first_observed: "2026-03-14T09:03:00+00:00",
    last_observed: "2026-03-14T11:12:00+00:00",
  },
];

/** Why payloads may use MODEL VIEW pseudonyms (PERSON_A) for privacy contrast. */
export const FIXTURE_WHY: DemoWhyPayload = {
  item_id: "att-atlas-review",
  headline: "WHY ENIGMA THINKS THIS MATTERS",
  evidence: [
    "Email: PERSON_A requested review.",
    "Email: USER said they would review before Friday.",
    "Calendar: Review meeting Friday at 15:00.",
  ],
  inference: [
    "USER made a commitment to PERSON_A.",
    "No evidence of completion has been observed.",
    "The commitment appears due before the Friday review.",
  ],
  decision: [
    "The commitment remains unresolved.",
    "Its deadline falls within the configured attention window.",
    "Surface as a high-priority item.",
  ],
  why_now: [
    "The deadline is approaching.",
    "There is still enough time to act before the review.",
  ],
  priority: 4,
  confidence: 0.91,
  reason_codes: ["USER_COMMITMENT", "DEADLINE_APPROACHING"],
};

export const FIXTURE_WHY_BY_ID: Record<string, DemoWhyPayload> = {
  "att-atlas-review": FIXTURE_WHY,
  "att-maya-scheduling": {
    item_id: "att-maya-scheduling",
    headline: "WHY ENIGMA THINKS THIS MATTERS",
    evidence: [
      "Email: PERSON_A proposed times that remain unanswered.",
      "Calendar: No matching hold on USER's schedule.",
    ],
    inference: [
      "A scheduling follow-up with PERSON_A remains open.",
      "No evidence USER closed the thread.",
    ],
    decision: [
      "The follow-up is unresolved.",
      "It falls inside the configured attention window.",
      "Surface as a medium-priority item.",
    ],
    why_now: [
      "The thread is still waiting on USER.",
      "Surface now while the window to respond is open.",
    ],
    priority: 3,
    confidence: 0.72,
    reason_codes: ["CROSS_SOURCE_MATCH", "FOLLOW_UP_REQUIRED", "UNRESOLVED_THREAD"],
  },
};
