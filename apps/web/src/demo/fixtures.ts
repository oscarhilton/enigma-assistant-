import type {
  DemoAttentionItem,
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

export const FIXTURE_ATTENTION: DemoAttentionItem[] = [
  {
    id: "att-review-atlas",
    title: "Review Atlas proposal before Friday",
    body: "Open loop from PERSON_A with a calendar deadline this week.",
    kind: "commitment",
    score: 0.91,
    evidence_ids: ["ev-mail-1", "ev-cal-1"],
  },
  {
    id: "att-dentist",
    title: "Confirm dentist appointment",
    body: "Reminder due; no confirmation reply yet.",
    kind: "reminder",
    score: 0.62,
    evidence_ids: ["ev-rem-1"],
  },
];

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

export const FIXTURE_WHY: DemoWhyPayload = {
  item_id: "att-review-atlas",
  headline: "WHY ENIGMA THINKS THIS MATTERS",
  evidence: [
    "Email: PERSON_A requested review.",
    "Email: USER said they would review before Friday.",
    "Calendar: Review meeting Friday 15:00.",
  ],
  inference: ["An unresolved commitment exists."],
  decision: ["Deadline approaching within useful action window.", "Priority: 4"],
  reason_codes: ["USER_COMMITMENT", "DEADLINE_APPROACHING"],
};

export const FIXTURE_WHY_BY_ID: Record<string, DemoWhyPayload> = {
  "att-review-atlas": FIXTURE_WHY,
  "att-dentist": {
    item_id: "att-dentist",
    headline: "WHY ENIGMA THINKS THIS MATTERS",
    evidence: ["Reminder due with no confirmation reply."],
    inference: ["A pending personal follow-up remains open."],
    decision: ["Surfaced at moderate priority.", "Priority: 2"],
    reason_codes: ["EXPLICIT_REQUEST"],
  },
};
