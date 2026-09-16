"""Typed loader for the feature registry, with the §7.2 + ADR 0003
assertions: every scoring-referenced feature exists, every entry has
complete provenance AND complete display fields (no user-facing label lives
in code), crime and the pairing counterweight are pinned to weight 0, no
display string uses the §12.3 banned vocabulary, and weights are coherent.
"""
from __future__ import annotations

import re
from dataclasses import dataclass
from pathlib import Path

import yaml

REGISTRY_PATH = Path(__file__).resolve().parent / "features.yaml"
PROV_KEYS = {"source", "dataset", "table", "variables", "geography",
             "vintage", "transform_id", "tier"}
# §12.3 / ADR 0003: accurate modelling terms, corrosive product copy.
BANNED_DISPLAY_TERMS = re.compile(
    r"\b(rivals?|markets?|supply|inventory|competitors?)\b", re.IGNORECASE)


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
    unit_short: str = ""      # sentence-context suffix; "" when the
    display_scale: float = 1.0  # display_name already carries the unit
    display_decimals: int = 1
    status: str = "active"    # active | deferred | context_only
    deviation: str | None = None
    todo: str | None = None


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


def _assert_display_clean(owner: str, *texts: str) -> None:
    for t in texts:
        m = BANNED_DISPLAY_TERMS.search(t or "")
        assert not m, (f"{owner}: display field contains banned term "
                       f"{m.group(0)!r} (§12.3/ADR 0003): {t!r}")


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
            display_scale=float(f.get("display_scale", 1.0)),
            display_decimals=int(f.get("display_decimals", 1)),
            status=f.get("status", "active"), deviation=f.get("deviation"),
            todo=f.get("todo"))
        assert spec.kind in ("extensive", "intensive"), spec.id
        assert spec.direction in (-1, 1), spec.id
        assert PROV_KEYS <= set(spec.provenance), (
            f"{spec.id}: incomplete provenance, missing "
            f"{PROV_KEYS - set(spec.provenance)}")
        _assert_display_clean(spec.id, spec.display_name, spec.unit,
                              spec.unit_short, spec.definition)
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

    for fid in ("crime_rate_context", "cross_group_pairing_rate"):
        spec = feats[fid]
        assert spec.weight_in_pillar == 0 and spec.status == "context_only", (
            f"{fid} must stay unscored "
            f"({'D01' if fid.startswith('crime') else 'ADR 0003 counterweight'})")
    deferred = [f.id for f in feats.values() if f.status == "deferred"]
    for fid in deferred:
        assert feats[fid].weight_in_pillar == 0 and feats[fid].todo, fid

    assert "comparator" not in raw, (
        "the D10 comparator is retired (ADR 0003); remove the registry block")

    return Registry(
        version=int(raw["version"]), pillars=pillars, features=feats,
        naics_venues={str(k): str(v) for k, v in raw["naics_venues"].items()},
        pleasant_day=raw["pleasant_day"], size_vs_odds=raw["size_vs_odds"],
        winsor_percentiles=tuple(raw["normalization"]["winsor_percentiles"]),
        missing_data_policy=raw["missing_data_policy"].strip())


def assert_scoring_features_registered(referenced: list[str],
                                       reg: Registry) -> None:
    missing = [r for r in referenced if r not in reg.features]
    assert not missing, f"scoring references unregistered features: {missing}"
