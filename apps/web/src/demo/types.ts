/**
 * Demo Mode UI payload types.
 *
 * Three representation layers (do not collapse them in the UI):
 *
 * PRIVATE UI — what the fictional user sees locally (Maya, Atlas, Friday 15:00).
 *   The Attention dashboard uses this layer.
 *
 * MODEL VIEW — what a hosted model may see (PERSON_A, PROJECT_B, DATE_T_PLUS_2).
 *   Why / privacy inspector surfaces may show this transformed layer.
 *
 * EXTERNAL ATTENTION — coarsened outward summaries ("a work follow-up").
 *   Not the default dashboard copy.
 */

export type DemoStatus = {
  active: boolean;
  mode: string;
  banner: string;
  scenario: string | null;
  simulated_time: string | null;
  speed: number | null;
  paused: boolean | null;
  storage_root: string | null;
  ground_truth_visible: boolean;
};

/** Attention card fields — priority ≠ confidence; rank ≠ confidence. */
export type DemoAttentionItem = {
  id: string;
  /** WHAT — private UI title (real synthetic names). */
  title: string;
  /** WHEN — human timing glance ("Before Friday"). */
  when: string | null;
  /** Glance "why now" without opening provenance. */
  why_now_glance: string | null;
  /** Human-readable summary (not reason-code prose). */
  body: string;
  kind: string;
  /** Discrete priority 1–5 (how much this matters). */
  priority: number;
  /** Interpretation confidence 0–1 (not a priority score). */
  confidence: number;
  /**
   * Deterministic attention rank for ordering.
   * Conceptually urgency × importance × actionability × timing × confidence —
   * confidence must not act as priority by itself.
   */
  attention_rank: number;
  evidence_ids: string[];
};

export type DemoAttentionPayload = {
  items: DemoAttentionItem[];
  simulated_time?: string | null;
  surfaced_count?: number;
  suppressed_count?: number;
};

export type DemoMemoryItem = {
  id: string;
  category: string;
  statement: string;
  confidence: number;
  evidence_count: number;
  first_observed: string;
  last_observed: string;
};

export type DemoWhyPayload = {
  item_id: string;
  headline: string;
  evidence: string[];
  inference: string[];
  decision: string[];
  /** Timing rationale — why surface *now* vs merely "this matters". */
  why_now: string[];
  priority: number;
  confidence: number;
  reason_codes: string[];
};

export type DemoAttentionActionResult = {
  ok: boolean;
  item_id: string;
  action: "done" | "snooze";
  items: DemoAttentionItem[];
  surfaced_count?: number;
  suppressed_count?: number;
};
