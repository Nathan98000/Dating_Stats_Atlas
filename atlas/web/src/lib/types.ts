/** Types mirroring the m2.0.0 response contract (ADR 0004) and GET
 * /v1/meta. The API computes every number; these types carry them —
 * nothing here is ever derived arithmetic. */

export interface Band {
  key: "low" | "mid" | "high";
  standing_all: number;
  label: string;
  tone: "good" | "neutral" | "poor";
}

export interface Stat {
  id: string;
  pillar?: string;
  value: number | null;
  display?: string;
  standing?: number;
  z?: number;
  weight?: number;
  contribution?: number | null;
  missing?: boolean;
  band?: Band;
}

export interface Card {
  id: string;
  value: number | null;
  display?: string;
  unit_line?: string;
  band?: Band;
  missing?: boolean;
}

export interface BalanceBlock {
  available: boolean;
  note?: string;
  value?: number;
  per_100?: number;
  display?: string;
  sought_word?: string;
  seeker_word?: string;
  standing?: number | null;
}

export interface RankedRow {
  cbsa: string;
  name: string;
  display_name: string;
  slug: string;
  rank: number;
  score: number;
  score_display: string;
  pool: number;
  pool_moe: number;
  cv: number;
  n_unweighted: number;
  tier: string;
  balance: BalanceBlock;
  allocation_purity: number;
  flags: string[];
  stats: Stat[];
  cards: Card[];
  contributions: { pillar: string; value: number }[];
  top_stats: string[];
  summary_line: string;
}

export interface SuppressedRow {
  cbsa: string;
  name: string;
  display_name: string;
  slug: string;
  reason: string;
  n_unweighted: number;
  flags: string[];
  balance: BalanceBlock;
  cards: Card[];
}

export interface RankResponse {
  data_version: string;
  model_version: string;
  permalink: string;
  sort: "best_first" | "worst_first";
  counts: {
    universe: number;
    ranked: number;
    shown_unranked: number;
    suppressed: number;
    suppressed_by_reason: Record<string, number>;
  };
  weights: Record<string, number>;
  few_metros_notice: boolean;
  balance_applies: boolean;
  balance_words: { sought: string; seeker: string };
  ranked: RankedRow[];
  shown_unranked: RankedRow[];
  suppressed: SuppressedRow[];
}

export interface FeatureLegend {
  pillar: string;
  kind: string;
  direction: number;
  weight_in_pillar: number;
  status: string;
  display_name: string;
  unit: string;
  unit_short: string;
  unit_template?: string | null;
  mover_phrase?: string | null;
  band_labels?: string[] | null;
  band_tones?: string[] | null;
  definition: string;
  display_scale: number;
  display_decimals: number;
  provenance: Record<string, unknown>;
}

export interface MetroMeta {
  cbsa: string;
  title: string;
  display_name: string;
  display_name_full: string;
  slug: string;
  description: string;
  lat: number;
  lon: number;
  ranked_set: boolean;
}

export interface Meta {
  data_version: string;
  model_version: string;
  pillars: Record<
    string,
    { display_name: string; definition: string; default_weight: number }
  >;
  pillar_order: string[];
  features: Record<string, FeatureLegend>;
  policy_strings: Record<string, string>;
  technical_strings: Record<string, string>;
  standing_bands: { low_below: number; high_above: number };
  city_cards: string[];
  licenses: Record<
    string,
    { name: string; url: string; attribution: string | null; notes: string | null }
  >;
  controls: {
    income_band_edges: number[];
    education_levels: string[];
    marital: string[];
    race_ethnicity: string[];
    importance_levels: string[];
    age: [number, number];
  };
  metros: MetroMeta[];
}
