"""Typed loader for the feature registry, with the §7.2 + ADR 0003/0004
assertions: every scoring-referenced feature exists, every entry has
complete provenance AND complete display fields (no user-facing label lives
in code), retired and context features are pinned to weight 0, no display
string uses the banned vocabulary (now including "odds"), band labels come
in threes with valid tones, and weights are coherent.
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
BAND_TONES = ("good", "neutral", "poor")


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
    band_labels: tuple[str, ...] | None = None
    band_tones: tuple[str, ...] | None = None
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


@dataclass(frozen=True)
class Registry:
    version: int
    pillars: dict[str, PillarSpec]
    features: dict[str, FeatureSpec]
    naics_venues: dict[str, str]
    pleasant_day: dict
    size_vs_odds: dict
    importance_levels: dict[str, float]
    standing_bands: dict[str, float]
    city_cards: tuple[str, ...]
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
            band_labels=tuple(f["band_labels"]) if "band_labels" in f else None,
            band_tones=tuple(f["band_tones"]) if "band_tones" in f else None,
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
                                  *(spec.band_labels or ()))
        if spec.status == "retired":
            assert spec.weight_in_pillar == 0 and spec.retired_reason, (
                f"{spec.id}: retired entries carry weight 0 and a reason")
        if spec.band_edges is not None:
            assert len(spec.band_edges) == 2, spec.id
            assert spec.band_edges[0] < spec.band_edges[1], spec.id
        if spec.band_labels is not None:
            assert len(spec.band_labels) == 3, (
                f"{spec.id}: band_labels must name the three bands")
            assert spec.band_tones is not None and len(spec.band_tones) == 3, (
                f"{spec.id}: band_labels require band_tones")
            assert all(t in BAND_TONES for t in spec.band_tones), spec.id
        feats[spec.id] = spec

    pillars = {}
    for k, v in raw["pillars"].items():
        assert "display_name" in v and "definition" in v, (
            f"pillar {k}: missing display fields (ADR 0003)")
        pillars[k] = PillarSpec(id=k, default_weight=float(v["default_weight"]),
                                display_name=str(v["display_name"]),
                                definition=str(v["definition"]).strip())
        _assert_display_clean(f"pillar {k}", pillars[k].display_name,
                              pillars[k].definition)
    assert abs(sum(p.default_weight for p in pillars.values()) - 1.0) < 1e-9
    for p in pillars:
        w = sum(f.weight_in_pillar for f in feats.values()
                if f.pillar == p and f.status == "active")
        assert abs(w - 1.0) < 1e-9, f"pillar {p} feature weights sum to {w}"

    for fid in ("crime_rate_context", "everyday_prices", "who_lives_here"):
        spec = feats[fid]
        assert spec.weight_in_pillar == 0 and spec.status == "context_only", (
            f"{fid} must stay unscored")
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

    bands = {str(k): float(v) for k, v in raw["standing_bands"].items()}
    assert set(bands) == {"low_below", "high_above"}
    assert 0 < bands["low_below"] < bands["high_above"] < 100

    cards = tuple(str(c) for c in raw["city_cards"])
    for c in cards:
        assert c in feats, f"city_cards names unknown feature {c}"
        assert feats[c].band_labels is not None, (
            f"city card {c} needs band_labels")

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
        importance_levels=levels, standing_bands=bands, city_cards=cards,
        city_description=desc,
        winsor_percentiles=tuple(raw["normalization"]["winsor_percentiles"]),
        missing_data_policy=raw["missing_data_policy"].strip())


def assert_scoring_features_registered(referenced: list[str],
                                       reg: Registry) -> None:
    missing = [r for r in referenced if r not in reg.features]
    assert not missing, f"scoring references unregistered features: {missing}"
