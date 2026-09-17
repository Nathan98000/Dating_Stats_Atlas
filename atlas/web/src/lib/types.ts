/** Types mirroring the m2.0.0 response contract (ADR 0004) and GET
 * /v1/meta. The API computes every number; these types carry them —
 * nothing here is ever derived arithmetic. */

export interface Band {
  key: string; // one of meta.standing_bands.keys (five since m2.1.0)
  standing_all: number;
  label: string;
  tone: "good" | "neutral" | "poor";
}

/** Crime context (never scored): rates arrive only with their coverage
 * figure and the FBI's caution — since Phase 2e as two CARDS whose
 * detail lives in the ⓘ popover, plus the compare page's banner. */
export interface CrimeBlock {
  available: boolean;
  caution: string;
  card_blank: string;
  card_info_label: string;
  compare_banner: string;
  note?: string;
  coverage_line?: string;
  coverage_pct?: number;
  stats?: { id: string; label: string; value: number; display: string;
            unit_line: string; band?: Band }[];
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
  crime: CrimeBlock;
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
  crime: CrimeBlock;
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
  stat_page_name?: string | null;
  band_direction?: "good_low" | "good_high" | "neutral" | null;
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
    { display_name: string; definition: string; default_weight: number;
      control_subtitle?: string | null }
  >;
  pillar_order: string[];
  features: Record<string, FeatureLegend>;
  policy_strings: Record<string, string>;
  technical_strings: Record<string, string>;
  standing_bands: { edges: number[]; keys: string[] };
  race_groups: { id: string; label: string }[];
  city_cards: string[];
  stat_pages: string[];
  crime: { year: number; coverage_floor: number };
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
    importance_pillars: string[];
    age: [number, number];
  };
  metros: MetroMeta[];
}
