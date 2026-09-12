"""Typed provenance and license contracts (§6.1, §4.6).

Every number that can reach a screen carries a Provenance record, and every
source carries LicenseTerms with a `shippable` flag. The build asserts that
no artifact field traces to a non-shippable source, and that the manifest's
recorded variable lists match the variables the adapters actually requested
— a provenance string can no longer drift from the query (the Phase 1
manifest said DHC "P5" while the code correctly queried P18; that class of
bug is now structurally impossible).
"""
from __future__ import annotations

from dataclasses import asdict, dataclass, field


@dataclass(frozen=True)
class LicenseTerms:
    name: str                     # e.g. "US public domain (17 USC 105)"
    url: str
    shippable: bool               # may derived values enter the serving artifact?
    attribution: str | None = None
    notes: str | None = None


@dataclass(frozen=True)
class Provenance:
    source: str                   # "census_acs", "bea", "epa", ...
    dataset: str                  # "acs/acs5 2020-2024 5-year PUMS"
    table: str                    # "P18", "B25064", "csv_p{st}.zip", ...
    variables: tuple[str, ...]    # exactly what the adapter requested
    geography: str                # "tract", "cbsa", "block group (2010)", ...
    vintage: str                  # "2020-2024", "2020", "2024", ...
    transform_id: str             # short id of the derivation, e.g. "gq_alloc_v2"
    tier: str                     # "measured" | "modelled" | "context"

    def as_dict(self) -> dict:
        d = asdict(self)
        d["variables"] = list(self.variables)
        return d


@dataclass
class Report:
    """Adapter validation outcome; a failed hard check fails the build."""
    source_id: str
    passed: bool
    checks: list[str] = field(default_factory=list)
    failures: list[str] = field(default_factory=list)


def assert_all_shippable(provenances: dict[str, Provenance],
                         licenses: dict[str, LicenseTerms]) -> None:
    """No artifact field may trace to a non-shippable source."""
    bad = [k for k, p in provenances.items()
           if not licenses[p.source].shippable]
    assert not bad, f"artifact fields trace to non-shippable sources: {bad}"


def assert_manifest_matches_requests(manifest_vars: dict[str, list[str]],
                                     requested: dict[str, list[str]]) -> None:
    """The manifest's recorded variable list must equal what the code asked
    the source for — recorded per source key, compared exactly."""
    for key, want in requested.items():
        got = manifest_vars.get(key)
        assert got == sorted(want), (
            f"manifest provenance drift for {key!r}: manifest={got} "
            f"requested={sorted(want)}")
