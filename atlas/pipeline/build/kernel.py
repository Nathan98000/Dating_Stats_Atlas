"""The assortative kernel (Phase 3, m3.0.0): who pairs with whom, as odds
multipliers relative to random pairing given availability.

    w(seeker, partner) = exp( f_age(age_c - age_s ; sex_s)
                            + f_edu(edu_s, edu_c)
                            + f_race(race_s, race_c ; sex_s) )

Estimated on the national couple table (pairing.py, opposite-sex couples
with both members 18-70) by iterative proportional fitting of a log-linear
model with an AVAILABILITY OFFSET: for every seeker type s = (sex, age,
edu4, race8) the model's partner distribution is

    P(c | s) = A(c) * w(s, c) / sum_c' A(c') * w(s, c')

where A is the national single adult population (18-70, never or
previously married, institutional GQ excluded) of the sought sex by age x
edu4 x race8. Dividing through by availability is what lets the kernel,
applied to a metro's OWN composition, reproduce local outcomes instead of
re-describing national demography. IPF matches three margins exactly —
the age-gap distribution per seeker sex, the 4x4 education pairing table
(pooled over sex) and the 8x8 race pairing table per seeker sex — and is
the maximum-likelihood fit of that model. Each component is reported in
the gauge "availability-weighted mean multiplier 1 on its own margin", so
a race entry reads as the odds of that pairing relative to random pairing
given who is available; the per-seeker constant log_norm makes the full
kernel average exactly 1 over the national single adult population.

Age term: the raw per-gap IPF estimate is replaced by a kernel-smoothed
one (Gaussian in the gap, Nadaraya-Watson on observed / expected-without-
the-age-term at the raw solution, bandwidth chosen per sex by leave-one-
gap-out Poisson deviance — not by eye); the education and race terms are
then refitted around the fixed smoothed age term, so their margins match
exactly given it. Margins with no observed couples floor at exp(FLOOR).

Metro dimension (item 3): the SHAPE is national; each metro carries one
dial per component, theta_k(m), a power on that component's log
multipliers (theta = 1 is the national kernel, theta > 1 more assortative
than the nation given local availability). Dials are fitted by maximum
likelihood on the metro's own couples against the metro's own single
population, their precision comes from the observed information rescaled
to the replicate-measured effective couple count (the marginals table's
80-replicate MOEs — no new data), and they are shrunk by empirical Bayes
(DerSimonian-Laird tau^2) toward the precision-weighted mean dial across
metros — the metro-average of the national kernel, which sits a little
below 1 because a kernel fitted against NATIONAL availability over-
predicts own-group pairing in the typical metro; shrinking toward exactly
1 would pull every metro toward that bias (measured, recorded). A
component earns a dial only where the split-half leave-one-metro-out test
says the shrunk dial predicts held-out couples better than the national
kernel, in total and in more than half the metros.

Outputs go to results/phase3/ (the report reads those files) and the
shipped artifact to data/kernel.json + data/kernel.npz, copied into the
build by cube.py.
"""
from __future__ import annotations

import json
import sys
import time
from concurrent.futures import ProcessPoolExecutor
from pathlib import Path

import numpy as np
import pandas as pd

from atlas.model.preferences import EDU_LEVELS, RACE_LEVELS, SEX_LEVELS
from atlas.pipeline.build import pairing
from atlas.pipeline.build.pool import open_pool
from atlas.pipeline.fetch import DATA, RESULTS

P3 = RESULTS / "phase3"
KERNEL_JSON = DATA / "kernel.json"
KERNEL_NPZ = DATA / "kernel.npz"
KERNEL_VERSION = "kernel_v1"

N_SEX, N_AGE, N_EDU, N_RACE = 2, 53, 4, 8
N_S = N_SEX * N_AGE * N_EDU * N_RACE      # 3,392 seeker types
N_C = N_AGE * N_EDU * N_RACE              # 1,696 partner cells
GAP0 = N_AGE - 1                          # gap index of 0 (gaps -52..52)
N_GAP = 2 * GAP0 + 1
FLOOR = float(np.log(1e-4))
COMPONENTS = ("age", "edu", "race")
BANDWIDTHS = (0.25, 0.35, 0.5, 0.75, 1.0, 1.5, 2.0, 3.0, 5.0)
THETA_BOUNDS = (0.0, 3.0)
IPF_TOL = 1e-6
IPF_MAX_ITER = 200
SEED_SPLIT = 2026


# ---------------------------------------------------------------------------
# indices shared by every fit
# ---------------------------------------------------------------------------

class Design:
    """Flattened seeker (sex, age, edu, race) x partner (age, edu, race)
    index arrays and the margin keys IPF sums over."""

    def __init__(self) -> None:
        S = np.indices((N_SEX, N_AGE, N_EDU, N_RACE)).reshape(4, -1)
        C = np.indices((N_AGE, N_EDU, N_RACE)).reshape(3, -1)
        self.sig_s, self.a_s, self.e_s, self.r_s = (x.astype(np.int64) for x in S)
        self.a_c, self.e_c, self.r_c = (x.astype(np.int64) for x in C)
        self.gap = (self.a_c[None, :] - self.a_s[:, None]) + GAP0          # (S, C)
        self.key_age = (self.sig_s[:, None] * N_GAP + self.gap).ravel()
        self.key_edu = (self.e_s[:, None] * N_EDU + self.e_c[None, :]).ravel()
        self.key_race = (self.sig_s[:, None] * N_RACE * N_RACE
                         + self.r_s[:, None] * N_RACE + self.r_c[None, :]).ravel()
        self.n_key = {"age": N_SEX * N_GAP, "edu": N_EDU * N_EDU,
                      "race": N_SEX * N_RACE * N_RACE}

    def gather(self, f: dict) -> np.ndarray:
        """log w(s, c) for every seeker type and partner cell."""
        return (f["age"][self.sig_s[:, None], self.gap]
                + f["edu"][self.e_s[:, None], self.e_c[None, :]]
                + f["race"][self.sig_s[:, None], self.r_s[:, None], self.r_c[None, :]])

    def gather_one(self, comp: str, f_comp: np.ndarray) -> np.ndarray:
        if comp == "age":
            return f_comp[self.sig_s[:, None], self.gap]
        if comp == "edu":
            return f_comp[self.e_s[:, None], self.e_c[None, :]]
        return f_comp[self.sig_s[:, None], self.r_s[:, None], self.r_c[None, :]]

    def margins(self, arr: np.ndarray) -> dict[str, np.ndarray]:
        flat = arr.ravel()
        return {"age": np.bincount(self.key_age, flat, self.n_key["age"]),
                "edu": np.bincount(self.key_edu, flat, self.n_key["edu"]),
                "race": np.bincount(self.key_race, flat, self.n_key["race"])}


_DESIGN: Design | None = None


def design() -> Design:
    global _DESIGN
    if _DESIGN is None:
        _DESIGN = Design()
    return _DESIGN


def zero_f() -> dict[str, np.ndarray]:
    return {"age": np.zeros((N_SEX, N_GAP)), "edu": np.zeros((N_EDU, N_EDU)),
            "race": np.zeros((N_SEX, N_RACE, N_RACE))}


def f_shape(comp: str) -> tuple:
    return {"age": (N_SEX, N_GAP), "edu": (N_EDU, N_EDU),
            "race": (N_SEX, N_RACE, N_RACE)}[comp]


# ---------------------------------------------------------------------------
# data
# ---------------------------------------------------------------------------

def table_to_dense(df: pd.DataFrame, col: str = "w") -> np.ndarray:
    """A couple table (national or one metro) -> (N_S, N_C) array."""
    s = (np.array([SEX_LEVELS.index(x) for x in df["sex_s"]]) * N_AGE * N_EDU * N_RACE
         + (df["age_s"].to_numpy(int) - 18) * N_EDU * N_RACE
         + df["edu_s"].map(EDU_LEVELS.index).to_numpy(int) * N_RACE
         + df["race_s"].map(RACE_LEVELS.index).to_numpy(int))
    c = ((df["age_c"].to_numpy(int) - 18) * N_EDU * N_RACE
         + df["edu_c"].map(EDU_LEVELS.index).to_numpy(int) * N_RACE
         + df["race_c"].map(RACE_LEVELS.index).to_numpy(int))
    out = np.zeros((N_S, N_C))
    np.add.at(out, (s, c), df[col].to_numpy(float))
    return out


def table_to_sparse(df: pd.DataFrame, col: str = "w") -> tuple[np.ndarray, np.ndarray, np.ndarray]:
    s = (np.array([SEX_LEVELS.index(x) for x in df["sex_s"]]) * N_AGE * N_EDU * N_RACE
         + (df["age_s"].to_numpy(int) - 18) * N_EDU * N_RACE
         + df["edu_s"].map(EDU_LEVELS.index).to_numpy(int) * N_RACE
         + df["race_s"].map(RACE_LEVELS.index).to_numpy(int))
    c = ((df["age_c"].to_numpy(int) - 18) * N_EDU * N_RACE
         + df["edu_c"].map(EDU_LEVELS.index).to_numpy(int) * N_RACE
         + df["race_c"].map(RACE_LEVELS.index).to_numpy(int))
    return s.astype(np.int64), c.astype(np.int64), df[col].to_numpy(float)


SINGLES_SQL = """
SELECT {dims} sex, agep, edu4, race8, sum(pwgtp * a_eff) AS w
FROM contrib
WHERE agep BETWEEN 18 AND 70 AND gq <> 2 AND marital3 IN ('never', 'formerly')
  AND edu4 IS NOT NULL
GROUP BY ALL
"""


def load_singles(con, metro_levels: list[str] | None = None) -> tuple[np.ndarray, np.ndarray | None]:
    """National single adult population A[sex, age, edu, race] and, when
    metro_levels is given, the per-metro version (n_metros, ...)."""
    nat = con.execute(SINGLES_SQL.format(dims="")).df()
    A = np.zeros((N_SEX, N_AGE, N_EDU, N_RACE))
    np.add.at(A, (nat["sex"].to_numpy(int) - 1, nat["agep"].to_numpy(int) - 18,
                  nat["edu4"].map(EDU_LEVELS.index).to_numpy(int),
                  nat["race8"].map(RACE_LEVELS.index).to_numpy(int)),
              nat["w"].to_numpy(float))
    if metro_levels is None:
        return A, None
    met = con.execute(SINGLES_SQL.format(dims="cbsa,")).df()
    midx = {c: i for i, c in enumerate(metro_levels)}
    met = met[met["cbsa"].isin(midx)]
    Am = np.zeros((len(metro_levels), N_SEX, N_AGE, N_EDU, N_RACE))
    np.add.at(Am, (met["cbsa"].map(midx).to_numpy(int), met["sex"].to_numpy(int) - 1,
                   met["agep"].to_numpy(int) - 18,
                   met["edu4"].map(EDU_LEVELS.index).to_numpy(int),
                   met["race8"].map(RACE_LEVELS.index).to_numpy(int)),
              met["w"].to_numpy(float))
    return A, Am


def log_avail_by_seeker(A: np.ndarray, d: Design) -> np.ndarray:
    """log A(c) of the OPPOSITE sex laid out per seeker type: (N_S, N_C)."""
    A_opp = A[1 - d.sig_s].reshape(N_S, N_C)
    with np.errstate(divide="ignore"):
        return np.log(A_opp)


# ---------------------------------------------------------------------------
# the fit
# ---------------------------------------------------------------------------

def _mu(logK: np.ndarray, logA: np.ndarray, N_s: np.ndarray) -> np.ndarray:
    """Model couple counts: rows sum to N_s (the seeker margin is exact)."""
    lm = logK + logA
    m = lm.max(axis=1, keepdims=True)
    m[~np.isfinite(m)] = 0.0
    mu = np.exp(lm - m)
    Z = mu.sum(axis=1)
    with np.errstate(invalid="ignore", divide="ignore"):
        scale = np.where(Z > 0, N_s / np.maximum(Z, 1e-300), 0.0)
    mu *= scale[:, None]
    return mu


def _raw_update(f_flat: np.ndarray, T: np.ndarray, M: np.ndarray) -> tuple[np.ndarray, float]:
    ok = (T > 0) & (M > 0)
    upd = np.zeros_like(f_flat)
    upd[ok] = np.log(T[ok] / M[ok])
    new = f_flat + upd
    new[T <= 0] = FLOOR
    return new, (float(np.abs(upd[ok]).max()) if ok.any() else 0.0)


def gauss_kernel(h: float) -> np.ndarray:
    g = np.arange(N_GAP)
    if h <= 0:
        return np.eye(N_GAP)
    K = np.exp(-0.5 * ((g[:, None] - g[None, :]) / h) ** 2)
    return K


def _smooth_age(f_age: np.ndarray, T: np.ndarray, M: np.ndarray,
                h: tuple[float, float]) -> tuple[np.ndarray, float]:
    """Nadaraya-Watson on observed / expected-without-the-age-term."""
    new = np.empty_like(f_age)
    change = 0.0
    for sig in range(N_SEX):
        Mt = M[sig] * np.exp(-f_age[sig])
        K = gauss_kernel(h[sig])
        num = K @ T[sig]
        den = K @ Mt
        f = np.full(N_GAP, FLOOR)
        ok = (num > 0) & (den > 0)
        f[ok] = np.log(num[ok] / den[ok])
        f = np.maximum(f, FLOOR)
        moved = np.isfinite(f_age[sig]) & (T[sig] > 0)
        if moved.any():
            change = max(change, float(np.abs(f[moved] - f_age[sig][moved]).max()))
        new[sig] = f
    return new, change


def fit_kernel(C: np.ndarray, A: np.ndarray, *, smooth_h: tuple[float, float] | None = None,
               fixed: dict[str, np.ndarray] | None = None, init: dict | None = None,
               skip: tuple[str, ...] = (), tol: float = IPF_TOL,
               max_iter: int = IPF_MAX_ITER) -> dict:
    """IPF of the separable kernel. `skip` names components held at zero
    (the sensitivity refits); `fixed` pins a component to given values.
    Returns f (log multipliers, raw gauge), fitted mu, margins and the
    convergence record."""
    d = design()
    N_s = C.sum(axis=1)
    T = d.margins(C)
    logA = log_avail_by_seeker(A, d)
    f = {k: v.copy() for k, v in (init or zero_f()).items()}
    for k in skip:
        f[k] = np.zeros(f_shape(k))
    for k, v in (fixed or {}).items():
        f[k] = v.copy()
    active = [k for k in COMPONENTS if k not in skip and k not in (fixed or {})]
    history = []
    for it in range(max_iter):
        worst = 0.0
        for comp in active:
            mu = _mu(d.gather(f), logA, N_s)
            M = d.margins(mu)[comp]
            if comp == "age" and smooth_h is not None:
                new, ch = _smooth_age(f["age"], T["age"].reshape(N_SEX, N_GAP),
                                      M.reshape(N_SEX, N_GAP), smooth_h)
                f["age"] = new
            else:
                new, ch = _raw_update(f[comp].ravel(), T[comp], M)
                f[comp] = new.reshape(f_shape(comp))
            worst = max(worst, ch)
        history.append(worst)
        if worst < tol:
            break
    mu = _mu(d.gather(f), logA, N_s)
    return {"f": f, "mu": mu, "T": T, "M": d.margins(mu), "N_s": N_s,
            "iterations": len(history), "converged": bool(history and history[-1] < tol),
            "final_change": history[-1] if history else 0.0}


def choose_bandwidth(T_age: np.ndarray, M_age: np.ndarray, f_age: np.ndarray) -> dict:
    """Leave-one-gap-out Poisson deviance over BANDWIDTHS, per sex, on the
    converged raw fit's observed (T) and expected-without-age-term (M e^-f)
    gap margins. Smallest deviance wins; ties go to the smaller h."""
    out = {"candidates": list(BANDWIDTHS), "deviance": {}, "chosen": []}
    for sig, name in enumerate(SEX_LEVELS):
        T = T_age[sig]
        Mt = M_age[sig] * np.exp(-f_age[sig])
        devs = []
        for h in BANDWIDTHS:
            K = gauss_kernel(h)
            np.fill_diagonal(K, 0.0)
            num = K @ T
            den = K @ Mt
            with np.errstate(invalid="ignore", divide="ignore"):
                pred = np.where(den > 0, Mt * num / den, 0.0)
            ok = (Mt > 0) & (den > 0)
            t, p = T[ok], np.maximum(pred[ok], 1e-12)
            with np.errstate(divide="ignore", invalid="ignore"):
                term = np.where(t > 0, t * np.log(t / p), 0.0) - (t - p)
            devs.append(float(2.0 * term.sum()))
        out["deviance"][name] = devs
        out["chosen"].append(float(BANDWIDTHS[int(np.argmin(devs))]))
    return out


def smooth_then_refit(C: np.ndarray, A: np.ndarray, raw: dict, h: tuple[float, float],
                      skip: tuple[str, ...] = (), tol: float = IPF_TOL,
                      max_iter: int = IPF_MAX_ITER) -> dict:
    """Smooth the converged raw age term once, fix it, refit the other
    components around it (warm-started)."""
    f_age_s, _ = _smooth_age(raw["f"]["age"], raw["T"]["age"].reshape(N_SEX, N_GAP),
                             raw["M"]["age"].reshape(N_SEX, N_GAP), h)
    return fit_kernel(C, A, fixed={"age": f_age_s}, init=raw["f"], skip=skip,
                      tol=tol, max_iter=max_iter)


def fit_national(C: np.ndarray, A: np.ndarray, *, skip: tuple[str, ...] = (),
                 bandwidth: tuple[float, float] | None = None) -> dict:
    """The two-stage national fit: raw IPF to convergence, bandwidth by
    leave-one-gap-out cross-validation (unless given), the age term
    smoothed once, then education and race refitted around it."""
    raw = fit_kernel(C, A, skip=skip)
    if "age" in skip:
        return {**raw, "raw_f_age": raw["f"]["age"], "raw_f": raw["f"], "bandwidth": None,
                "bandwidth_cv": None, "raw_iterations": raw["iterations"]}
    cv = choose_bandwidth(raw["T"]["age"].reshape(N_SEX, N_GAP),
                          raw["M"]["age"].reshape(N_SEX, N_GAP), raw["f"]["age"])
    h = tuple(bandwidth) if bandwidth is not None else tuple(cv["chosen"])
    sm = smooth_then_refit(C, A, raw, h, skip=skip)
    return {**sm, "raw_f_age": raw["f"]["age"], "raw_f": raw["f"], "bandwidth": list(h),
            "bandwidth_cv": cv, "raw_iterations": raw["iterations"]}


# ---------------------------------------------------------------------------
# gauge, normalisation, multipliers
# ---------------------------------------------------------------------------

def gauge(f: dict, A: np.ndarray, N_s: np.ndarray) -> dict:
    """Each component in the gauge 'availability-weighted mean multiplier 1
    on its own margin under random pairing'. Serving is gauge-invariant
    (log_norm absorbs the constants); this is the reporting convention
    and the convention the disclosure mixtures rely on."""
    g = {}
    # race: per seeker sex, the opposite sex's single population by race
    p_race = A.sum(axis=(1, 2))                        # (sex, race)
    p_race = p_race / p_race.sum(axis=1, keepdims=True)
    fr = f["race"].copy()
    for sig in range(N_SEX):
        p = p_race[1 - sig]
        for rs in range(N_RACE):
            mean = float((p * np.exp(fr[sig, rs])).sum())
            fr[sig, rs] -= np.log(mean) if mean > 0 else 0.0
    g["race"] = fr
    # education: pooled over sex, the single population by edu
    p_edu = A.sum(axis=(0, 1, 3))
    p_edu = p_edu / p_edu.sum()
    fe = f["edu"].copy()
    for es in range(N_EDU):
        mean = float((p_edu * np.exp(fe[es])).sum())
        fe[es] -= np.log(mean) if mean > 0 else 0.0
    g["edu"] = fe
    # age: per seeker sex, the gap distribution under random pairing —
    # seekers of the fitting sample by age crossed with the opposite
    # sex's single population by age
    Ns = N_s.reshape(N_SEX, N_AGE, N_EDU, N_RACE).sum(axis=(2, 3))     # (sex, age_s)
    A_age = A.sum(axis=(2, 3))                                         # (sex, age)
    fa = f["age"].copy()
    for sig in range(N_SEX):
        p = np.zeros(N_GAP)
        for a_s in range(N_AGE):
            for a_c in range(N_AGE):
                p[a_c - a_s + GAP0] += Ns[sig, a_s] * A_age[1 - sig, a_c]
        p = p / p.sum()
        mean = float((p * np.exp(fa[sig])).sum())
        fa[sig] -= np.log(mean) if mean > 0 else 0.0
    g["age"] = fa
    return g


def log_norm_for(f: dict, A: np.ndarray, theta: np.ndarray | None = None) -> np.ndarray:
    """Per seeker type: -log of the availability-weighted mean multiplier
    over the national single adult population, so exp(logK + log_norm)
    averages exactly 1. theta (3,) applies dial powers."""
    d = design()
    fk = f if theta is None else {k: f[k] * float(theta[i]) for i, k in enumerate(COMPONENTS)}
    logK = d.gather(fk)
    A_opp = A[1 - d.sig_s].reshape(N_S, N_C)
    tot = A_opp.sum(axis=1)
    m = logK.max(axis=1, keepdims=True)
    mean = (A_opp * np.exp(logK - m)).sum(axis=1) / np.maximum(tot, 1e-300)
    with np.errstate(divide="ignore"):
        ln = -(np.log(mean) + m[:, 0])
    ln[~np.isfinite(ln)] = 0.0
    return ln


# ---------------------------------------------------------------------------
# diagnostics: separability, face validity, age curves
# ---------------------------------------------------------------------------

def gap_band(gap_idx: np.ndarray) -> np.ndarray:
    g = gap_idx - GAP0
    return np.digitize(g, [-10, -5, -2, 1, 3, 6, 11])     # 8 bands


def separability(C: np.ndarray, mu: np.ndarray, mean_weight: float) -> dict:
    """Where the multiplicative form fails: two-way interactions the
    separable model does not carry, observed vs fitted, with G^2, the
    dissimilarity index (share of couples misallocated) and the worst
    cells. Cells thinner than 30 couples (in weight units) are not named."""
    d = design()
    bands = gap_band(d.gap)
    age_s_band = np.digitize(d.a_s + 18, [25, 35, 45, 55])              # 5 cohorts
    same_race = (d.r_s[:, None] == d.r_c[None, :]).astype(int)
    same_edu = (d.e_s[:, None] == d.e_c[None, :]).astype(int)
    tables = {
        "edu_by_seeker_sex": (d.sig_s[:, None], d.e_s[:, None], d.e_c[None, :]),
        "gap_band_by_seeker_edu": (d.sig_s[:, None], bands, d.e_s[:, None]),
        "gap_band_by_seeker_race": (d.sig_s[:, None], bands, d.r_s[:, None]),
        "race_pair_by_edu_pair": (d.sig_s[:, None], d.r_s[:, None], d.r_c[None, :],
                                  d.e_s[:, None], d.e_c[None, :]),
        "same_race_by_seeker_age_cohort": (d.sig_s[:, None], age_s_band[:, None],
                                           d.r_s[:, None], same_race),
        "same_edu_by_seeker_age_cohort": (d.sig_s[:, None], age_s_band[:, None],
                                          d.e_s[:, None], same_edu),
    }
    out = {"thin_cell_weight": 30 * mean_weight, "tables": {}}
    total = C.sum()
    for name, dims in tables.items():
        dims_b = np.broadcast_arrays(*[np.broadcast_to(x, (N_S, N_C)) for x in dims])
        sizes = [int(x.max()) + 1 for x in dims_b]
        key = np.zeros((N_S, N_C), dtype=np.int64)
        for x, sz in zip(dims_b, sizes):
            key = key * sz + x
        n = int(np.prod(sizes))
        O = np.bincount(key.ravel(), C.ravel(), n)
        E = np.bincount(key.ravel(), mu.ravel(), n)
        ok = (O > 0) & (E > 0)
        g2 = float(2.0 * (O[ok] * np.log(O[ok] / E[ok])).sum() - 2.0 * (O - E).sum())
        dissim = float(np.abs(O - E).sum() / (2.0 * total))
        thick = E >= 30 * mean_weight
        ratio = np.where(E > 0, O / np.maximum(E, 1e-300), np.nan)
        off = np.abs(np.log(np.where(thick & (O > 0), ratio, 1.0)))
        worst_idx = np.argsort(-off)[:8]
        cells = []
        for k in worst_idx:
            if off[k] <= 0:
                break
            idx = np.unravel_index(k, sizes)
            cells.append({"cell": [int(i) for i in idx], "observed": round(float(O[k]), 1),
                          "fitted": round(float(E[k]), 1),
                          "ratio": round(float(ratio[k]), 3)})
        share_off = float(O[thick & ((ratio < 0.8) | (ratio > 1.25))].sum() / total)
        out["tables"][name] = {
            "cells": n, "cells_with_couples": int((O > 0).sum()),
            "G2": round(g2, 1), "dissimilarity_index": round(dissim, 4),
            "share_of_couples_in_thick_cells_off_by_over_25pct": round(share_off, 4),
            "worst_thick_cells": cells,
            "dims": {"edu_by_seeker_sex": ["sex_s", "edu_s", "edu_c"],
                     "gap_band_by_seeker_edu": ["sex_s", "gap_band", "edu_s"],
                     "gap_band_by_seeker_race": ["sex_s", "gap_band", "race_s"],
                     "race_pair_by_edu_pair": ["sex_s", "race_s", "race_c", "edu_s", "edu_c"],
                     "same_race_by_seeker_age_cohort": ["sex_s", "age_cohort", "race_s", "same_race"],
                     "same_edu_by_seeker_age_cohort": ["sex_s", "age_cohort", "edu_s", "same_edu"]}[name]}
    out["gap_bands"] = "<-10, -10..-6, -5..-3, -2..0, 1..2, 3..5, 6..10, >10 (partner minus seeker)"
    out["age_cohorts"] = "18-24, 25-34, 35-44, 45-54, 55-70 (seeker)"
    return out


def face_validity(fg: dict, A: np.ndarray) -> dict:
    """The three cheap checks the brief requires; a failure is a finding."""
    d = design()
    out: dict = {}
    # 1. a 30-year-old's age weight (availability-adjusted partner age
    #    distribution) peaks near their own age
    peaks = {}
    for sig, name in enumerate(SEX_LEVELS):
        a_s = 30 - 18
        A_age = A[1 - sig].sum(axis=(1, 2))
        gaps = np.arange(N_AGE) - a_s + GAP0
        wt = np.exp(fg["age"][sig][gaps])                # pure multiplier by partner age
        peak_mult = int(np.argmax(wt)) + 18
        peak_dist = int(np.argmax(wt * A_age)) + 18
        peaks[name] = {"multiplier_peak_age": peak_mult, "distribution_peak_age": peak_dist,
                       "within_3_years": abs(peak_mult - 30) <= 3}
    out["age_peak_at_30"] = peaks
    out["age_pass"] = all(p["within_3_years"] for p in peaks.values())
    # 2. education diagonal-dominant
    fe = fg["edu"]
    out["edu_diagonal_dominant_rows"] = [bool(fe[e, e] == fe[e].max()) for e in range(N_EDU)]
    out["edu_pass"] = all(out["edu_diagonal_dominant_rows"])
    # 3. race diagonal exceeds every off-diagonal, every group, both sexes
    rows = {}
    for sig, name in enumerate(SEX_LEVELS):
        fr = fg["race"][sig]
        rows[name] = {RACE_LEVELS[r]: bool(fr[r, r] > np.delete(fr[r], r).max())
                      for r in range(N_RACE)}
    out["race_diagonal_exceeds_offdiagonal"] = rows
    out["race_pass"] = all(all(v.values()) for v in rows.values())
    out["pass"] = out["age_pass"] and out["edu_pass"] and out["race_pass"]
    return out


def age_curves(C: np.ndarray, mu: np.ndarray, seeker_ages=(25, 35, 50)) -> pd.DataFrame:
    """Raw vs fitted partner-age distribution for seekers of exactly
    those ages, per sex (the report's smoothing check)."""
    d = design()
    rows = []
    Cs = C.reshape(N_SEX, N_AGE, N_EDU, N_RACE, N_AGE, N_EDU, N_RACE)
    Ms = mu.reshape(N_SEX, N_AGE, N_EDU, N_RACE, N_AGE, N_EDU, N_RACE)
    for sig, name in enumerate(SEX_LEVELS):
        for a in seeker_ages:
            raw = Cs[sig, a - 18].sum(axis=(0, 1, 3, 4))
            fit = Ms[sig, a - 18].sum(axis=(0, 1, 3, 4))
            tot = raw.sum()
            for j in range(N_AGE):
                rows.append({"sex_s": name, "age_s": a, "age_c": j + 18,
                             "raw_share": raw[j] / tot if tot else np.nan,
                             "fitted_share": fit[j] / tot if tot else np.nan,
                             "raw_weight": raw[j]})
    return pd.DataFrame(rows)


def multiplier_tables(fg: dict) -> dict:
    return {
        "edu": {EDU_LEVELS[i]: {EDU_LEVELS[j]: round(float(np.exp(fg["edu"][i, j])), 4)
                                for j in range(N_EDU)} for i in range(N_EDU)},
        "race": {SEX_LEVELS[s]: {RACE_LEVELS[i]: {RACE_LEVELS[j]: round(float(np.exp(fg["race"][s, i, j])), 4)
                                                 for j in range(N_RACE)}
                                 for i in range(N_RACE)} for s in range(N_SEX)},
        "age": {SEX_LEVELS[s]: {str(g - GAP0): round(float(np.exp(fg["age"][s, g])), 4)
                                for g in range(N_GAP)} for s in range(N_SEX)},
    }


# ---------------------------------------------------------------------------
# per-metro dials
# ---------------------------------------------------------------------------

class MetroCouples:
    """One metro's couples at the kernel grain (sparse) plus the per-seeker
    (N_S-length) totals and the compact seeker list the dial fit runs on."""

    def __init__(self, s: np.ndarray, c: np.ndarray, w: np.ndarray) -> None:
        self.s, self.c, self.w = s, c, w
        self.W = float(w.sum())
        self.N_s = np.bincount(s, w, N_S)
        self.present = np.nonzero(self.N_s)[0]
        self.pos = {int(v): i for i, v in enumerate(self.present)}
        self.row_pos = np.array([self.pos[int(v)] for v in s]) if len(s) else np.zeros(0, int)


def metro_from_table(df: pd.DataFrame) -> MetroCouples:
    s, c, w = table_to_sparse(df)
    return MetroCouples(s, c, w)


def _dial_terms(f: dict, mc: MetroCouples, A_m: np.ndarray) -> dict:
    """Precompute the (present seekers x cells) component matrices, the
    per-row component values and the metro availability per present
    seeker."""
    d = design()
    P = mc.present
    F = {"age": f["age"][d.sig_s[P][:, None], d.gap[P]],
         "edu": f["edu"][d.e_s[P][:, None], d.e_c[None, :]],
         "race": f["race"][d.sig_s[P][:, None], d.r_s[P][:, None], d.r_c[None, :]]}
    rowF = {k: F[k][mc.row_pos, mc.c] for k in COMPONENTS}
    with np.errstate(divide="ignore"):
        logA = np.log(A_m[1 - d.sig_s[P]].reshape(len(P), N_C))
    return {"F": F, "rowF": rowF, "logA": logA, "N": mc.N_s[P], "w": mc.w}


def dial_loglik_grad_hess(theta: np.ndarray, terms: dict) -> tuple[float, np.ndarray, np.ndarray]:
    F, rowF, logA, N, w = terms["F"], terms["rowF"], terms["logA"], terms["N"], terms["w"]
    logK = sum(theta[i] * F[k] for i, k in enumerate(COMPONENTS)) + logA
    m = logK.max(axis=1, keepdims=True)
    m[~np.isfinite(m)] = 0.0
    P = np.exp(logK - m)
    Z = P.sum(axis=1)
    P /= np.maximum(Z, 1e-300)[:, None]
    ll = float(sum(theta[i] * (w * rowF[k]).sum() for i, k in enumerate(COMPONENTS))
               - (N * (np.log(np.maximum(Z, 1e-300)) + m[:, 0])).sum())
    Ef = np.array([(P * F[k]).sum(axis=1) for k in COMPONENTS])            # (3, nP)
    grad = np.array([(w * rowF[k]).sum() - (N * Ef[i]).sum()
                     for i, k in enumerate(COMPONENTS)])
    H = np.zeros((3, 3))
    for i, ki in enumerate(COMPONENTS):
        for j, kj in enumerate(COMPONENTS):
            if j < i:
                H[i, j] = H[j, i]
                continue
            Eij = (P * F[ki] * F[kj]).sum(axis=1)
            H[i, j] = -(N * (Eij - Ef[i] * Ef[j])).sum()
    return ll, grad, H


def fit_dials(f: dict, mc: MetroCouples, A_m: np.ndarray, comps: tuple[str, ...] = COMPONENTS,
              max_iter: int = 40) -> dict:
    """Maximum-likelihood dials (a power per component) for one metro;
    components not in `comps` stay at 1. Damped Newton, boxed to
    THETA_BOUNDS. Returns theta, the observed information (weight units)
    and the log-likelihood at the optimum."""
    terms = _dial_terms(f, mc, A_m)
    theta = np.ones(3)
    free = np.array([k in comps for k in COMPONENTS])
    ll, g, H = dial_loglik_grad_hess(theta, terms)
    for _ in range(max_iter):
        Hf = H[np.ix_(free, free)]
        gf = g[free]
        try:
            step = np.linalg.solve(Hf - 1e-9 * np.eye(int(free.sum())), -gf)
        except np.linalg.LinAlgError:
            step = -gf / np.maximum(np.abs(np.diag(Hf)), 1e-9)
        step = np.clip(step, -0.5, 0.5)
        lam = 1.0
        while lam > 1e-3:
            cand = theta.copy()
            cand[free] = np.clip(theta[free] + lam * step, *THETA_BOUNDS)
            ll2, g2, H2 = dial_loglik_grad_hess(cand, terms)
            if ll2 >= ll - 1e-9:
                break
            lam *= 0.5
        moved = float(np.abs(cand - theta).max())
        theta, ll, g, H = cand, ll2, g2, H2
        if moved < 1e-6:
            break
    return {"theta": theta, "info": -H, "loglik": ll, "W": mc.W}


def loglik_at(theta: np.ndarray, f: dict, mc: MetroCouples, A_m: np.ndarray) -> float:
    if len(mc.w) == 0:
        return 0.0
    ll, _, _ = dial_loglik_grad_hess(theta, _dial_terms(f, mc, A_m))
    return ll


def shrink(theta_hat: np.ndarray, se2: np.ndarray) -> dict:
    """Empirical Bayes toward the metro-average dial: DerSimonian-Laird
    tau^2 around the precision-weighted mean mu, prior share
    B = se2 / (se2 + tau^2), theta_tilde = mu + (theta_hat - mu)(1 - B).
    A metro without a usable estimate sits at mu."""
    ok = np.isfinite(theta_hat) & np.isfinite(se2) & (se2 > 0)
    th, v = theta_hat[ok], se2[ok]
    wgt = 1.0 / v
    mean = float((wgt * th).sum() / wgt.sum())
    Q = float((wgt * (th - mean) ** 2).sum())
    k = int(ok.sum())
    tau2 = max(0.0, (Q - (k - 1)) / (wgt.sum() - (wgt ** 2).sum() / wgt.sum()))
    B = np.where(ok, se2 / (se2 + tau2) if tau2 > 0 else 1.0, 1.0)
    tilde = np.where(ok, mean + (theta_hat - mean) * (1.0 - B), mean)
    return {"tau2": tau2, "tau": float(np.sqrt(tau2)), "prior_share": B,
            "theta_tilde": tilde, "precision_weighted_mean": mean, "Q": Q, "k": k}


def shrink_one(theta_hat: float, se2: float, sh: dict) -> tuple[float, float]:
    """One metro's shrunk dial and prior share under another set's
    (mu, tau^2) — the leave-one-out use."""
    mu, tau2 = sh["precision_weighted_mean"], sh["tau2"]
    if not (np.isfinite(theta_hat) and np.isfinite(se2) and se2 > 0):
        return mu, 1.0
    B = se2 / (se2 + tau2) if tau2 > 0 else 1.0
    return mu + (theta_hat - mu) * (1.0 - B), B


def effective_counts(marg: pd.DataFrame) -> pd.DataFrame:
    """Replicate-measured effective couple-side counts per metro and
    component from the homophily shares: n_eff = p(1-p) / Var_rep(p)."""
    m = marg[marg["sex_s"] == "all"].set_index("cbsa")
    out = pd.DataFrame(index=m.index)
    for comp in COMPONENTS:
        p = m[f"share_{comp}"].to_numpy(float)
        var = (m[f"moe_{comp}"].to_numpy(float) / 1.645) ** 2
        with np.errstate(divide="ignore", invalid="ignore"):
            n_eff = np.where(var > 0, p * (1 - p) / var, np.nan)
        # never more precise than the allocated couple-sides themselves
        out[f"n_eff_{comp}"] = np.minimum(n_eff, m["n_alloc"].to_numpy(float))
    out["n_alloc"] = m["n_alloc"]
    out["n_kish"] = m["n_kish"]
    out["W"] = m["den"]
    return out


def dial_se2(fit: dict, n_eff: dict[str, float]) -> np.ndarray:
    """Variance of theta_hat: inverse observed information after rescaling
    each component's weight mass to its replicate-measured effective
    count (the design effect enters through the marginals' MOEs)."""
    scale = np.array([np.sqrt(max(n_eff[k], 1e-9) / max(fit["W"], 1e-9)) for k in COMPONENTS])
    I = fit["info"] * scale[:, None] * scale[None, :]
    try:
        cov = np.linalg.inv(I + 1e-12 * np.eye(3))
        se2 = np.diag(cov)
    except np.linalg.LinAlgError:
        se2 = 1.0 / np.maximum(np.diag(I), 1e-12)
    se2 = np.where(np.isfinite(se2) & (se2 > 0), se2, np.inf)
    return se2


# ---------------------------------------------------------------------------
# composition predictions (Pew) and the served-quantity math shared with
# the validation
# ---------------------------------------------------------------------------

def formation_propensity(N_s: np.ndarray, A: np.ndarray) -> np.ndarray:
    """National union-formation rate by seeker type: recent-couple seekers
    over singles of that type (a national quantity, so a metro's
    prediction never uses its own couples through this term)."""
    with np.errstate(divide="ignore", invalid="ignore"):
        pi = np.where(A.ravel() > 0, N_s / np.maximum(A.ravel(), 1e-300), 0.0)
    return pi


def predict_outgroup(f: dict, theta: np.ndarray, A_m: np.ndarray, pi: np.ndarray) -> dict:
    """Predicted share of new unions in a metro that cross race8 lines:
    seekers are the metro's singles weighted by the national formation
    propensity; partners are drawn from the metro's own singles through
    the (dialled) kernel. Also the random-pairing expectation."""
    d = design()
    fk = {k: f[k] * float(theta[i]) for i, k in enumerate(COMPONENTS)}
    logK = d.gather(fk)
    A_opp = A_m[1 - d.sig_s].reshape(N_S, N_C)
    m = logK.max(axis=1, keepdims=True)
    m[~np.isfinite(m)] = 0.0
    P = A_opp * np.exp(logK - m)
    Z = P.sum(axis=1)
    out_mask = (d.r_s[:, None] != d.r_c[None, :])
    with np.errstate(invalid="ignore", divide="ignore"):
        p_out = np.where(Z > 0, (P * out_mask).sum(axis=1) / np.maximum(Z, 1e-300), np.nan)
        rand = np.where(A_opp.sum(1) > 0, (A_opp * out_mask).sum(1) / np.maximum(A_opp.sum(1), 1e-300), np.nan)
    seekers = A_m.ravel() * pi
    ok = np.isfinite(p_out) & (seekers > 0)
    tot = seekers[ok].sum()
    return {"predicted": float((seekers[ok] * p_out[ok]).sum() / tot) if tot > 0 else np.nan,
            "random_pairing": float((seekers[ok] * rand[ok]).sum() / tot) if tot > 0 else np.nan}


def observed_outgroup(mc: MetroCouples) -> float:
    d = design()
    if mc.W <= 0:
        return np.nan
    out = d.r_s[mc.s] != d.r_c[mc.c]
    return float(mc.w[out].sum() / mc.W)


# ---------------------------------------------------------------------------
# artifact
# ---------------------------------------------------------------------------

def write_artifact(fg: dict, A: np.ndarray, metro_levels: list[str], dials: np.ndarray,
                   dial_components: list[str], meta: dict, out_dir: Path = DATA) -> dict:
    """data/kernel.json (metadata + small tables) and data/kernel.npz (the
    per-metro normalisers). cube.py copies both into the build. `out_dir`
    other than data/ writes a CANDIDATE artifact (the Phase 3b half-life
    sweep loads those into a build in memory without shipping them)."""
    out_dir.mkdir(parents=True, exist_ok=True)
    log_norm = np.stack([log_norm_for(fg, A, dials[i]) for i in range(len(metro_levels))])
    log_norm = log_norm.reshape(len(metro_levels), N_SEX, N_AGE, N_EDU, N_RACE)
    np.savez_compressed(out_dir / KERNEL_NPZ.name,
                        f_age=fg["age"], f_edu=fg["edu"], f_race=fg["race"],
                        dials=dials, log_norm=log_norm.astype(np.float32),
                        avail_national=A, metro_levels=np.array(metro_levels))
    payload = {
        "version": KERNEL_VERSION,
        "form": "w = exp(theta_age f_age(gap; sex_s) + theta_edu f_edu(edu_s, edu_c) "
                "+ theta_race f_race(race_s, race_c; sex_s) + log_norm(metro, seeker))",
        "gauge": "each component: availability-weighted mean multiplier 1 on its own "
                 "margin under random pairing; log_norm makes the full kernel average "
                 "exactly 1 over the national single adult population per seeker type",
        "sex_levels": SEX_LEVELS, "age_levels": list(range(18, 71)),
        "edu_levels": EDU_LEVELS, "race_levels": RACE_LEVELS,
        "gap_offset": GAP0, "floor_log": FLOOR,
        "dial_components": dial_components,
        "components": list(COMPONENTS),
        "f_age": fg["age"].round(6).tolist(), "f_edu": fg["edu"].round(6).tolist(),
        "f_race": fg["race"].round(6).tolist(),
        "dials": {c: [round(float(x), 6) for x in dials[i]] for i, c in enumerate(metro_levels)},
        "npz": "kernel.npz: f_age, f_edu, f_race, dials (metro x component), "
               "log_norm (metro x sex x age x edu x race, float32), avail_national",
        **meta,
    }
    (out_dir / KERNEL_JSON.name).write_text(json.dumps(payload, indent=1) + "\n")
    return payload


# ---------------------------------------------------------------------------
# the full run
# ---------------------------------------------------------------------------

def _json(o):
    if isinstance(o, (np.floating, np.integer)):
        return o.item()
    if isinstance(o, np.ndarray):
        return o.tolist()
    return str(o)


def load_metro_tables(sample: str) -> tuple[dict[str, MetroCouples], dict[str, tuple[MetroCouples, MetroCouples]]]:
    df = pd.read_parquet(DATA / f"couple_table_metro_{sample}.parquet")
    df["cbsa"] = df["cbsa"].astype(str)
    full, halves = {}, {}
    for cbsa, g in df.groupby("cbsa", sort=False):
        full[cbsa] = metro_from_table(g)
        h0 = g[g["fold"] == 0]
        h1 = g[g["fold"] == 1]
        halves[cbsa] = (metro_from_table(h0), metro_from_table(h1))
    return full, halves


# state shared with forked workers
_W: dict = {}


def _init_worker(state: dict) -> None:
    _W.update(state)


def _lomo_one(cbsa: str) -> dict:
    """Leave metro `cbsa` out: refit the national kernel without it
    (warm-started), fit its dials on its own couples, shrink them with the
    other metros' tau^2, and record (a) the split-half held-out
    log-likelihoods per component and (b) the Pew-style out-group
    predictions under national-only, raw-dial and shrunk-dial kernels."""
    C, A, f_full = _W["C"], _W["A"], _W["f_full"]
    i = _W["midx"][cbsa]
    mc = _W["full"][cbsa]
    h0, h1 = _W["halves"][cbsa]
    A_m = _W["A_metro"][i]
    C_minus = C.copy()
    np.add.at(C_minus, (mc.s, mc.c), -mc.w)
    C_minus[C_minus < 0] = 0.0
    A_minus = np.maximum(A - A_m, 0.0)
    raw = fit_kernel(C_minus, A_minus, init=f_full, tol=1e-4, max_iter=25)
    fit = smooth_then_refit(C_minus, A_minus, raw, tuple(_W["bandwidth"]),
                            tol=1e-4, max_iter=25)
    fit["iterations"] = raw["iterations"] + fit["iterations"]
    f_m = gauge(fit["f"], A_minus, fit["N_s"])
    pi = formation_propensity(fit["N_s"], A_minus)
    n_eff = _W["n_eff"].get(cbsa, {k: np.nan for k in COMPONENTS})
    # dials on all of the metro's couples
    d_all = fit_dials(f_m, mc, A_m)
    se2 = dial_se2(d_all, n_eff)
    # mu and tau^2 from the other metros' full-sample dials (approximation
    # noted: those dials were fitted against the full national kernel)
    others = np.array([j for j in range(len(_W["metro_levels"])) if j != i])
    shs = [shrink(_W["theta_hat_all"][others, k], _W["se2_all"][others, k]) for k in range(3)]
    tilde = np.ones(3)
    B = np.ones(3)
    for k in range(3):
        tilde[k], B[k] = shrink_one(d_all["theta"][k], se2[k], shs[k])
    # split-half test per component: dial from half 0, likelihood on half 1
    # (and the mirror), against the national kernel
    split = {}
    for k_i, comp in enumerate(COMPONENTS):
        rec = {"national": 0.0, "raw": 0.0, "shrunk": 0.0, "sides": 0.0}
        for fit_half, eval_half in ((h0, h1), (h1, h0)):
            if fit_half.W <= 0 or eval_half.W <= 0:
                continue
            dh = fit_dials(f_m, fit_half, A_m, comps=(comp,))
            se2h = dial_se2(dh, {c: n_eff[c] / 2 for c in COMPONENTS})
            th_raw = np.ones(3); th_raw[k_i] = dh["theta"][k_i]
            th_shr = np.ones(3); th_shr[k_i], _ = shrink_one(dh["theta"][k_i], se2h[k_i], shs[k_i])
            rec["national"] += loglik_at(np.ones(3), f_m, eval_half, A_m)
            rec["raw"] += loglik_at(th_raw, f_m, eval_half, A_m)
            rec["shrunk"] += loglik_at(th_shr, f_m, eval_half, A_m)
            rec["sides"] += eval_half.W
        split[comp] = rec
    pred_nat = predict_outgroup(f_m, np.ones(3), A_m, pi)
    pred_raw = predict_outgroup(f_m, d_all["theta"], A_m, pi)["predicted"]
    pred_shr = predict_outgroup(f_m, tilde, A_m, pi)["predicted"]
    return {"cbsa": cbsa, "iterations": fit["iterations"],
            "theta_hat": d_all["theta"].tolist(), "se2": se2.tolist(),
            "theta_tilde": tilde.tolist(), "prior_share": B.tolist(),
            "shrink_centre": [sh["precision_weighted_mean"] for sh in shs],
            "split_half": split,
            "pew_pred": {"national_only": pred_nat["predicted"],
                         "random_pairing": pred_nat["random_pairing"],
                         "raw_dial": pred_raw, "shrunk_dial": pred_shr,
                         "observed_fitting_sample": observed_outgroup(mc)}}


def run_lomo(C: np.ndarray, A: np.ndarray, A_metro: np.ndarray, metro_levels: list[str],
             f_full: dict, bandwidth: list[float], full: dict, halves: dict,
             n_eff: dict, theta_hat_all: np.ndarray, se2_all: np.ndarray,
             workers: int = 6) -> list[dict]:
    state = {"C": C, "A": A, "A_metro": A_metro, "metro_levels": metro_levels,
             "midx": {c: i for i, c in enumerate(metro_levels)}, "f_full": f_full,
             "bandwidth": bandwidth, "full": full, "halves": halves, "n_eff": n_eff,
             "theta_hat_all": theta_hat_all, "se2_all": se2_all}
    import multiprocessing as mp
    ctx = mp.get_context("fork")
    with ProcessPoolExecutor(max_workers=workers, mp_context=ctx,
                             initializer=_init_worker, initargs=(state,)) as ex:
        return list(ex.map(_lomo_one, metro_levels, chunksize=4))


def pew_table(metro_levels: list[str]) -> pd.DataFrame:
    pew = pd.read_csv(RESULTS / "reference" / "pew_intermarriage_2015.csv",
                      comment="#", dtype={"msa_code": str})
    pew = pew[pew["msa_code"] != "1"].copy()
    pew["pew_total"] = pd.to_numeric(pew["total"], errors="coerce") / 100.0
    return pew[pew["msa_code"].isin(set(metro_levels))][["msa_code", "metro_name", "pew_total"]]


def pew_national() -> float:
    pew = pd.read_csv(RESULTS / "reference" / "pew_intermarriage_2015.csv",
                      comment="#", dtype={"msa_code": str})
    return float(pew.loc[pew["msa_code"] == "1", "total"].iloc[0]) / 100.0


def error_summary(err: np.ndarray) -> dict:
    e = np.abs(err[np.isfinite(err)]) * 100
    return {"n": int(len(e)), "median_abs_pts": round(float(np.median(e)), 2),
            "p90_abs_pts": round(float(np.percentile(e, 90)), 2),
            "max_abs_pts": round(float(e.max()), 2),
            "mean_signed_pts": round(float(np.mean(err[np.isfinite(err)]) * 100), 2)}


def recent_supports_fit(S: dict, metro_levels: list[str]) -> dict:
    """The stated stability criterion for the default sample (counts and
    margins, never feel)."""
    d = pd.read_csv(P3 / "dials_recent.csv", dtype={"cbsa": str})
    nat = pd.read_parquet(DATA / "couple_table_national_recent.parquet")
    own = nat[nat["race_s"] == nat["race_c"]].groupby(["sex_s", "race_s"])
    own_kish = (own["w"].sum() ** 2 / own["sumw2"].sum())
    out = {"ipf_converged": bool(S["ipf"]["converged"]),
           "face_validity": bool(S["face_validity"]["pass"]),
           "edu_cells_min_effective": S["margins"]["edu_4x4"]["n_kish_min"],
           "own_group_race_cells_min_effective": round(float(own_kish.min()), 1),
           "own_group_race_cells_below_100": int((own_kish < 100).sum()),
           "metros_below_100_kish_sides": int((d["couple_sides_kish"] < 100).sum())}
    out["pass"] = bool(out["ipf_converged"] and out["face_validity"]
                       and out["edu_cells_min_effective"] >= 100
                       and out["own_group_race_cells_below_100"] == 0
                       and out["metros_below_100_kish_sides"] == 0)
    return out


def candidate_artifact(sample: str, out_dir: Path, report: dict | None = None,
                       provisional: bool = False) -> dict:
    """Refit the national kernel on `sample` (the bandwidth the Phase 3 run
    cross-validated for it), read its shrunk dials from
    results/phase3/dials_<sample>.csv and write the artifact to `out_dir`.
    The half-life sweep writes candidates under results/phase3b/; shipping
    writes data/. Returns the report entry it used."""
    report = report if report is not None else json.loads((P3 / "kernel_report.json").read_text())
    con = open_pool()
    metro_levels = sorted(pd.read_csv(RESULTS / "metros.csv", dtype={"cbsa": str})["cbsa"])
    A, _ = load_singles(con)
    con.close()
    nat = pd.read_parquet(DATA / f"couple_table_national_{sample}.parquet")
    C = table_to_dense(nat)
    fit = fit_national(C, A, bandwidth=tuple(report["samples"][sample]["bandwidth"]))
    fits = {sample: {"fit": fit, "fg": gauge(fit["f"], A, fit["N_s"])}}
    _ship(report, fits, metro_levels, A, sample, provisional=provisional, out_dir=out_dir)
    return report


def ship_sample(sample: str, chosen_by: str | None = None) -> None:
    """Refit the national kernel on `sample`, read its dials, write the
    final artifact to data/ and record the decision in kernel_report.json
    — the same code path as the end of `fit`, runnable on its own.
    `chosen_by` records a selection rule other than the Phase 3 default
    (Phase 3b: the rank-stability gate, shortest half-life first)."""
    report = json.loads((P3 / "kernel_report.json").read_text())
    metro_levels = sorted(pd.read_csv(RESULTS / "metros.csv", dtype={"cbsa": str})["cbsa"])
    choice = sample_choice(report, list(report["samples"]), metro_levels, forced=sample)
    if chosen_by:
        choice["chosen_by"] = chosen_by
    report["sample_choice"] = choice
    candidate_artifact(sample, DATA, report=report)
    (P3 / "kernel_report.json").write_text(json.dumps(report, indent=1, default=_json) + "\n")


def sample_choice(report: dict, samples: list[str], metro_levels: list[str],
                  forced: str | None = None) -> dict:
    """The stated decision: recent unions ship unless their counts and
    margins cannot support a stable fit; then the time-weighted sample
    with the smallest out-of-sample Pew error; the stock never ships."""
    scores = {n: report["samples"][n]["pew"]["corrected_errors"]["shrunk_dial"]["median_abs_pts"]
              for n in samples if "pew" in report["samples"][n]}
    pew_best = min(scores, key=lambda n: scores[n])
    best = "recent" if "recent" in samples else pew_best
    stable = None
    if "recent" in samples:
        stable = recent_supports_fit(report["samples"]["recent"], metro_levels)
        if not stable["pass"]:
            decays = [n for n in samples if n.startswith("decay_h") and n in scores]
            best = min(decays, key=lambda n: scores[n]) if decays else pew_best
    if forced is not None:
        best = forced
    return {
        "rule": "recent unions ship unless their counts and margins cannot support a "
                "stable fit (IPF converged, face validity, every edu cell and every "
                "own-group race cell >= 100 effective sides, no metro below 100 Kish "
                "sides); then the time-weighted sample with the smallest out-of-sample "
                "Pew error. The stock is never shipped (a 1985 marriage voting as loudly "
                "as a 2024 one).",
        "recent_stability": stable,
        "scores_median_abs_pts": scores, "pew_best_sample": pew_best,
        "pew_confound": "Pew's newlyweds are 2011-2015 unions; samples that weight "
                        "older unions more move toward Pew's period as well as toward "
                        "its pattern, so the Pew criterion cannot separate 'fits current "
                        "pairing better' from 'sits closer to the test period'",
        "shipped": best}


def _ship(report: dict, fits: dict, metro_levels: list[str], A: np.ndarray, best: str,
          provisional: bool, out_dir: Path = DATA) -> None:
    ship = report["samples"][best]
    earned = [k for k in COMPONENTS if ship["split_half_dial_test"][k]["earns_dial"]]
    dial_df = pd.read_csv(P3 / f"dials_{best}.csv", dtype={"cbsa": str}).set_index("cbsa").loc[metro_levels]
    dials = np.ones((len(metro_levels), 3))
    for j, k in enumerate(COMPONENTS):
        if k in earned:
            dials[:, j] = dial_df[f"theta_tilde_{k}"].to_numpy(float)
    fg = fits[best]["fg"]
    meta = {"fitting_sample": best, "fitting_sample_spec": ship["spec"],
            "couple_sides_weighted": ship["couple_sides_weighted"], "n_alloc": ship["n_alloc"],
            "bandwidth_years": ship["bandwidth"],
            "dials_tau": {k: ship["dials"][k]["tau"] for k in COMPONENTS},
            "dials_centre": {k: ship["dials"][k]["precision_weighted_mean_theta"] for k in COMPONENTS},
            "provisional": provisional,
            "generated_at": time.strftime("%Y-%m-%dT%H:%M:%S%z")}
    write_artifact(fg, A, metro_levels, dials, earned, meta, out_dir=out_dir)
    if out_dir == DATA:
        report["shipped"] = {"sample": best, "dial_components": earned, "provisional": provisional,
                             "artifact": [str(KERNEL_JSON.relative_to(DATA.parent)),
                                          str(KERNEL_NPZ.relative_to(DATA.parent))],
                             "face_validity": ship["face_validity"]}
    print(f"[{best}] artifact written to {out_dir} ({'provisional' if provisional else 'final'}); "
          f"dials: {earned}", flush=True)


def pew_comparison(lomo: list[dict], pew: pd.DataFrame, pew_nat: float, nat_ours: float,
                   metro_levels: list[str], full: dict, out_csv: Path) -> tuple[dict, dict]:
    """The out-of-sample Pew comparison for one sample's LOMO record: the
    corrected and raw error distributions for the three models plus random
    pairing and the observed rate, the paired win counts with a sign test
    (the bar), and the brief's composition check re-derived. Writes the
    per-metro table to `out_csv`."""
    by = {r["cbsa"]: r for r in lomo}
    # Pew comparison, out of sample
    pw = pew.copy()
    for col, key in (("national_only", "national_only"), ("raw_dial", "raw_dial"),
                     ("shrunk_dial", "shrunk_dial"), ("random_pairing", "random_pairing"),
                     ("observed_2020_24", "observed_fitting_sample")):
        pw[col] = [by[c]["pew_pred"][key] if c in by else np.nan for c in pw["msa_code"]]
        offset_ratio = nat_ours / pew_nat
    pew_rec = {"metros_matched": int(pw["pew_total"].notna().sum()),
               "pew_national": pew_nat, "our_national_fitting_sample": nat_ours,
               "level_offset_ratio_ours_over_pew": round(offset_ratio, 4),
               "correction": "predictions divided by the national ratio (Pew's US row vs "
                             "our national fitting-sample share) — one constant from a "
                             "row outside the metro test set; raw errors also reported",
               "raw_errors": {}, "corrected_errors": {}}
    for col in ("random_pairing", "national_only", "raw_dial", "shrunk_dial", "observed_2020_24"):
        err = pw[col].to_numpy(float) - pw["pew_total"].to_numpy(float)
        pew_rec["raw_errors"][col] = error_summary(err)
        errc = pw[col].to_numpy(float) / offset_ratio - pw["pew_total"].to_numpy(float)
        pew_rec["corrected_errors"][col] = error_summary(errc)
    pw["corrected_national_only"] = pw["national_only"] / offset_ratio
    pw["corrected_shrunk_dial"] = pw["shrunk_dial"] / offset_ratio
    pw["corrected_raw_dial"] = pw["raw_dial"] / offset_ratio
    pw.to_csv(out_csv, index=False)
    # the bar, read model against model on the SAME metros: paired
    # absolute errors, win counts and a two-sided sign test
    from scipy.stats import binomtest
    e = {m: (pw[f"corrected_{m}"] - pw["pew_total"]).abs().to_numpy(float) * 100
         for m in ("national_only", "raw_dial", "shrunk_dial")}
    okp = np.isfinite(e["shrunk_dial"]) & np.isfinite(e["raw_dial"]) & np.isfinite(e["national_only"])
    def paired(a, b):
        d = e[a][okp] - e[b][okp]
        wins = int((d < 0).sum()); losses = int((d > 0).sum())
        return {"a_better_metros": wins, "b_better_metros": losses,
                "median_paired_diff_pts": round(float(np.median(d)), 3),
                "mean_paired_diff_pts": round(float(d.mean()), 3),
                "sign_test_p": round(float(binomtest(wins, wins + losses).pvalue), 4)
                if wins + losses else None}
    pew_rec["paired"] = {"shrunk_vs_national": paired("shrunk_dial", "national_only"),
                         "shrunk_vs_raw": paired("shrunk_dial", "raw_dial"),
                         "raw_vs_national": paired("raw_dial", "national_only")}
    pew_rec["bar"] = {
        "national_only_median_abs_pts": pew_rec["corrected_errors"]["national_only"]["median_abs_pts"],
        "shrunk_beats_national_materially": bool(
            pew_rec["corrected_errors"]["shrunk_dial"]["median_abs_pts"]
            < 0.9 * pew_rec["corrected_errors"]["national_only"]["median_abs_pts"]),
        "shrunk_median_below_raw_median": bool(
            pew_rec["corrected_errors"]["shrunk_dial"]["median_abs_pts"]
            < pew_rec["corrected_errors"]["raw_dial"]["median_abs_pts"]),
        "shrunk_not_worse_than_raw_paired": bool(
            pew_rec["paired"]["shrunk_vs_raw"]["sign_test_p"] is None
            or pew_rec["paired"]["shrunk_vs_raw"]["sign_test_p"] > 0.05
            or pew_rec["paired"]["shrunk_vs_raw"]["median_paired_diff_pts"] <= 0)}
    # the brief's rough check, re-derived: composition R^2, ratio span,
    # one national multiplier on local composition
    ok = pw["pew_total"].notna() & pw["random_pairing"].notna()
    x, y = pw.loc[ok, "random_pairing"].to_numpy(), pw.loc[ok, "pew_total"].to_numpy()
    r2 = float(np.corrcoef(x, y)[0, 1] ** 2) if ok.sum() > 2 else np.nan
    obs_all = np.array([by[c]["pew_pred"]["observed_fitting_sample"] for c in metro_levels])
    rnd_all = np.array([by[c]["pew_pred"]["random_pairing"] for c in metro_levels])
    with np.errstate(invalid="ignore", divide="ignore"):
        ratio_all = obs_all / rnd_all
    rho_nat = float(nat_ours / np.nansum(rnd_all * np.array([full[c].W for c in metro_levels]))
                    * np.nansum([full[c].W for c in metro_levels]))
    one_mult = pw["random_pairing"] * rho_nat / offset_ratio
    err1 = (one_mult - pw["pew_total"]).to_numpy(float)
    jackson = pw[pw["msa_code"] == "27140"]
    comp_check = {
        "r2_pew_on_random_pairing_expectation": round(r2, 3),
        "availability_adjusted_ratio_observed_over_random": {
            "min": round(float(np.nanmin(ratio_all)), 3), "max": round(float(np.nanmax(ratio_all)), 3),
            "median": round(float(np.nanmedian(ratio_all)), 3)},
        "one_national_multiplier": {"rho": round(rho_nat, 4),
                                    **error_summary(err1),
                                    "share_off_by_over_1_5x": round(float(np.nanmean(
                                        np.maximum(one_mult / pw["pew_total"], pw["pew_total"] / one_mult) > 1.5)), 3)},
        "jackson_ms": ({"pew": float(jackson["pew_total"].iloc[0]),
                        "one_multiplier_predicted": round(float(one_mult[jackson.index[0]]), 4),
                        "national_only_corrected": round(float(jackson["corrected_national_only"].iloc[0]), 4),
                        "shrunk_corrected": round(float(jackson["corrected_shrunk_dial"].iloc[0]), 4),
                        "observed_2020_24": round(float(jackson["observed_2020_24"].iloc[0]), 4)}
                       if len(jackson) else None)}
    return pew_rec, comp_check


def main(argv: list[str]) -> None:
    """kernel.py fit [--samples recent,stock,decay_h10,...] [--workers N]"""
    P3.mkdir(parents=True, exist_ok=True)
    t_start = time.time()
    workers = 6
    samples = ["recent", "stock", "decay_h5", "decay_h10", "decay_h20", "decay_h40"]
    if "--workers" in argv:
        workers = int(argv[argv.index("--workers") + 1])
    if "--samples" in argv:
        samples = argv[argv.index("--samples") + 1].split(",")
    con = open_pool()
    con.execute("SET enable_progress_bar=false")
    metro_levels = sorted(pd.read_csv(RESULTS / "metros.csv", dtype={"cbsa": str})["cbsa"])
    A, A_metro = load_singles(con, metro_levels)
    np.save(P3 / "_avail_national.npy", A)
    np.save(P3 / "_avail_metro.npy", A_metro)
    con.close()   # the couple tables are on disk; free the database for the build
    report: dict = {"metros": len(metro_levels), "samples": {}, "workers": workers}

    # ---- the three fitting samples: counts, margins, national fits ---------
    specs = {}
    for name in samples:
        if name.startswith("decay_h"):
            specs[name] = pairing.decay_sample(float(name[len("decay_h"):]))
        else:
            specs[name] = pairing.SAMPLES[name]
    have = {p.stem.replace("couple_table_national_", "") for p in DATA.glob("couple_table_national_*.parquet")}
    missing = [n for n in samples if n not in have]
    assert not missing, f"couple tables missing for {missing}: run pairing.build_couple_tables first"
    fits = {}
    pew = pew_table(metro_levels)
    pew_nat = pew_national()
    for name in samples:
        t0 = time.time()
        nat = pd.read_parquet(DATA / f"couple_table_national_{name}.parquet")
        C = table_to_dense(nat)
        n_alloc = table_to_dense(nat, "n_alloc")
        mean_weight = float(C.sum() / n_alloc.sum())
        fit = fit_national(C, A)
        fg = gauge(fit["f"], A, fit["N_s"])
        d = design()
        # per-cell margins of the fitting sample on the three component
        # grains (effective respondent counts and replicate MOE of each
        # cell's share of its row)
        rep_cols = [f"w_r{i}" for i in range(1, 81)]
        def margin_stats(keys: list[str]) -> dict:
            g = nat.groupby(keys)
            W = g["w"].sum()
            R = g[rep_cols].sum()
            NA = g["n_alloc"].sum()
            S2 = g["sumw2"].sum()
            kish = W ** 2 / S2
            row_keys = keys[:-1]
            rowW = W.groupby(level=list(range(len(row_keys)))).transform("sum") if row_keys else W.sum()
            rowR = R.groupby(level=list(range(len(row_keys)))).transform("sum") if row_keys else R.sum()
            share = W / rowW
            rr = R.div(rowR)
            var = 0.05 * ((rr.sub(share, axis=0)) ** 2).sum(axis=1)
            rel_moe = 1.645 * np.sqrt(var) / share
            return {"cells": int(len(W)), "n_alloc_min": round(float(NA.min()), 1),
                    "n_alloc_median": round(float(NA.median()), 1),
                    "n_kish_min": round(float(kish.min()), 1),
                    "n_kish_median": round(float(kish.median()), 1),
                    "cells_below_30_effective": int((np.minimum(NA, kish) < 30).sum()),
                    "cells_below_100_effective": int((np.minimum(NA, kish) < 100).sum()),
                    "rel_moe_median": round(float(np.nanmedian(rel_moe)), 4),
                    "rel_moe_p90": round(float(np.nanpercentile(rel_moe, 90)), 4),
                    "rel_moe_max": round(float(np.nanmax(rel_moe)), 4)}
        nat["gap"] = nat["age_c"] - nat["age_s"]
        margins = {"edu_4x4": margin_stats(["edu_s", "edu_c"]),
                   "race_8x8_by_sex": margin_stats(["sex_s", "race_s", "race_c"]),
                   "age_gap_by_sex": margin_stats(["sex_s", "gap"])}
        race_cells_possible = N_SEX * N_RACE * N_RACE
        gap_cells_possible = N_SEX * N_GAP
        sep = separability(C, fit["mu"], mean_weight)
        fv = face_validity(fg, A)
        floored = {"age": int((fit["f"]["age"] <= FLOOR + 1e-9).sum()),
                   "edu": int((fit["f"]["edu"] <= FLOOR + 1e-9).sum()),
                   "race": int((fit["f"]["race"] <= FLOOR + 1e-9).sum()),
                   "race_cells": [[SEX_LEVELS[i], RACE_LEVELS[j], RACE_LEVELS[k]]
                                  for i, j, k in zip(*np.where(fit["f"]["race"] <= FLOOR + 1e-9))],
                   "age_gaps": [[SEX_LEVELS[i], int(g - GAP0)]
                                for i, g in zip(*np.where(fit["f"]["age"] <= FLOOR + 1e-9))]}
        fits[name] = {"C": C, "fit": fit, "fg": fg, "mean_weight": mean_weight}
        report["samples"][name] = {
            "spec": {"where": specs[name][0], "weight": specs[name][1]},
            "couple_sides_weighted": round(float(C.sum()), 1),
            "n_alloc": round(float(n_alloc.sum()), 1),
            "n_kish": round(float(C.sum() ** 2 / nat["sumw2"].sum()), 1),
            "mean_weight_per_side": round(mean_weight, 2),
            "cells_nonzero": int((C > 0).sum()),
            "margins": margins,
            "race_cells_empty": race_cells_possible - margins["race_8x8_by_sex"]["cells"],
            "gap_cells_empty": gap_cells_possible - margins["age_gap_by_sex"]["cells"],
            "floored_cells": floored,
            "ipf": {"raw_iterations": fit["raw_iterations"], "smoothed_iterations": fit["iterations"],
                    "converged": fit["converged"], "final_change": fit["final_change"]},
            "bandwidth": fit["bandwidth"], "bandwidth_cv": fit["bandwidth_cv"],
            "face_validity": fv,
            "separability": sep,
            "national_outgroup_share": round(float(observed_outgroup(
                MetroCouples(*table_to_sparse(nat)))), 4),
            "seconds": round(time.time() - t0, 1)}
        print(f"[{name}] fit {fit['iterations']} it, bandwidth {fit['bandwidth']}, "
              f"face {fv['pass']}, {time.time() - t0:.0f}s", flush=True)
        (P3 / f"kernel_multipliers_{name}.json").write_text(
            json.dumps(multiplier_tables(fg), indent=1) + "\n")
        age_curves(C, fit["mu"]).to_csv(P3 / f"kernel_age_curves_{name}.csv", index=False)
        pd.DataFrame({"sex_s": np.repeat(SEX_LEVELS, N_GAP), "gap": np.tile(np.arange(N_GAP) - GAP0, 2),
                      "raw_log_mult": fit["raw_f_age"].ravel(), "smoothed_log_mult": fit["f"]["age"].ravel(),
                      "gauged_log_mult": fg["age"].ravel()}).to_csv(
            P3 / f"kernel_age_term_{name}.csv", index=False)

    # ---- metro dials + LOMO for every sample (Pew out of sample) -----------
    lomo_all = {}
    for name in samples:
        t0 = time.time()
        C, fit, fg = fits[name]["C"], fits[name]["fit"], fits[name]["fg"]
        full, halves = load_metro_tables(name)
        marg = pd.read_parquet(DATA / f"couple_marginals_metro_{name}.parquet")
        marg["cbsa"] = marg["cbsa"].astype(str)
        ne = effective_counts(marg)
        n_eff = {c: {k: float(ne.loc[c, f"n_eff_{k}"]) for k in COMPONENTS} for c in ne.index}
        # full-sample dials for every metro (the shrinkage table)
        theta_hat = np.ones((len(metro_levels), 3))
        se2 = np.full((len(metro_levels), 3), np.inf)
        ll_nat = np.zeros(len(metro_levels))
        for i, cbsa in enumerate(metro_levels):
            mc = full.get(cbsa)
            if mc is None or mc.W <= 0:
                continue
            dm = fit_dials(fg, mc, A_metro[i])
            theta_hat[i] = dm["theta"]
            se2[i] = dial_se2(dm, n_eff.get(cbsa, {k: np.nan for k in COMPONENTS}))
            ll_nat[i] = dm["loglik"]
        shr = {k: shrink(theta_hat[:, j], se2[:, j]) for j, k in enumerate(COMPONENTS)}
        dial_df = pd.DataFrame({"cbsa": metro_levels})
        for j, k in enumerate(COMPONENTS):
            dial_df[f"theta_hat_{k}"] = theta_hat[:, j]
            dial_df[f"se_{k}"] = np.sqrt(se2[:, j])
            dial_df[f"theta_tilde_{k}"] = shr[k]["theta_tilde"]
            dial_df[f"prior_share_{k}"] = shr[k]["prior_share"]
            dial_df[f"n_eff_{k}"] = [n_eff.get(c, {}).get(k, np.nan) for c in metro_levels]
        dial_df["couple_sides_n_alloc"] = [ne.loc[c, "n_alloc"] if c in ne.index else np.nan
                                          for c in metro_levels]
        dial_df["couple_sides_kish"] = [ne.loc[c, "n_kish"] if c in ne.index else np.nan for c in metro_levels]
        dial_df.to_csv(P3 / f"dials_{name}.csv", index=False)
        print(f"[{name}] dials: tau " + ", ".join(f"{k}={shr[k]['tau']:.3f}" for k in COMPONENTS)
              + f" ({time.time() - t0:.0f}s); LOMO x{len(metro_levels)} ...", flush=True)
        t1 = time.time()
        lomo = run_lomo(C, A, A_metro, metro_levels, fit["raw_f"], fit["bandwidth"], full, halves,
                        n_eff, theta_hat, se2, workers=workers)
        lomo_all[name] = lomo
        by = {r["cbsa"]: r for r in lomo}
        # split-half dial test per component
        split = {}
        for k in COMPONENTS:
            nat_ll = sum(r["split_half"][k]["national"] for r in lomo)
            raw_ll = sum(r["split_half"][k]["raw"] for r in lomo)
            shr_ll = sum(r["split_half"][k]["shrunk"] for r in lomo)
            sides = sum(r["split_half"][k]["sides"] for r in lomo)
            wins = sum(1 for r in lomo if r["split_half"][k]["shrunk"] > r["split_half"][k]["national"])
            raw_wins = sum(1 for r in lomo if r["split_half"][k]["raw"] > r["split_half"][k]["national"])
            shr_over_raw = sum(1 for r in lomo if r["split_half"][k]["shrunk"] > r["split_half"][k]["raw"])
            split[k] = {"heldout_loglik_national": nat_ll, "heldout_loglik_raw_dial": raw_ll,
                        "heldout_loglik_shrunk_dial": shr_ll,
                        "gain_shrunk_minus_national_per_1000_weighted_sides": (shr_ll - nat_ll) / sides * 1000,
                        "gain_raw_minus_national_per_1000_weighted_sides": (raw_ll - nat_ll) / sides * 1000,
                        "metros_where_shrunk_beats_national": wins,
                        "metros_where_raw_beats_national": raw_wins,
                        "metros_where_shrunk_beats_raw": shr_over_raw,
                        "metros": len(lomo),
                        "rule": "earns a dial when the shrunk dial beats the national kernel on "
                                "held-out couples in total AND in more than half the metros",
                        "earns_dial": bool(shr_ll > nat_ll and wins > len(lomo) / 2)}
        pew_rec, comp_check = pew_comparison(
            lomo, pew, pew_nat, report["samples"][name]["national_outgroup_share"],
            metro_levels, full, P3 / f"pew_lomo_{name}.csv")
        report["samples"][name].update({
            "dials": {k: {"tau": round(shr[k]["tau"], 4), "tau2": shr[k]["tau2"],
                          "precision_weighted_mean_theta": round(shr[k]["precision_weighted_mean"], 4),
                          "metros_prior_share_above_0_9": int((shr[k]["prior_share"] > 0.9).sum()),
                          "prior_share_median": round(float(np.median(shr[k]["prior_share"])), 4),
                          "theta_hat_p10_p50_p90": [round(float(v), 4) for v in
                                                    np.nanpercentile(theta_hat[:, j], [10, 50, 90])],
                          "theta_hat_at_bounds": int(((theta_hat[:, j] <= THETA_BOUNDS[0] + 1e-9)
                                                      | (theta_hat[:, j] >= THETA_BOUNDS[1] - 1e-9)).sum())}
                      for j, k in enumerate(COMPONENTS)},
            "split_half_dial_test": split,
            "pew": pew_rec,
            "composition_check": comp_check,
            "lomo_seconds": round(time.time() - t1, 1),
            "lomo_iterations_median": float(np.median([r["iterations"] for r in lomo]))})
        print(f"[{name}] LOMO {time.time() - t1:.0f}s; Pew corrected median abs: "
              + ", ".join(f"{c}={pew_rec['corrected_errors'][c]['median_abs_pts']}" for c in
                          ("national_only", "raw_dial", "shrunk_dial")), flush=True)
        (P3 / f"lomo_{name}.json").write_text(json.dumps(lomo, indent=0, default=_json) + "\n")
        if name == "recent":
            # the default sample: write a PROVISIONAL artifact now so the
            # build chain can start while the other samples run; the
            # final choice below rewrites it only if another sample wins
            _ship(report, fits, metro_levels, A, "recent", provisional=True)
            (P3 / "kernel_report.json").write_text(json.dumps(report, indent=1, default=_json) + "\n")

    # ---- choose the sample (the stated rule; see sample_choice) ---------------
    report["sample_choice"] = sample_choice(report, samples, metro_levels)
    best = report["sample_choice"]["shipped"]
    # ---- the shipped kernel: dials where earned ------------------------------
    _ship(report, fits, metro_levels, A, best, provisional=False)
    report["seconds_total"] = round(time.time() - t_start, 1)
    (P3 / "kernel_report.json").write_text(json.dumps(report, indent=1, default=_json) + "\n")
    print(json.dumps({"shipped": report["shipped"], "sample_choice": report["sample_choice"],
                      "seconds": report["seconds_total"]}, indent=1, default=_json))


def pew_rerun(sample: str, workers: int = 8) -> dict:
    """Phase 3b A2: re-run the leave-one-metro-out Pew comparison (and the
    split-half dial test that rides with it) for one sample from scratch
    — the national refit, every metro's dials, the 387 LOMO refits — and
    write the record under results/phase3b/ beside the Phase 3 figures
    for the same sample, so the report can put the two side by side."""
    P3B = RESULTS / "phase3b"
    P3B.mkdir(parents=True, exist_ok=True)
    t0 = time.time()
    report = json.loads((P3 / "kernel_report.json").read_text())
    con = open_pool()
    con.execute("SET enable_progress_bar=false")
    metro_levels = sorted(pd.read_csv(RESULTS / "metros.csv", dtype={"cbsa": str})["cbsa"])
    A, A_metro = load_singles(con, metro_levels)
    con.close()
    nat = pd.read_parquet(DATA / f"couple_table_national_{sample}.parquet")
    C = table_to_dense(nat)
    fit = fit_national(C, A, bandwidth=tuple(report["samples"][sample]["bandwidth"]))
    fg = gauge(fit["f"], A, fit["N_s"])
    full, halves = load_metro_tables(sample)
    marg = pd.read_parquet(DATA / f"couple_marginals_metro_{sample}.parquet")
    marg["cbsa"] = marg["cbsa"].astype(str)
    ne = effective_counts(marg)
    n_eff = {c: {k: float(ne.loc[c, f"n_eff_{k}"]) for k in COMPONENTS} for c in ne.index}
    theta_hat = np.ones((len(metro_levels), 3))
    se2 = np.full((len(metro_levels), 3), np.inf)
    for i, cbsa in enumerate(metro_levels):
        mc = full.get(cbsa)
        if mc is None or mc.W <= 0:
            continue
        dm = fit_dials(fg, mc, A_metro[i])
        theta_hat[i] = dm["theta"]
        se2[i] = dial_se2(dm, n_eff.get(cbsa, {k: np.nan for k in COMPONENTS}))
    shr = {k: shrink(theta_hat[:, j], se2[:, j]) for j, k in enumerate(COMPONENTS)}
    old_d = pd.read_csv(P3 / f"dials_{sample}.csv", dtype={"cbsa": str}).set_index("cbsa").loc[metro_levels]
    dial_drift = {k: float(np.nanmax(np.abs(old_d[f"theta_tilde_{k}"].to_numpy(float)
                                            - shr[k]["theta_tilde"]))) for k in COMPONENTS}
    print(f"[{sample}] dials refitted: max |drift| vs Phase 3 {dial_drift}; LOMO x{len(metro_levels)} ...",
          flush=True)
    t1 = time.time()
    lomo = run_lomo(C, A, A_metro, metro_levels, fit["raw_f"], fit["bandwidth"], full, halves,
                    n_eff, theta_hat, se2, workers=workers)
    split = {}
    for k in COMPONENTS:
        nat_ll = sum(r["split_half"][k]["national"] for r in lomo)
        raw_ll = sum(r["split_half"][k]["raw"] for r in lomo)
        shr_ll = sum(r["split_half"][k]["shrunk"] for r in lomo)
        sides = sum(r["split_half"][k]["sides"] for r in lomo)
        split[k] = {"gain_shrunk_minus_national_per_1000_weighted_sides": (shr_ll - nat_ll) / sides * 1000,
                    "gain_raw_minus_national_per_1000_weighted_sides": (raw_ll - nat_ll) / sides * 1000,
                    "metros_where_shrunk_beats_national": sum(
                        1 for r in lomo if r["split_half"][k]["shrunk"] > r["split_half"][k]["national"]),
                    "metros_where_shrunk_beats_raw": sum(
                        1 for r in lomo if r["split_half"][k]["shrunk"] > r["split_half"][k]["raw"]),
                    "metros": len(lomo),
                    "earns_dial": bool(shr_ll > nat_ll and sum(
                        1 for r in lomo if r["split_half"][k]["shrunk"] > r["split_half"][k]["national"])
                        > len(lomo) / 2)}
    nat_ours = report["samples"][sample]["national_outgroup_share"]
    pew_rec, comp_check = pew_comparison(lomo, pew_table(metro_levels), pew_national(), nat_ours,
                                         metro_levels, full, P3B / f"pew_lomo_{sample}.csv")
    old = report["samples"][sample]["pew"]
    out = {"sample": sample, "spec": report["samples"][sample]["spec"],
           "national_outgroup_share": nat_ours,
           "pew": pew_rec, "composition_check": comp_check, "split_half_dial_test": split,
           "dials_tau": {k: round(shr[k]["tau"], 4) for k in COMPONENTS},
           "dials_centre": {k: round(shr[k]["precision_weighted_mean"], 4) for k in COMPONENTS},
           "dial_max_abs_drift_vs_phase3": dial_drift,
           "phase3_record": {"corrected_errors": old["corrected_errors"], "paired": old["paired"]},
           "reproduces_phase3": {
               m: pew_rec["corrected_errors"][m]["median_abs_pts"] == old["corrected_errors"][m]["median_abs_pts"]
               for m in ("national_only", "raw_dial", "shrunk_dial")},
           "m3_0_0_recent": {"corrected_errors": report["samples"]["recent"]["pew"]["corrected_errors"],
                             "paired": report["samples"]["recent"]["pew"]["paired"]},
           "workers": workers, "lomo_seconds": round(time.time() - t1, 1),
           "seconds": round(time.time() - t0, 1)}
    (P3B / f"lomo_{sample}.json").write_text(json.dumps(lomo, indent=0, default=_json) + "\n")
    (P3B / f"pew_rerun_{sample}.json").write_text(json.dumps(out, indent=1, default=_json) + "\n")
    print(json.dumps({k: out[k] for k in ("reproduces_phase3", "dial_max_abs_drift_vs_phase3",
                                          "lomo_seconds")}, indent=1)
          + "\nPew corrected median abs: "
          + ", ".join(f"{c}={pew_rec['corrected_errors'][c]['median_abs_pts']}"
                      for c in ("national_only", "raw_dial", "shrunk_dial")), flush=True)
    return out


if __name__ == "__main__":
    if sys.argv[1:2] == ["ship"]:
        ship_sample(sys.argv[2], chosen_by=(sys.argv[3] if len(sys.argv) > 3 else None))
    elif sys.argv[1:2] == ["pew"]:
        pew_rerun(sys.argv[2], workers=int(sys.argv[sys.argv.index("--workers") + 1])
                  if "--workers" in sys.argv else 8)
    else:
        main(sys.argv[1:])
