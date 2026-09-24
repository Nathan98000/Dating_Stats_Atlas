"""Phase 3c, B1 (ADR 0011): the rank-stability gate that reads the whole
picture. A change fails only if it makes rankings shakier overall, not
because two near-tied cities swapped places in one search.

The measure — a search's WOBBLE. For each of the 80 replicate versions of
the survey, take every city in the top 10 of either the published ranking
or that version's ranking, measure how many places each moved between the
two rankings, and average those moves; the search's wobble is that average
over the 80 versions. A swap between 10th and 11th counts one place for
each city; a city jumping from 40th into the top 10 counts thirty.

The test searches: the eighteen golden personas, the Phase 3b effects grid
(both sexes at 25/30/35/40/50, undisclosed, each education level, each
race group and each education x race, the grid's window and marital
selection), and a same-sex grid (men seeking men and women seeking women
at the same ages, education undisclosed or each level). Identical requests
count once; a search that ranks fewer than 12 metros is skipped. These
serve the gate only; the golden fixture does not change.

The verdict: a change FAILS if its total wobble is more than 10% above the
reference's total, both summed over the same searches — those the change
touches, meaning any whose index (point or replicate) differs from the
reference's; when nothing is touched the totals run over every search, so
the reference against itself reads exactly 1.0. The reference is m3.2.0
(f20cb02c3af8), fixed in results/phase3c/stability_reference.json and
moved only by Nathan's decision in an ADR, so small rises cannot pile up
release after release.

The replicate machinery is the validation suite's (the same pool, the
same replicate weights, the same score function); the kernel-weighted
numerator is composed in numpy from the masked pool's per-cell replicate
sums, which do not depend on the kernel and are cached on disk
(data/phase3c_cache/) so every kernel is read against bit-identical sums.

    python -m atlas.pipeline.build.stability_gate reference <build_dir>
        -> results/phase3c/stability_reference.json
    python -m atlas.pipeline.build.stability_gate check <build_dir> --name <n> [--kernel <dir>] [--noise 1.5]
        -> results/phase3c/gate_<n>.json (the record and the verdict)
    python -m atlas.pipeline.build.stability_gate controls <build_dir>
        -> results/phase3c/gate_controls.json (identity; enlarged noise x1.5)
"""
from __future__ import annotations

import hashlib
import json
import sys
import time
from dataclasses import replace
from pathlib import Path

import numpy as np

from atlas import model as engine
from atlas.model.preferences import EDU_LEVELS, RACE_LEVELS, SEX_LEVELS, seeker_weights
from atlas.model.scoring import score_vector
from atlas.model.tests.golden.make_fixture import GOLDEN_VECTORS
from atlas.pipeline.fetch import DATA, RESULTS

P3C = RESULTS / "phase3c"
REFERENCE = P3C / "stability_reference.json"
CACHE = DATA / "phase3c_cache"
TOLERANCE = 0.10          # a change fails above 1 + TOLERANCE times the reference
RISE_FLAG = 0.25          # searches whose wobble rose more than this are named (findings)
TOP = 10
OVERLAP_OLD = 8           # the old rule, kept as a soft reading
GRID_AGES = (25, 30, 35, 40, 50)
MIN_RANKED = 12
N_REP = 80


# ---------------------------------------------------------------------------
# the test searches
# ---------------------------------------------------------------------------

def grid_body(sex: str, age: int, edu: str | None = None, race: str | None = None,
              same_sex: bool = False) -> dict:
    """The Phase 3b effects grid's request (phase3b_refine_effects.body_for):
    the site's default window (age - 2 to age + 10) and marital selection;
    `same_sex` seeks the seeker's own sex."""
    self_ = {"sex": sex, "age": age}
    if edu:
        self_["education"] = edu
    if race:
        self_["race_ethnicity"] = {v: k for k, v in engine.SPEC_RACE.items()}[race]
    seeking = {"age": [max(18, age - 2), min(70, age + 10)],
               "marital": ["never_married", "previously_married"]}
    if same_sex:
        seeking["sex"] = sex
    return {"self": self_, "seeking": seeking}


def test_searches() -> list[tuple[str, dict]]:
    """(name, request body) — personas, the effects grid, the same-sex grid;
    identical requests count once (the first name wins)."""
    out: list[tuple[str, dict]] = []
    for v in GOLDEN_VECTORS:
        body = {k: v[k] for k in ("self", "seeking", "weights", "pool_vs_match",
                                  "pool_vs_balance", "importance") if k in v}
        out.append(("persona:" + v["name"], body))
    for sex in SEX_LEVELS:
        for age in GRID_AGES:
            out.append((f"{sex}:{age}:undisclosed", grid_body(sex, age)))
            for e in EDU_LEVELS:
                out.append((f"{sex}:{age}:edu={e}", grid_body(sex, age, edu=e)))
            for r in RACE_LEVELS:
                out.append((f"{sex}:{age}:race={r}", grid_body(sex, age, race=r)))
            for e in EDU_LEVELS:
                for r in RACE_LEVELS:
                    out.append((f"{sex}:{age}:edu={e}:race={r}", grid_body(sex, age, edu=e, race=r)))
    for sex in SEX_LEVELS:
        for age in GRID_AGES:
            out.append((f"samesex:{sex}:{age}:undisclosed", grid_body(sex, age, same_sex=True)))
            for e in EDU_LEVELS:
                out.append((f"samesex:{sex}:{age}:edu={e}", grid_body(sex, age, edu=e, same_sex=True)))
    seen: set[str] = set()
    uniq = []
    for name, body in out:
        key = json.dumps(body, sort_keys=True, separators=(",", ":"))
        if key in seen:
            continue
        seen.add(key)
        uniq.append((name, body))
    return uniq


def pool_where(body: dict) -> str:
    """The sought pool's SQL mask (the validation suite's own mirror of the
    cube mask); every search sharing it shares one set of cell sums."""
    from atlas.pipeline.build.validate import _spec_to_sql
    return _spec_to_sql(body["seeking"], body["self"])[0]


# ---------------------------------------------------------------------------
# the replicate sums, per pool
# ---------------------------------------------------------------------------

def cell_replicate_sums(con, where: str, metro_levels: list[str],
                        cache_dir: Path | None = CACHE) -> tuple[np.ndarray, np.ndarray]:
    """S0[m, a, e, r] — the masked pool's estimate per (metro, partner age,
    education, race) cell — and S[m, a, e, r, k] for the 80 replicates,
    from the contribution table (gq <> 2, a_eff allocation, as the
    validation suite sums them). Cached by the mask's hash."""
    key = hashlib.sha1(where.encode()).hexdigest()[:16]
    path = (cache_dir / f"cells_{key}.npz") if cache_dir is not None else None
    if path is not None and path.exists():
        z = np.load(path)
        return z["S0"], z["S"]
    reps = ", ".join(f"sum(pwgtp{i} * a_eff) AS r{i}" for i in range(1, N_REP + 1))
    q = con.execute(
        f"SELECT cbsa, agep, edu4, race8, sum(pwgtp * a_eff) AS s0, {reps} FROM contrib "
        f"WHERE gq <> 2 AND ({where}) GROUP BY 1, 2, 3, 4").fetchnumpy()
    M = len(metro_levels)
    S0 = np.zeros((M, 53, 4, 8), np.float32)
    S = np.zeros((M, 53, 4, 8, N_REP), np.float32)
    midx = {c: i for i, c in enumerate(metro_levels)}
    cbsa = [str(c) for c in np.asarray(q["cbsa"]).tolist()]
    keep = np.array([c in midx for c in cbsa])
    assert keep.all(), f"{(~keep).sum()} contribution rows outside the build's metros"
    m = np.array([midx[c] for c in cbsa])
    a = np.asarray(q["agep"]).astype(int) - 18
    e = np.array([EDU_LEVELS.index(str(x)) for x in np.asarray(q["edu4"]).tolist()])
    r = np.array([RACE_LEVELS.index(str(x)) for x in np.asarray(q["race8"]).tolist()])
    assert ((a >= 0) & (a < 53)).all()
    S0[m, a, e, r] = np.asarray(q["s0"], dtype=np.float64)
    for i in range(1, N_REP + 1):
        S[m, a, e, r, i - 1] = np.asarray(q[f"r{i}"], dtype=np.float64)
    if path is not None:
        cache_dir.mkdir(parents=True, exist_ok=True)
        np.savez_compressed(path, S0=S0, S=S)
    return S0, S


# ---------------------------------------------------------------------------
# one search
# ---------------------------------------------------------------------------

def wobble_of(order: np.ndarray, top: int = TOP) -> tuple[float, bool]:
    """`order[j]` is the published position of the city at replicate
    position j. Returns (the mean rank move over the cities in either
    top-`top`, whether the old >= 8-of-10 overlap holds)."""
    n = len(order)
    rank_rep = np.empty(n, dtype=np.int64)
    rank_rep[order] = np.arange(n)
    cities = set(range(top)) | set(order[:top].tolist())
    moves = [abs(int(rank_rep[c]) - c) for c in cities]
    hit = len(set(order[:top].tolist()) & set(range(top))) >= OVERLAP_OLD
    return float(np.mean(moves)), hit


def _hash(a: np.ndarray, decimals: int) -> str:
    return hashlib.sha256(np.ascontiguousarray(np.round(a, decimals)).tobytes()).hexdigest()[:24]


def search_record(build, req, res: dict, S0: np.ndarray, S: np.ndarray,
                  noise_scale: float = 1.0) -> dict:
    """The wobble and the diagnostics of one search on one kernel, from the
    pool's cell replicate sums. `noise_scale` scales every replicate's
    deviation from the published estimate (the enlarged-noise control)."""
    ranked = [r["cbsa"] for r in res["ranked"]]
    n = len(ranked)
    if n < MIN_RANKED:
        return {"skipped": f"only {n} ranked"}
    M = len(build.metro_levels)
    same_sex = req.seeking.sex == req.self_sex
    age_vec, Wk = seeker_weights(build.kernel, req.self_sex, req.self_age,
                                 req.self_edu, req.self_race, same_sex=same_sex)
    full = (age_vec[:, :, None, None] * Wk[:, None, :, :]).reshape(M, -1)      # (M, 1696)
    S0f = S0.reshape(M, -1)
    Sf = S.reshape(M, -1, N_REP)
    W0 = np.einsum("mc,mc->m", full, S0f.astype(np.float64))
    Wr = np.empty((M, N_REP))
    for m in range(M):
        Wr[m] = Sf[m].astype(np.float64).T @ full[m]
    P0 = S0f.sum(axis=1, dtype=np.float64)
    Pr = Sf.sum(axis=1, dtype=np.float64)                                        # (M, 80)
    nat0 = W0.sum() / max(P0.sum(), 1e-9)
    nat_r = Wr.sum(axis=0) / np.maximum(Pr.sum(axis=0), 1e-9)
    ridx = np.array([build.metro_levels.index(c) for c in ranked])
    est0 = P0[ridx]
    est_r = Pr[ridx]                                                             # (n, 80)
    match0 = 100.0 * (W0[ridx] / np.maximum(est0, 1e-9)) / nat0
    match_r = 100.0 * (Wr[ridx] / np.maximum(est_r, 1e-9)) / nat_r[None, :]
    if noise_scale != 1.0:
        est_r = est0[:, None] + noise_scale * (est_r - est0[:, None])
        match_r = match0[:, None] + noise_scale * (match_r - match0[:, None])
    wts = res["weights"]
    wobbles = np.empty(N_REP)
    hits = 0
    for k in range(N_REP):
        score_r = score_vector(build, ridx, est_r[:, k], match_r[:, k], wts)
        order = np.argsort(-score_r, kind="stable")
        wobbles[k], hit = wobble_of(order)
        hits += int(hit)
    sd = np.sqrt(4.0 / N_REP * ((match_r - match0[:, None]) ** 2).sum(axis=1))
    served = np.array([r["match"]["value"] if r["match"].get("value") is not None else np.nan
                       for r in res["ranked"]], float)
    with np.errstate(invalid="ignore", divide="ignore"):
        rel = np.nanmax(np.abs(match0 - served) / np.abs(served))
    by_cbsa = np.argsort(np.array(ranked))
    return {"n_ranked": n, "same_sex": bool(same_sex),
            "wobble": round(float(wobbles.mean()), 6),
            "wobble_p90_over_replicates": round(float(np.percentile(wobbles, 90)), 4),
            "overlap_share_old_rule": hits / N_REP,
            "match_index_replicate_sd_median": round(float(np.median(sd)), 3),
            "match_index_replicate_sd_p90": round(float(np.percentile(sd, 90)), 3),
            "score_gap_rank10_to_rank11": round(float(res["ranked"][9]["score"] - res["ranked"][10]["score"]), 3),
            "served_index_max_rel_diff": (round(float(rel), 8) if np.isfinite(rel) else None),
            "index_hash": _hash(match0[by_cbsa], 6),
            "replicate_hash": _hash(np.concatenate([match_r[by_cbsa].ravel(), est_r[by_cbsa].ravel()]), 4)}


# ---------------------------------------------------------------------------
# a whole kernel
# ---------------------------------------------------------------------------

def gate_record(build, con, name: str, noise_scale: float = 1.0,
                searches: list[tuple[str, dict]] | None = None,
                cache_dir: Path | None = CACHE, verbose: bool = False) -> dict:
    """Every test search's record on this build's kernel."""
    t0 = time.time()
    searches = searches if searches is not None else test_searches()
    groups: dict[str, list[tuple[str, dict]]] = {}
    for n, body in searches:
        groups.setdefault(pool_where(body), []).append((n, body))
    km = build.kernel.meta or {}
    ss = build.kernel.same_sex
    out = {"name": name, "build": build.manifest["data_version"],
           "model_version": engine.MODEL_VERSION, "noise_scale": noise_scale,
           "kernel": {"version": km.get("version"), "fitting_sample": km.get("fitting_sample"),
                      "age_cohorts": km.get("age_cohorts"), "edu_by_sex": km.get("edu_by_sex"),
                      "interaction": km.get("interaction"),
                      "same_sex_components": list(ss.components) if ss else [],
                      "same_sex_interaction": (bool(getattr(ss, "interaction", False)) if ss else None)},
           "rule": {"wobble": "mean rank move of the cities in the top 10 of either the published "
                              "or the replicate ranking, averaged over the 80 replicates",
                    "verdict": f"fail if total wobble over the touched searches exceeds "
                               f"{1 + TOLERANCE:.2f} x the reference's; all searches when nothing is touched",
                    "min_ranked": MIN_RANKED},
           "n_searches": len(searches), "n_pool_groups": len(groups), "searches": {}}
    done = 0
    for where, members in groups.items():
        S0, S = cell_replicate_sums(con, where, build.metro_levels, cache_dir)
        for n, body in members:
            req = engine.parse_request(body)
            res = engine.rank(build, req)
            rec = search_record(build, req, res, S0, S, noise_scale)
            rec["pool_group"] = hashlib.sha1(where.encode()).hexdigest()[:16]
            out["searches"][n] = rec
            done += 1
        if verbose:
            print(f"  {done}/{len(searches)} searches ({time.time() - t0:.0f}s)", flush=True)
    live = [r for r in out["searches"].values() if "skipped" not in r]
    personas = [r for n, r in out["searches"].items() if n.startswith("persona:") and "skipped" not in r]
    out["totals"] = {"searches_scored": len(live), "searches_skipped": len(searches) - len(live),
                     "wobble_sum": round(float(sum(r["wobble"] for r in live)), 6),
                     "wobble_median": round(float(np.median([r["wobble"] for r in live])), 4),
                     "wobble_max": round(float(max(r["wobble"] for r in live)), 4),
                     "old_rule_min_share_personas": min(r["overlap_share_old_rule"] for r in personas),
                     "old_rule_min_share_all": min(r["overlap_share_old_rule"] for r in live),
                     "seconds": round(time.time() - t0, 1)}
    return out


def verdict(cand: dict, ref: dict, tolerance: float = TOLERANCE) -> dict:
    """The gate's reading of `cand` against `ref`."""
    names = [n for n, r in ref["searches"].items()
             if n in cand["searches"] and "skipped" not in r and "skipped" not in cand["searches"][n]]
    touched = [n for n in names
               if cand["searches"][n]["index_hash"] != ref["searches"][n]["index_hash"]
               or cand["searches"][n]["replicate_hash"] != ref["searches"][n]["replicate_hash"]]
    basis = touched if touched else names
    c = float(sum(cand["searches"][n]["wobble"] for n in basis))
    r = float(sum(ref["searches"][n]["wobble"] for n in basis))
    ratio = (c / r) if r > 0 else (1.0 if c == 0 else float("inf"))
    c_all = float(sum(cand["searches"][n]["wobble"] for n in names))
    r_all = float(sum(ref["searches"][n]["wobble"] for n in names))
    rose = sorted((n for n in names
                   if cand["searches"][n]["wobble"] > (1 + RISE_FLAG) * ref["searches"][n]["wobble"]),
                  key=lambda n: -(cand["searches"][n]["wobble"] / max(ref["searches"][n]["wobble"], 1e-12)))
    personas = [n for n in names if n.startswith("persona:")]
    old_min = min(cand["searches"][n]["overlap_share_old_rule"] for n in personas) if personas else None
    return {"candidate": cand["name"], "reference_build": ref["build"], "candidate_build": cand["build"],
            "searches_compared": len(names), "searches_touched": len(touched),
            "basis": "touched searches" if touched else "all searches (nothing touched)",
            "wobble_candidate": round(c, 6), "wobble_reference": round(r, 6),
            "ratio": round(ratio, 6), "tolerance": tolerance,
            "pass": bool(ratio <= 1.0 + tolerance),
            "ratio_over_all_searches": round(c_all / r_all, 6) if r_all > 0 else None,
            "searches_wobble_rose_more_than_25pct": [
                {"search": n, "reference": ref["searches"][n]["wobble"], "candidate": cand["searches"][n]["wobble"]}
                for n in rose],
            "old_rule": {"min_share_personas": old_min,
                         "pass_at_0_80": (bool(old_min >= 0.80) if old_min is not None else None),
                         "reading": "soft (ADR 0011): the >= 8-of-10 overlap in >= 80% of replicates, "
                                    "every persona"},
            "touched": touched}


def load_reference(path: Path = REFERENCE) -> dict:
    assert path.exists(), f"the stability reference is missing: {path} (ADR 0011)"
    return json.loads(path.read_text())


def _write(path: Path, obj: dict) -> None:
    P3C.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(obj, indent=1, default=lambda o: o.item() if hasattr(o, "item") else str(o)) + "\n")


def _load(build_dir: str, kernel_dir: str | None):
    from atlas.model.loader import _load_kernel
    build = engine.load_build(build_dir, allow_model_mismatch=True)
    if kernel_dir:
        build = replace(build, kernel=_load_kernel(Path(kernel_dir), build.metro_levels))
    return build


def main(argv: list[str]) -> int:
    from atlas.pipeline.build.pool import open_pool
    cmd, build_dir = argv[0], argv[1]
    opt = {argv[i]: argv[i + 1] for i in range(2, len(argv) - 1, 2) if argv[i].startswith("--")}
    build = _load(build_dir, opt.get("--kernel"))
    con = open_pool()
    con.execute("SET enable_progress_bar=false")
    try:
        if cmd == "reference":
            rec = gate_record(build, con, "reference", verbose=True)
            rec["role"] = ("THE REFERENCE (ADR 0011): moved only by Nathan's decision recorded in an ADR")
            _write(REFERENCE, rec)
            print(json.dumps(rec["totals"], indent=1))
        elif cmd == "check":
            name = opt.get("--name", "candidate")
            rec = gate_record(build, con, name, float(opt.get("--noise", "1.0")), verbose=True)
            ref = load_reference(Path(opt["--reference"])) if "--reference" in opt else load_reference()
            v = verdict(rec, ref)
            rec["verdict"] = v
            _write(P3C / f"gate_{name}.json", rec)
            print(json.dumps({k: v[k] for k in v if k != "touched"}, indent=1))
            return 0 if v["pass"] else 1
        elif cmd == "controls":
            ref = load_reference()
            ident = gate_record(build, con, "control_identity", verbose=True)
            ident["verdict"] = verdict(ident, ref)
            noise = gate_record(build, con, "control_noise_x1.5", noise_scale=1.5, verbose=True)
            noise["verdict"] = verdict(noise, ref)
            out = {"reference_build": ref["build"],
                   "identity": {"ratio": ident["verdict"]["ratio"], "pass": ident["verdict"]["pass"],
                                "searches_touched": ident["verdict"]["searches_touched"],
                                "reads_exactly_1": bool(ident["verdict"]["ratio"] == 1.0),
                                "control_passes": bool(ident["verdict"]["ratio"] == 1.0 and ident["verdict"]["pass"])},
                   "enlarged_noise": {"scale": 1.5, "ratio": noise["verdict"]["ratio"],
                                      "pass": noise["verdict"]["pass"],
                                      "searches_touched": noise["verdict"]["searches_touched"],
                                      "control_passes": bool(not noise["verdict"]["pass"])},
                   "records": {"identity": ident, "enlarged_noise": noise}}
            out["both_controls_pass"] = bool(out["identity"]["control_passes"]
                                             and out["enlarged_noise"]["control_passes"])
            _write(P3C / "gate_controls.json", out)
            print(json.dumps({k: v for k, v in out.items() if k != "records"}, indent=1))
            return 0 if out["both_controls_pass"] else 1
        else:
            print(__doc__)
            return 2
    finally:
        con.close()
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
