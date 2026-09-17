"""Typed loader for the feature registry, with the §7.2 + ADR 0003/0004
assertions: every scoring-referenced feature exists, every entry has
complete provenance AND complete display fields (no user-facing label lives
in code), retired and context features are pinned to weight 0, no display
string uses the banned vocabulary (now including "odds"), and weights are
coherent.

Phase 2d (m2.1.0): standing bands come in FIVES with per-feature
band_direction — the loader derives the tone of each band from direction
alone (good_low, good_high or neutral), so a position label can never be
coloured as a virtue by accident. The registry also owns the crime
context block, the stat-pages list and the new interface strings.
"""
from __future__ import annotations

import re
from dataclasses import dataclass, field
from pathlib import Path

import yaml

REGISTRY_PATH = Path(__file__).resolve().parent / "features.yaml"
PROV_KEYS = {"source", "dataset", "table", "variables", "geography",
             "vintage", "transform_id", "tier"}
# §12.3 / ADR 0003 / ADR 0004: accurate modelling terms, corrosive product
# copy. "odds" joined the list when balance became the plain sex ratio.
BANNED_DISPLAY_TERMS = re.compile(
    r"\b(odds|rivals?|markets?|supply|inventory|competitors?)\b",
    re.IGNORECASE)
STATUSES = ("active", "deferred", "context_only", "retired")
N_BANDS = 5
# tones are DERIVED from direction, one rule for every feature: the two
# low bands, the middle, the two high bands
BAND_DIRECTION_TONES = {
    "good_low": ("good", "good", "neutral", "poor", "poor"),
    "good_high": ("poor", "poor", "neutral", "good", "good"),
    "neutral": ("neutral",) * 5,
}


@dataclass(frozen=True)
class FeatureSpec:
    id: str
    pillar: str
    kind: str                 # extensive | intensive
    direction: int            # +1 | -1
    weight_in_pillar: float
    computed: str             # per_request | static
    provenance: dict
    display_name: str
    unit: str
    definition: str
    unit_short: str = ""
    unit_template: str | None = None
    mover_phrase: str | None = None
    stat_page_name: str | None = None   # "See all cities by {this}"
    band_direction: str | None = None
    band_labels: tuple[str, ...] | None = None
    band_tones: tuple[str, ...] | None = None     # derived from direction
    band_edges: tuple[float, ...] | None = None
    display_scale: float = 1.0
    display_decimals: int = 1
    status: str = "active"
    deviation: str | None = None
    todo: str | None = None
    retired_reason: str | None = None


@dataclass(frozen=True)
class PillarSpec:
    id: str
    default_weight: float
    display_name: str
    definition: str
    control_subtitle: str | None = None


@dataclass(frozen=True)
class Registry:
    version: int
    pillars: dict[str, PillarSpec]
    features: dict[str, FeatureSpec]
    naics_venues: dict[str, str]
    pleasant_day: dict
    size_vs_odds: dict
    importance_levels: dict[str, float]
    standing_bands: dict
    race_groups: tuple[dict, ...]
    city_cards: tuple[str, ...]
    stat_pages: tuple[str, ...]
    crime: dict
    strings: dict[str, str]
    city_description: dict
    winsor_percentiles: tuple[float, float]
    missing_data_policy: str

    @property
    def pillar_weights(self) -> dict[str, float]:
        return {k: p.default_weight for k, p in self.pillars.items()}

    def scored(self) -> list[FeatureSpec]:
        return [f for f in self.features.values()
                if f.status == "active" and f.weight_in_pillar > 0]

    def pillar_features(self, pillar: str) -> list[FeatureSpec]:
        return [f for f in self.scored() if f.pillar == pillar]


def _assert_display_clean(owner: str, *texts) -> None:
    for t in texts:
        m = BANNED_DISPLAY_TERMS.search(str(t or ""))
        assert not m, (f"{owner}: display field contains banned term "
                       f"{m.group(0)!r} (§12.3/ADR 0004): {t!r}")


def load_registry(path: Path = REGISTRY_PATH) -> Registry:
    raw = yaml.safe_load(path.read_text())
    feats = {}
    for f in raw["features"]:
        for k in ("display_name", "unit", "definition"):
            assert k in f, f"{f['id']}: registry entry missing {k} (ADR 0003)"
        spec = FeatureSpec(
            id=f["id"], pillar=f["pillar"], kind=f["kind"],
            direction=int(f["direction"]),
            weight_in_pillar=float(f["weight_in_pillar"]),
            computed=f["computed"], provenance=f["provenance"],
            display_name=str(f["display_name"]), unit=str(f["unit"]),
            definition=str(f["definition"]).strip(),
            unit_short=str(f.get("unit_short", "")),
            unit_template=f.get("unit_template"),
            mover_phrase=f.get("mover_phrase"),
            stat_page_name=f.get("stat_page_name"),
            band_direction=f.get("band_direction"),
            band_labels=tuple(f["band_labels"]) if "band_labels" in f else None,
            band_tones=(BAND_DIRECTION_TONES[f["band_direction"]]
                        if "band_direction" in f else None),
            band_edges=tuple(float(x) for x in f["band_edges"])
                if "band_edges" in f else None,
            display_scale=float(f.get("display_scale", 1.0)),
            display_decimals=int(f.get("display_decimals", 1)),
            status=f.get("status", "active"), deviation=f.get("deviation"),
            todo=f.get("todo"), retired_reason=f.get("retired_reason"))
        assert spec.kind in ("extensive", "intensive"), spec.id
        assert spec.direction in (-1, 1), spec.id
        assert spec.status in STATUSES, (spec.id, spec.status)
        assert PROV_KEYS <= set(spec.provenance), (
            f"{spec.id}: incomplete provenance, missing "
            f"{PROV_KEYS - set(spec.provenance)}")
        if spec.status != "retired":
            # a retired entry's display fields are history, not UI; every
            # live entry's rendered strings stay clean
            _assert_display_clean(spec.id, spec.display_name, spec.unit,
                                  spec.unit_short, spec.unit_template,
                                  spec.mover_phrase, spec.definition,
                                  spec.stat_page_name,
                                  *(spec.band_labels or ()))
        if spec.status == "retired":
            assert spec.weight_in_pillar == 0 and spec.retired_reason, (
                f"{spec.id}: retired entries carry weight 0 and a reason")
        if spec.band_edges is not None:
            assert len(spec.band_edges) == N_BANDS - 1, (
                f"{spec.id}: {N_BANDS} bands need {N_BANDS - 1} edges")
            assert list(spec.band_edges) == sorted(spec.band_edges), spec.id
        if spec.band_labels is not None:
            assert len(spec.band_labels) == N_BANDS, (
                f"{spec.id}: band_labels must name the five bands")
            assert spec.band_direction in BAND_DIRECTION_TONES, (
                f"{spec.id}: band_labels require band_direction "
                f"(one of {sorted(BAND_DIRECTION_TONES)}) — the tone of a "
                f"position comes from direction, never from the position")
        feats[spec.id] = spec

    pillars = {}
    for k, v in raw["pillars"].items():
        assert "display_name" in v and "definition" in v, (
            f"pillar {k}: missing display fields (ADR 0003)")
        pillars[k] = PillarSpec(id=k, default_weight=float(v["default_weight"]),
                                display_name=str(v["display_name"]),
                                definition=str(v["definition"]).strip(),
                                control_subtitle=v.get("control_subtitle"))
        _assert_display_clean(f"pillar {k}", pillars[k].display_name,
                              pillars[k].definition,
                              pillars[k].control_subtitle)
    assert abs(sum(p.default_weight for p in pillars.values()) - 1.0) < 1e-9
    for p in pillars:
        w = sum(f.weight_in_pillar for f in feats.values()
                if f.pillar == p and f.status == "active")
        assert abs(w - 1.0) < 1e-9, f"pillar {p} feature weights sum to {w}"

    for fid in ("violent_crime_rate", "property_crime_rate", "crime_coverage",
                "everyday_prices", "who_lives_here"):
        spec = feats[fid]
        assert spec.weight_in_pillar == 0 and spec.status == "context_only", (
            f"{fid} must stay unscored" + (" (D01)" if "crime" in fid else ""))
    for fid in ("partners_per_rival", "cross_group_pairing_rate"):
        assert feats[fid].status == "retired", (
            f"{fid} left serving in m2.0.0 (ADR 0004)")
    deferred = [f.id for f in feats.values() if f.status == "deferred"]
    for fid in deferred:
        assert feats[fid].weight_in_pillar == 0 and feats[fid].todo, fid

    assert "comparator" not in raw, (
        "the D10 comparator is retired (ADR 0003); remove the registry block")

    levels = {str(k): float(v) for k, v in raw["importance_levels"].items()}
    assert set(levels) == {"not_much", "some", "a_lot"}, levels
    assert all(v > 0 for v in levels.values()), (
        "importance multipliers are floors, never zero (ADR 0004)")
    assert levels["not_much"] < levels["some"] < levels["a_lot"]

    bands = {"edges": [float(x) for x in raw["standing_bands"]["edges"]],
             "keys": [str(k) for k in raw["standing_bands"]["keys"]]}
    assert len(bands["edges"]) == N_BANDS - 1, bands
    assert bands["edges"] == sorted(bands["edges"]), bands
    assert all(0 < e < 100 for e in bands["edges"]), bands
    assert len(bands["keys"]) == N_BANDS, bands

    race_groups = tuple({"id": str(g["id"]), "label": str(g["label"])}
                        for g in raw["race_groups"])
    assert len(race_groups) == 8 and len({g["id"] for g in race_groups}) == 8, (
        "eight equal race groups, one rule (m2.2.0/ADR 0006)")
    for g in race_groups:
        _assert_display_clean(f"race_groups.{g['id']}", g["label"])

    cards = tuple(str(c) for c in raw["city_cards"])
    for c in cards:
        assert c in feats, f"city_cards names unknown feature {c}"
        assert feats[c].band_labels is not None, (
            f"city card {c} needs band_labels")

    stat_pages = tuple(str(c) for c in raw["stat_pages"])
    for c in stat_pages:
        assert c in feats and feats[c].computed == "static", (
            f"stat_pages must name static features; {c} is not "
            f"(matches and balance depend on the visitor's search, and "
            f"crime never gets a ranking page)")
        assert "crime" not in c, "crime never gets a ranking page (D01)"

    crime = raw["crime"]
    assert {"year", "coverage_floor", "implausible_min_pop",
            "implausible_violent_per_100k",
            "implausible_property_per_100k"} <= set(crime), crime
    assert 0.0 < float(crime["coverage_floor"]) < 1.0, crime

    strings = {str(k): str(v).strip() for k, v in raw["strings"].items()}
    for k, v in strings.items():
        _assert_display_clean(f"strings.{k}", v)

    _assert_display_clean("size_vs_odds labels",
                          raw["size_vs_odds"].get("label_low"),
                          raw["size_vs_odds"].get("label_high"))

    desc = raw["city_description"]
    _assert_display_clean("city_description", desc["template"],
                          desc["location_near"], desc["location_far"],
                          *(c["text"] for c in desc["characters"]),
                          *(d["text"] for d in desc["drive_phrases"]))

    return Registry(
        version=int(raw["version"]), pillars=pillars, features=feats,
        naics_venues={str(k): str(v) for k, v in raw["naics_venues"].items()},
        pleasant_day=raw["pleasant_day"], size_vs_odds=raw["size_vs_odds"],
        importance_levels=levels, standing_bands=bands,
        race_groups=race_groups, city_cards=cards,
        stat_pages=stat_pages, crime=dict(crime), strings=strings,
        city_description=desc,
        winsor_percentiles=tuple(raw["normalization"]["winsor_percentiles"]),
        missing_data_policy=raw["missing_data_policy"].strip())


def assert_scoring_features_registered(referenced: list[str],
                                       reg: Registry) -> None:
    missing = [r for r in referenced if r not in reg.features]
    assert not missing, f"scoring references unregistered features: {missing}"
