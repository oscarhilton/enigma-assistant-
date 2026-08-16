/**
 * Demo Mode UI payload types.
 *
 * Three representation layers (do not collapse them in the UI):
 *
 * PRIVATE UI — what the fictional user sees locally (Maya, Friday deadlines).
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
  /** Total signals in the attention window (surfaced + suppressed). */
  signals_considered?: number | null;
  /** Attention items currently on the surface (D08e / D10 stats). */
  surfaced_count?: number | null;
  /** Signals considered but not surfaced (background + noise). */
  suppressed_count?: number | null;
  /** Alias for noise-layer suppression when D08d streams contribute. */
  noise_suppressed_count?: number | null;
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
  signals_considered?: number;
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
  signals_considered?: number;
  surfaced_count?: number;
  suppressed_count?: number;
};

/** Engine suppression reason for the developer inspector (not ScenarioSignalClass). */
export type DemoSuppressionReason =
  | "background"
  | "newsletter"
  | "spam"
  | "low_priority"
  | "duplicate"
  | "resolved";

export type DemoSuppressedItem = {
  id: string;
  message: string;
  suppression_reason: DemoSuppressionReason;
  classification: string;
  open_obligation: string;
  relationship_relevance: string;
  deadline: string;
  decision: "suppressed";
  why_not: string[];
};

export type DemoSuppressedPayload = {
  developer_only: boolean;
  filters: DemoSuppressionReason[];
  filter: DemoSuppressionReason | null;
  signals_considered: number;
  surfaced_count: number;
  suppressed_count: number;
  sample_count: number;
  items: DemoSuppressedItem[];
  simulated_time?: string | null;
};
