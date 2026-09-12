"""Typed loader for the feature registry, with the §7.2 assertions:
every scoring-referenced feature exists, every entry has complete
provenance, crime is pinned to weight 0, and weights are coherent.
"""
from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

import yaml

REGISTRY_PATH = Path(__file__).resolve().parent / "features.yaml"
PROV_KEYS = {"source", "dataset", "table", "variables", "geography",
             "vintage", "transform_id", "tier"}


@dataclass(frozen=True)
class FeatureSpec:
    id: str
    pillar: str
    kind: str                 # extensive | intensive
    direction: int            # +1 | -1
    weight_in_pillar: float
    computed: str             # per_request | static
    provenance: dict
    status: str = "active"    # active | deferred | context_only
    deviation: str | None = None
    todo: str | None = None


@dataclass(frozen=True)
class Registry:
    version: int
    pillars: dict[str, float]          # pillar -> default weight
    features: dict[str, FeatureSpec]
    naics_venues: dict[str, str]
    pleasant_day: dict
    size_vs_odds: dict
    comparator: dict
    winsor_percentiles: tuple[float, float]
    missing_data_policy: str

    def scored(self) -> list[FeatureSpec]:
        return [f for f in self.features.values()
                if f.status == "active" and f.weight_in_pillar > 0]

    def pillar_features(self, pillar: str) -> list[FeatureSpec]:
        return [f for f in self.scored() if f.pillar == pillar]


def load_registry(path: Path = REGISTRY_PATH) -> Registry:
    raw = yaml.safe_load(path.read_text())
    feats = {}
    for f in raw["features"]:
        spec = FeatureSpec(
            id=f["id"], pillar=f["pillar"], kind=f["kind"],
            direction=int(f["direction"]),
            weight_in_pillar=float(f["weight_in_pillar"]),
            computed=f["computed"], provenance=f["provenance"],
            status=f.get("status", "active"), deviation=f.get("deviation"),
            todo=f.get("todo"))
        assert spec.kind in ("extensive", "intensive"), spec.id
        assert spec.direction in (-1, 1), spec.id
        assert PROV_KEYS <= set(spec.provenance), (
            f"{spec.id}: incomplete provenance, missing "
            f"{PROV_KEYS - set(spec.provenance)}")
        feats[spec.id] = spec

    pillars = {k: float(v["default_weight"]) for k, v in raw["pillars"].items()}
    assert abs(sum(pillars.values()) - 1.0) < 1e-9, pillars
    for p in pillars:
        w = sum(f.weight_in_pillar for f in feats.values()
                if f.pillar == p and f.status == "active")
        assert abs(w - 1.0) < 1e-9, f"pillar {p} feature weights sum to {w}"

    crime = feats["crime_rate_context"]
    assert crime.weight_in_pillar == 0 and crime.status == "context_only", (
        "D01 violated: crime must stay unscored")
    deferred = [f.id for f in feats.values() if f.status == "deferred"]
    for fid in deferred:
        assert feats[fid].weight_in_pillar == 0 and feats[fid].todo, fid

    return Registry(
        version=int(raw["version"]), pillars=pillars, features=feats,
        naics_venues={str(k): str(v) for k, v in raw["naics_venues"].items()},
        pleasant_day=raw["pleasant_day"], size_vs_odds=raw["size_vs_odds"],
        comparator=raw["comparator"],
        winsor_percentiles=tuple(raw["normalization"]["winsor_percentiles"]),
        missing_data_policy=raw["missing_data_policy"].strip())


def assert_scoring_features_registered(referenced: list[str],
                                       reg: Registry) -> None:
    missing = [r for r in referenced if r not in reg.features]
    assert not missing, f"scoring references unregistered features: {missing}"
