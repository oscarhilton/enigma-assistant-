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

export type DemoAttentionItem = {
  id: string;
  title: string;
  body: string;
  kind: string;
  score: number;
  evidence_ids: string[];
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
  reason_codes: string[];
};
