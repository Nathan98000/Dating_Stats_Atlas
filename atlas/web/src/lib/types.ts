/** Types mirroring the §8.2 response contract (as amended by ADRs
 * 0002/0003) and GET /v1/meta. The API computes every number; these types
 * carry them — nothing here is ever derived arithmetic. */

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
  moe?: number;
  moe_display?: string;
  n_unweighted?: number;
  suppressed?: string;
}

export interface RankedRow {
  cbsa: string;
  name: string;
  rank: number;
  score: number;
  score_moe: number;
  pool: number;
  pool_moe: number;
  cv: number;
  n_unweighted: number;
  tier: string;
  ratio: number;
  ratio_moe: number;
  rivals: number;
  allocation_purity: number;
  flags: string[];
  stats: Stat[];
  contributions: { pillar: string; value: number }[];
  explanation: string;
  top_stats?: string[];
  cross_group_pairing_rate: number | null;
  cross_group_pairing_moe?: number;
  cross_group_pairing_n?: number;
  cross_group_pairing_display?: string;
  cross_group_pairing_moe_display?: string;
  cross_group_pairing_suppressed?: string;
}

export interface SuppressedRow {
  cbsa: string;
  name: string;
  reason: string;
  n_unweighted: number;
  flags: string[];
  stats: Stat[];
}

export interface RankResponse {
  data_version: string;
  model_version: string;
  permalink: string;
  counts: {
    universe: number;
    ranked: number;
    shown_unranked: number;
    suppressed: number;
    suppressed_by_reason: Record<string, number>;
  };
  weights: Record<string, number>;
  few_metros_notice: boolean;
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
  definition: string;
  display_scale: number;
  display_decimals: number;
  provenance: {
    source: string;
    dataset: string;
    table: string;
    variables: string[];
    geography: string;
    vintage: string;
    transform_id: string;
    tier: string;
  };
}

export interface Meta {
  data_version: string;
  model_version: string;
  schema_version: string;
  pillars: Record<
    string,
    { display_name: string; definition: string; default_weight: number }
  >;
  pillar_order: string[];
  features: Record<string, FeatureLegend>;
  policy_strings: Record<string, string>;
  tier_policy: Record<string, string>;
  interval_model: {
    mechanism: string;
    copy_rule: string;
    validation: Record<string, unknown>;
  };
  model_defaults: {
    pillar_weights: Record<string, number>;
    size_vs_odds: {
      pool_plus_balance_mass: number;
      default_s: number;
      label_low: string;
      label_high: string;
    };
  };
  licenses: Record<
    string,
    {
      name: string;
      url: string;
      shippable: boolean;
      attribution: string | null;
      notes: string | null;
    }
  >;
  thresholds: Record<string, number>;
  controls: {
    income_band_edges: number[];
    education_levels: string[];
    marital: string[];
    race_ethnicity: string[];
    age: [number, number];
  };
  sources: Record<string, unknown>;
  metros: { cbsa: string; title: string; ranked_set: boolean }[];
}

export interface ApiError {
  status: number;
  detail: string;
}
