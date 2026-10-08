"""Ranking endpoint — thin transport over atlas.model, m2.0.0 (ADR 0004).
Single process, one build loaded at boot, cubes in memory, never writes.
Same-origin posture: no CORS middleware, loopback bind, no public API
(D04) — the site reaches this only through its own server-side proxy.

When BUILD_DIR is unset, the fallback loads the single complete build under
data/builds — and REFUSES to guess when more than one is present.

Contract, m2.0.0 (second breaking change after ADR 0003's comparator
removal — both noted here as the contract docs):
  - REMOVED from rows: ratio, ratio_moe, rivals (the rival apparatus left
    the model), cross_group_pairing_rate and its display fields (race
    filters carry no claim about who partners with whom), explanation
    (replaced by summary_line), n_below_100-era reason "no_rivals".
  - ADDED: balance {available, value, per_100, display, standing} — the
    plain sex ratio, gated separately from the pool, present on ranked AND
    suppressed rows; score_display; summary_line; cards (the v3 city-page
    stat cards with national standing bands); display_name / slug per
    metro; counts by reason.
  - marital accepts only never_married / previously_married; the cube
    keeps its third level.
  - m2.1.0 (ADR 0005): weights come from named controls
    {pool_vs_balance: 0..1, importance: {cost|reach|students|weather:
    not_much|some|a_lot}}, mapped through registry constants server-side;
    importance.lifestyle is a deprecated alias landing on both split
    pillars for exactly this version; size_vs_odds is REMOVED (its one
    deprecation version, m2.0.0, has been served). Rows gain the composed
    crime context block; bands are five with direction-derived tones.
    Explicit weight vectors still win.
  - pool_moe and cv are STILL returned (the interval machinery is intact;
    Gate 0's bound stays in the manifest) — they are simply never rendered
    by the site. Technical wording lives under /v1/meta technical_strings.
  - m3.0.0 (ADR 0009): the slider control is pool_vs_match; pool_vs_balance
    is accepted as a deprecated alias for exactly this version (naming
    both is a 422). weights names the match pillar (balance is no longer a
    pillar; an unknown weight key is a 422). self.education and
    self.race_ethnicity are OPTIONAL and sharpen chances of matching; every
    ranked row carries a `match` block {available, value, display, moe,
    unit_line, band} beside its stats entry, and the response carries
    match_inputs (what was disclosed, the national reference rate). The
    balance block stays on every row, displayed and unscored. /v1/meta
    gains controls.slider_labels and controls.self_education_levels (the
    registry's pole labels and the four levels) and a kernel summary.
  - m4.0.0 (ADR 0018, Nathan's decisions): the visitor's own sex,
    education and race never reach the server. `self` carries the own
    age only — self.sex, self.education and self.race_ethnicity are a 422
    — and seeking.sex is required. The response carries every variant
    those three details could select (model.variants): `ranked` holds the
    rows in the default variant's order without the parts a variant
    changes, `suppressed` the rows without balance, and `variants` the
    per-variant columns, the balance for both own sexes, the explanation
    table and the index the browser selects with. The response no longer
    carries balance_applies, balance_words or match_inputs at the top
    (they are per variant), `ranked` is not reversed for worst_first (the
    selector orders by the variant's rank and reverses), the permalink
    token encodes no "about you" detail, and every response says
    Referrer-Policy: no-referrer.
  - m4.1.0 (ADR 0004 amended, Nathan's decision): balance is the single
    people of the sought sex per 100 single people of the other sex, so it
    no longer depends on the visitor's own sex and applies to every search,
    same-sex included. The response sends it once: variants.balance holds
    balance_words and the block of every ranked and suppressed row
    (aligned to them), replacing variants.by_sex (one copy per own sex);
    balance_applies is gone, and /v1/meta no longer carries
    policy_strings.balance_same_sex. It gains
    strings.self_race_same_sex_tip and self_race_same_sex_tip_label (the
    race field's explanation on a same-sex search).
  - Phase 4d (ADR 0019, Nathan's decision): GET /v1/political_lean serves
    each metro's 2024 presidential vote as the city and compare pages show
    it (model.context: the shares, the text, the bar), keyed by CBSA. It
    takes no input. Political lean is context only: /v1/rank neither
    carries it nor accepts it — no request field names it, and its
    response is byte for byte what the build gave before the feature, the
    build id apart. /v1/meta gains the feature's registry entry, its words
    and its stat page.
  - After Phase 4d (ADR 0019 amended, 2026-10-02): POST /v1/profile serves
    one metro's stat cards and crime block — the blocks a ranked or
    suppressed row carries, which no request changes
    (scoring.metro_profile) — for every metro of the build, so the metros
    below the ranked set's population floor, which no search returns, get
    their profile on the city and compare pages. Its body names the metro
    and nothing else ({"cbsa": ...}; any other field is a 422, an unknown
    CBSA a 404). It is a POST so the metro travels in the body, as a
    search does: the API's access lines never say which city a page
    showed. /v1/rank is untouched: its response is byte for byte what it
    was.
  - m4.1.1 (Nathan's report after the launch): a row's summary_line and
    top_stats follow explain.movers. The two price levels are one item,
    "everyday prices", their contributions added, and an item is never
    named against its city's card (a minus where the card says better than
    most, or a plus where it says worse). top_stats lists the named items'
    stats, so an everyday-prices item contributes both of its ids. No
    score, rank, figure, band or suppression changes.
  - m4.2.1 (Phase 5, ADR 0003 amended): the movers line names at most two
    pluses and then the biggest minus, "Biggest pluses: X, Y · Biggest
    minus: Z". Every explanation (variants.explain, and rank()'s rows)
    gains `movers`, [{key, sign}], the pick as data: key the item's first
    stat id, sign +1 or -1. /v1/meta's features gain chip_label, and its
    strings the redesign's labels. No score, rank, figure, band or
    suppression changes.
"""
from __future__ import annotations

import json
import os
from pathlib import Path
from typing import Literal, Optional

from fastapi import FastAPI, HTTPException, Request
from fastapi.responses import JSONResponse
from pydantic import BaseModel, ConfigDict, Field, model_validator

from atlas import model as engine
from atlas.model.context import political_lean_all
from atlas.model.preferences import (ALLOWED_MARITAL, DEPRECATED_SLIDER_ALIAS,
                                     SELECTABLE_RACES, SLIDER_CONTROL)
from atlas.model.scoring import metro_profile
from atlas.model.suppression import (FEW_METROS_NOTICE, GQ_SHARE_FLAG_BAR,
                                     N_GATE_MIN, POLICY_STRINGS,
                                     PURITY_FLAG_BAR, TECHNICAL_STRINGS)

BUILDS_DEFAULT = Path(__file__).resolve().parents[1] / "data" / "builds"


def _resolve_build_dir() -> Path:
    env = os.environ.get("BUILD_DIR")
    if env:
        return Path(env)
    complete = sorted(
        p for p in BUILDS_DEFAULT.iterdir()
        if p.is_dir() and (p / "manifest.json").exists()
        and ((p / "pool_cube.npy").exists() or (p / "fixture.npz").exists()))
    if not complete:
        raise RuntimeError(f"no complete builds under {BUILDS_DEFAULT}; "
                           f"set BUILD_DIR")
    if len(complete) > 1:
        raise RuntimeError(
            "multiple complete builds present: "
            + ", ".join(p.name for p in complete)
            + " — refusing to guess; set BUILD_DIR to the one to serve")
    return complete[0]


BUILD = engine.load_build(_resolve_build_dir())
_METROS_META = json.loads((BUILD.path / "metros.json").read_text())
_METRO_INDEX = {c: i for i, c in enumerate(BUILD.metro_levels)}
app = FastAPI(title="Dating Stats Atlas ranking", docs_url=None, redoc_url=None)


@app.middleware("http")
async def no_referrer(request: Request, call_next):
    """m4.0.0 (ADR 0018): no response of this site's sends a referrer
    onward — every response of the API says so, errors included."""
    response = await call_next(request)
    response.headers["Referrer-Policy"] = "no-referrer"
    return response


# m4.0.0 (ADR 0018): the "about you" details stay in the visitor's browser
ABOUT_YOU_FIELDS = ("sex", "education", "race_ethnicity")


class SelfSpec(BaseModel):
    model_config = ConfigDict(extra="forbid")
    age: int = Field(ge=18, le=70)

    @model_validator(mode="before")
    @classmethod
    def _no_about_you(cls, data):
        if isinstance(data, dict):
            sent = [f"self.{k}" for k in ABOUT_YOU_FIELDS if k in data]
            if sent:
                raise ValueError(
                    f"{', '.join(sent)}: the visitor's own sex, education and race stay in "
                    "their browser and are never sent (ADR 0018); send self.age only — the "
                    "response carries every variant")
        return data


class SeekingSpec(BaseModel):
    sex: Literal["male", "female"]
    age: tuple[int, int]
    education_min: Optional[Literal["some_college", "bachelors", "graduate"]] = None
    income_min: Optional[int] = None
    # m2.0.0: the site counts single people only (ADR 0004)
    marital: list[Literal[tuple(ALLOWED_MARITAL)]]                 # type: ignore[valid-type]
    # m2.2.0 (ADR 0006): eight equal groups — the selection IS the
    # filter, nothing added; zero or all eight means no filter
    race_ethnicity: Optional[list[Literal[tuple(SELECTABLE_RACES)]]] = None  # type: ignore[valid-type]
    religion: Optional[str] = None

    @model_validator(mode="after")
    def _check(self):
        lo, hi = self.age
        if not (18 <= lo <= hi <= 70):
            raise ValueError("seeking.age must satisfy 18 <= lo <= hi <= 70")
        if self.income_min is not None and self.income_min not in engine.INCOME_FLOORS:
            raise ValueError(
                f"income_min must be a cube band edge: {sorted(engine.INCOME_FLOORS)}")
        if not self.marital:
            raise ValueError("seeking.marital must list at least one status")
        if self.religion is not None:
            raise ValueError("religion is the modelled tier and ships in Phase 4")
        return self


class Weights(BaseModel):
    # defaults are float literals: pydantic keeps a default's type, so an
    # int 0 here would make the canonical permalink JSON render "0" for
    # defaulted pillars and "0.0" for user-sent ones — two encodings of the
    # same request. The shared permalink test (web/tests) pins this.
    # m3.0.0: the pillar is match; a stray "balance" key fails loudly
    model_config = ConfigDict(extra="forbid")
    pool: float = Field(ge=0, default=0.0)
    match: float = Field(ge=0, default=0.0)
    reach: float = Field(ge=0, default=0.0)
    cost: float = Field(ge=0, default=0.0)
    weather: float = Field(ge=0, default=0.0)
    students: float = Field(ge=0, default=0.0)


class Importance(BaseModel):
    model_config = ConfigDict(extra="forbid")
    # m2.1.0: four controls. "lifestyle" is the m2.0.0 bundled control,
    # accepted as a deprecated alias for exactly this version — the model
    # applies its level to both split pillars and rejects contradictions.
    cost: Optional[Literal["not_much", "some", "a_lot"]] = None
    reach: Optional[Literal["not_much", "some", "a_lot"]] = None
    students: Optional[Literal["not_much", "some", "a_lot"]] = None
    weather: Optional[Literal["not_much", "some", "a_lot"]] = None
    lifestyle: Optional[Literal["not_much", "some", "a_lot"]] = None


class RankRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")
    data_version: Optional[str] = None
    model_version: Optional[str] = None
    self: SelfSpec
    seeking: SeekingSpec
    weights: Optional[Weights] = None
    pool_vs_match: Optional[float] = Field(default=None, ge=0.0, le=1.0)
    # deprecated alias for exactly m3.0.0 (ADR 0009), as size_vs_odds was
    # for m2.0.0: accepted, mapped, gone next version
    pool_vs_balance: Optional[float] = Field(default=None, ge=0.0, le=1.0)
    importance: Optional[Importance] = None
    sort: Literal["best_first", "worst_first"] = "best_first"
    # size_vs_odds was accepted-but-deprecated for exactly m2.0.0
    # (ADR 0004); m2.1.0 removes it, and an unknown field now fails
    # loudly rather than being silently dropped

    @model_validator(mode="after")
    def _check(self):
        if self.pool_vs_match is not None and self.pool_vs_balance is not None:
            raise ValueError(f"{DEPRECATED_SLIDER_ALIAS} is the deprecated name for "
                             f"{SLIDER_CONTROL}; send one or the other, not both")
        named = (self.pool_vs_match is not None
                 or self.pool_vs_balance is not None
                 or self.importance is not None)
        if self.weights is not None and named:
            raise ValueError("pass either weights or the named controls, not both")
        if self.weights is not None and sum(
                self.weights.model_dump().values()) <= 0:
            raise ValueError("weights must not all be zero")
        return self


@app.get("/v1/health")
def health() -> dict:
    return {"status": "ok",
            "data_version": BUILD.manifest["data_version"],
            "model_version": engine.MODEL_VERSION,
            "schema_version": BUILD.manifest["schema_version"],
            "metros": len(BUILD.metro_levels),
            "ranked_set": int(BUILD.ranked_set.sum()),
            "interval": BUILD.manifest["interval_model"]["validation"],
            "kernel": BUILD.kernel.meta.get("version")}


@app.get("/v1/meta")
def meta() -> dict:
    """Display legend, policy wording, provenance and control vocabulary —
    the single source every rendered label and sentence comes from
    (ADR 0003/0004: no user-facing label lives in code, frontend
    included)."""
    m = BUILD.manifest
    return {
        "data_version": m["data_version"],
        "model_version": engine.MODEL_VERSION,
        "schema_version": m["schema_version"],
        "pillars": m["pillars"],
        "pillar_order": engine.PILLARS,
        "features": m["features_block"],
        # registry-owned strings (m2.1.0) merge over the versioned policy
        # strings: ONE lookup for every rendered sentence, still nothing
        # improvised in a component
        "policy_strings": {**POLICY_STRINGS, **m["strings"]},
        "technical_strings": TECHNICAL_STRINGS,
        "tier_policy": m["tier_policy"],
        "standing_bands": m["standing_bands"],
        "race_groups": m["race_groups"],
        "city_cards": m["city_cards"],
        "stat_pages": m["stat_pages"],
        # Phase 2f item 8.5: What-we-measure composes from this list,
        # never from a hard-coded array of ids in the component
        "measure_page": m["measure_page"],
        "crime": {"year": m["crime"]["year"],
                  "coverage_floor": m["crime"]["coverage_floor"]},
        "interval_model": {k: m["interval_model"][k] for k in
                           ("mechanism", "validation", "copy_rule")},
        "licenses": m.get("licenses", {}),
        "thresholds": {"n_gate_min": N_GATE_MIN,
                       "purity_flag_bar": PURITY_FLAG_BAR,
                       "gq_share_flag_bar": GQ_SHARE_FLAG_BAR,
                       "few_metros_notice": FEW_METROS_NOTICE},
        "controls": {
            "income_band_edges": sorted(engine.INCOME_FLOORS),
            "education_levels": engine.EDU_LEVELS,
            # m3.0.0: the slider's pole labels and the seeker's own
            # education levels (registry-owned wording, never typed by
            # the panel)
            "slider_labels": {
                "low": m["model_defaults"]["size_vs_odds"]["label_low"],
                "high": m["model_defaults"]["size_vs_odds"]["label_high"]},
            "slider_control": SLIDER_CONTROL,
            "slider_deprecated_alias": DEPRECATED_SLIDER_ALIAS,
            "self_education_levels": engine.EDU_LEVELS,
            "marital": list(ALLOWED_MARITAL),
            "race_ethnicity": list(SELECTABLE_RACES),
            "importance_levels": list(m["model_defaults"]["importance_levels"]),
            "importance_pillars": list(engine.IMPORTANCE_PILLARS),
            "age": [18, 70],
        },
        "sources": m["sources"],
        # the kernel's technical record (rendered nowhere; the plain-words
        # account is strings.match_how)
        "kernel": {**BUILD.kernel.meta, "dial_components": list(BUILD.kernel.dial_components)},
        "metros": [{"cbsa": c,
                    "title": BUILD.titles[c],
                    "display_name": BUILD.display_names[i],
                    "display_name_full": BUILD.display_names_full[i],
                    "slug": BUILD.slugs[i],
                    "description": BUILD.descriptions[i],
                    "lat": _METROS_META[i].get("lat"),
                    "lon": _METROS_META[i].get("lon"),
                    "ranked_set": bool(BUILD.ranked_set[i])}
                   for i, c in enumerate(BUILD.metro_levels)],
    }


@app.get("/v1/political_lean")
def political_lean() -> dict:
    """Phase 4d (ADR 0019): how each metro area voted in the 2024
    presidential election — context only, never scored or asked. No
    input; every figure and word composed by the engine from the build and
    the registry (the caption and labels also reach the pages through
    /v1/meta)."""
    if "political_lean" not in BUILD.legend:
        raise HTTPException(404, "this build carries no political lean")
    return {"data_version": BUILD.manifest["data_version"],
            "year": BUILD.legend["political_lean"]["provenance"]["vintage"],
            "metros": political_lean_all(BUILD)}


class ProfileRequest(BaseModel):
    # the metro and nothing else: no search detail can reach a profile
    model_config = ConfigDict(extra="forbid")
    cbsa: str


@app.post("/v1/profile")
def profile(req: ProfileRequest) -> dict:
    """A metro's profile, as its city page shows it: the stat cards and the
    crime block, for any metro of the build — the ranked set's and the ones
    below its population floor, which no search returns. No input but the
    metro, sent in the body so no access line names it; the blocks are the
    ones a rank row carries, made once per metro (scoring.metro_profile)."""
    i = _METRO_INDEX.get(req.cbsa)
    if i is None:
        raise HTTPException(404, f"no metro {req.cbsa!r} in this build")
    return {"data_version": BUILD.manifest["data_version"], "cbsa": req.cbsa,
            **metro_profile(BUILD, i)}


@app.post("/v1/rank")
def rank(req: RankRequest) -> dict:
    dv = BUILD.manifest["data_version"]
    if req.data_version and req.data_version != dv:
        raise HTTPException(409, f"data_version {req.data_version!r} not loaded "
                                 f"(this process serves {dv!r})")
    if req.model_version and req.model_version != engine.MODEL_VERSION:
        raise HTTPException(409, f"model_version {req.model_version!r} != "
                                 f"{engine.MODEL_VERSION!r}")
    body = req.model_dump(exclude_none=True)
    sort = body.pop("sort", "best_first")
    try:
        parsed = engine.parse_request(body)
        result = engine.rank_variants(BUILD, parsed)
    except (ValueError, AssertionError) as e:
        raise HTTPException(status_code=422, detail=str(e)) from e
    # worst_first is a reversal of the same ranked array — same cities,
    # same scores, same ranks, never widened to fill the bottom (ADR 0004);
    # since m4.0.0 the browser's selector reverses the variant it selects
    result["sort"] = sort
    # every value is already a plain JSON type: skip the encoder's walk
    # over the ~1.5 MB of variants
    return JSONResponse({"data_version": dv, "model_version": engine.MODEL_VERSION,
                         "permalink": engine.permalink(dv, engine.MODEL_VERSION, body),
                         **result})
