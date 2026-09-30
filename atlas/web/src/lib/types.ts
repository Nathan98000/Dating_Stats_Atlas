/** Types mirroring the m2.0.0 response contract (ADR 0004) and GET
 * /v1/meta. The API computes every number; these types carry them —
 * nothing here is ever derived arithmetic. */

/** Five tones since m2.3.1 (Phase 2f item 1): the extreme bands read
 * harder than the middles. Derived server-side from band position ×
 * band_direction; the phrase always carries the meaning — colour is
 * never the only signal (WCAG 1.4.1). */
export type Tone = "good_strong" | "good" | "neutral" | "poor" | "poor_strong";

export interface Band {
  key: string; // one of meta.standing_bands.keys (five since m2.1.0)
  standing_all: number;
  label: string;
  tone: Tone;
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

/** Phase 4d (ADR 0019): political lean, as GET /v1/political_lean serves
 * it — context only, never scored or asked. Every string and number is
 * the API's: the text ("56% Democratic · 42% Republican"), the bar's
 * spoken label, and each segment's label, display and width (a share in
 * percent), always Democratic, everyone else, Republican. */
export interface PoliticalLeanSegment {
  key: "dem" | "other" | "rep";
  label: string;
  display: string;
  width: number;
}

export type PoliticalLeanBlock =
  | { available: true; text: string; bar_label: string;
      segments: PoliticalLeanSegment[]; share: { dem: number; rep: number } }
  | { available: false; note: string };

export interface PoliticalLeanResponse {
  data_version: string;
  year: string;
  metros: Record<string, PoliticalLeanBlock>;
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

/** m3.0.0 (ADR 0009): the compatibility figure for a ranked row (named
 * "chances of matching" until m4.0.0, ADR 0018) — the index (100 = the US
 * average for this search), its display string, the unrendered margin
 * (single-seeker path only) and its within-query band. Computed by the
 * API. */
export interface MatchBlock {
  available: boolean;
  value?: number | null;
  /** the API's display string — capped at the registry ceiling with its
   * token ("250+") when `capped` is true (m3.1.0); never parsed back
   * into a number by the site except the compare difference, which
   * skips capped figures */
  display?: string | null;
  capped?: boolean;
  /** m3.2.0: for a same-sex search, the registry sentence saying whose
   * pairing patterns the figure is built from (rendered in the box) */
  note?: string;
  moe?: number | null;
  unit_line?: string;
  band?: Band;
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
  match: MatchBlock;
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
  /** the balance's words: the sought sex and the other sex (the key
   * "seeker" names the other sex — the seeker's own on an opposite-sex
   * search). m4.1.0: balance applies to every search, so there is no
   * balance_applies */
  balance_words: { sought: string; seeker: string };
  match_inputs: MatchInputs;
  ranked: RankedRow[];
  shown_unranked: RankedRow[];
  suppressed: SuppressedRow[];
}

export interface MatchInputs {
  education: string | null;
  race_ethnicity: string | null;
  national_rate: number | null;
  same_sex: boolean;
  same_sex_components: string[];
}

/** m4.0.0 (ADR 0018): what /v1/rank returns. The visitor's own sex,
 * education and race never reach the server, so the response carries
 * every variant those details could select; lib/variants selects one and
 * hands the components a RankResponse. `ranked` rows lack the parts a
 * variant changes; `variants.columns[field][variant][position]` holds
 * them, each variant's rows in its own rank order. The rows' balance
 * travels in `variants.balance`, once (m4.1.0, ADR 0004 amended: it is
 * the search's, whoever is searching). */
export type BaseRow = Omit<RankedRow, "rank" | "score" | "score_display" |
  "balance" | "match" | "top_stats" | "summary_line"> & {
  match: { available: boolean; unit_line: string };
};
export type BaseSuppressedRow = Omit<SuppressedRow, "balance">;

export interface VariantColumns {
  order: number[][];
  rank: number[][];
  score: number[][];
  score_display: string[][];
  value: (number | null)[][];
  display: (string | null)[][];
  capped: number[][];
  band: (number | null)[][];
  standing: (number | null)[][];
  z: (number | null)[][];
  contribution: (number | null)[][];
  explain: number[][];
}

export interface VariantInfo {
  key: string;
  sex: "male" | "female";
  education: string | null;
  race_ethnicity: string | null;
  match_inputs: MatchInputs;
}

export interface Variants {
  default: number;
  sought_sex: "male" | "female";
  /** index[own sex][education or "none"][race or "off"] -> list position */
  index: Record<string, Record<string, Record<string, number>>>;
  same_sex_note: string;
  match_bands: { key: string; label: string; tone: Tone }[];
  explain: { top_stats: string[]; summary_line: string }[];
  /** m4.1.0: the search's balance, once — its words and the block of
   * every ranked and suppressed row, aligned to them (m4.0.0 sent a copy
   * per own sex, `by_sex`) */
  balance: {
    balance_words: RankResponse["balance_words"];
    ranked: BalanceBlock[];
    suppressed: BalanceBlock[];
  };
  list: VariantInfo[];
  columns: VariantColumns;
}

export interface VariantResponse {
  data_version: string;
  model_version: string;
  permalink: string;
  sort: "best_first" | "worst_first";
  counts: RankResponse["counts"];
  weights: Record<string, number>;
  few_metros_notice: boolean;
  ranked: BaseRow[];
  shown_unranked: RankedRow[];
  suppressed: BaseSuppressedRow[];
  variants: Variants;
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
  /** Phase 2f item 8.5: the What-we-measure composition — group headed by
   * a pillar id (or "people"/"context", which name registry strings) over
   * ordered pillar/feature ids; the page composes nothing. */
  measure_page: {
    heading: string;
    pillars?: string[];
    features?: string[];
    crime?: boolean;
  }[];
  licenses: Record<
    string,
    { name: string; url: string; attribution: string | null; notes: string | null;
      /** ADR 0012: the citations the licence asks for, its notice (the
       * Census Bureau Data API's), and the conditions the build keeps */
      citations?: string[]; notice?: string | null; conditions?: string[] }
  >;
  controls: {
    income_band_edges: number[];
    education_levels: string[];
    marital: string[];
    race_ethnicity: string[];
    importance_levels: string[];
    importance_pillars: string[];
    age: [number, number];
    /** m3.0.0: the slider's pole labels and the seeker's own education
     * levels, registry-owned */
    slider_labels: { low: string; high: string };
    slider_control: string;
    self_education_levels: string[];
  };
  kernel: Record<string, unknown>;
  metros: MetroMeta[];
}
