"""Phase 3b, Part B (m3.2.0): three refinements of the assortative kernel,
each fitted and tested on the shipped sample under the framework Phase 3
built — leave one metro out, split its couples in half by household,
score the held-out half — and each shipping only if it improves total
held-out likelihood and breaks neither rank stability nor latency.

  B1   a gap curve per seeker age cohort, per sex, smoothed as before with
       the bandwidth cross-validated per cohort; the partition chosen by
       split-half held-out likelihood among stated candidate partitions
  B2a  the race x education two-way term, shrunk toward no interaction by
       empirical Bayes: a Gaussian prior on the log interaction whose
       variance tau^2 is estimated from the data, so a thin cell cannot
       swing on a handful of couples; undialled (a national correction)
  B2b  a sex-specific education matrix
  B3   same-sex pairing terms fitted on the same-sex couples the Phase 3
       fit excluded, served per component where the sample supports it
       AND the held-out test says it predicts same-sex couples better
       than the opposite-sex fallback

The kernel keeps its form,

    w = exp( theta_age f_age(gap; sex, cohort) + theta_edu f_edu(edu_s, edu_c[; sex])
           + theta_race f_race(race_s, race_c; sex) + g(race_s, race_c, edu_s, edu_c; sex)
           + log_norm(metro, seeker) )

with the same IPF-with-availability-offset estimation, the same smoothing,
gauge, dials, shrinkage, split-half test and Pew comparison as kernel.py
(whose data loading, metro tables, shrinkage and Pew code are reused as
they are). The two-way term is estimated by penalised coordinate ascent:
the main effects take exact IPF steps, the interaction takes a Newton step
on the ridge-penalised Poisson objective per cell, in weight units with
the penalty scaled by the mean weight per side so tau^2 is on the scale of
one allocated couple-side. Artifact version kernel_v2 (loader.py reads v1
and v2).

    python -m atlas.pipeline.build.kernel_refine check
    python -m atlas.pipeline.build.kernel_refine fit  [--sample decay_h5]
    python -m atlas.pipeline.build.kernel_refine lomo [--workers 8]
    python -m atlas.pipeline.build.kernel_refine samesex [--workers 8]
    python -m atlas.pipeline.build.kernel_refine ship
"""
from __future__ import annotations

import json
import sys
import time
from concurrent.futures import ProcessPoolExecutor
from dataclasses import dataclass, field
from pathlib import Path

import numpy as np
import pandas as pd

from atlas.model.preferences import EDU_LEVELS, RACE_LEVELS, SEX_LEVELS
from atlas.pipeline.build import kernel as K
from atlas.pipeline.build.kernel import (COMPONENTS, FLOOR, GAP0, N_AGE, N_C, N_EDU,
                                         N_GAP, N_RACE, N_S, N_SEX, MetroCouples,
                                         gauss_kernel)
from atlas.pipeline.build.pool import open_pool
from atlas.pipeline.fetch import DATA, RESULTS

P3 = RESULTS / "phase3"
P3B = RESULTS / "phase3b"
# Phase 3c: `--dir results/phase3c` points every read and write of the fit
# store (refine_fits.json, _form_fits.npz, dials_*.csv, lomo_*.json, the
# same-sex records) at that directory; seed it with copies of the Phase 3b
# records first (results/phase3c/_seed.sh).
KERNEL_VERSION_V2 = "kernel_v2"
N_INT = N_SEX * N_RACE * N_RACE * N_EDU * N_EDU
INT_TOL = 1e-6
INT_MAX_ITER = 200


# ---------------------------------------------------------------------------
# forms
# ---------------------------------------------------------------------------

@dataclass(frozen=True)
class Form:
    """The kernel's form: cohort boundaries for the age term (lower bounds
    of every cohort after the first, so () is one cohort for all ages),
    whether the education matrix is per seeker sex, and whether the race x
    education two-way term is present."""
    age_edges: tuple[int, ...] = ()
    edu_by_sex: bool = False
    interaction: bool = False
    name: str = "baseline"

    @property
    def n_cohorts(self) -> int:
        return len(self.age_edges) + 1

    def cohort_of_age(self) -> np.ndarray:
        return np.digitize(np.arange(18, 71), np.array(self.age_edges, int)) if self.age_edges \
            else np.zeros(N_AGE, int)

    def cohort_labels(self) -> list[str]:
        lo = [18, *self.age_edges]
        hi = [*[e - 1 for e in self.age_edges], 70]
        return [f"{a}-{b}" for a, b in zip(lo, hi)]

    def describe(self) -> dict:
        return {"name": self.name, "age_edges": list(self.age_edges),
                "age_cohorts": self.cohort_labels(), "edu_by_sex": self.edu_by_sex,
                "interaction": self.interaction}


# candidate partitions for B1, chosen by split-half held-out likelihood
PARTITIONS = {
    "one": (),
    "three": (30, 45),
    "five": (25, 35, 45, 55),
    "eight": (22, 25, 28, 31, 35, 40, 50),
    "twelve": (21, 23, 25, 27, 29, 31, 34, 37, 41, 46, 53),
    # the grid was extended downward once, as the bandwidth grid was in
    # Phase 3, to show whether the held-out gain flattens: two-year
    # cohorts to 40 and every single year of age
    "seventeen": (20, 22, 24, 26, 28, 30, 32, 34, 36, 38, 40, 43, 46, 50, 55, 60),
    "single_year": tuple(range(19, 71)),
}


class Design2:
    """kernel.Design generalised to a Form: the margin keys and gathers
    for the cohort age term, the (per-sex) education term, the race term
    and the interaction."""

    def __init__(self, form: Form) -> None:
        d = K.design()
        self.form = form
        self.base = d
        self.K = form.n_cohorts
        self.cohort_of_age = form.cohort_of_age()
        self.coh_s = self.cohort_of_age[d.a_s]
        self.row_age = d.sig_s * self.K + self.coh_s                        # (S,)
        self.key_age = (self.row_age[:, None] * N_GAP + d.gap).ravel()
        self.n_age = N_SEX * self.K * N_GAP
        if form.edu_by_sex:
            self.key_edu = (d.sig_s[:, None] * N_EDU * N_EDU + d.e_s[:, None] * N_EDU
                            + d.e_c[None, :]).ravel()
            self.n_edu = N_SEX * N_EDU * N_EDU
        else:
            self.key_edu = d.key_edu
            self.n_edu = N_EDU * N_EDU
        self.key_race = d.key_race
        self.n_race = N_SEX * N_RACE * N_RACE
        self.key_int = None
        if form.interaction:
            self.key_int = ((((d.sig_s * N_RACE + d.r_s)[:, None] * N_RACE + d.r_c[None, :])
                             * N_EDU + d.e_s[:, None]) * N_EDU + d.e_c[None, :]).ravel()

    def shapes(self) -> dict:
        return {"age": (N_SEX, self.K, N_GAP),
                "edu": (N_SEX, N_EDU, N_EDU) if self.form.edu_by_sex else (N_EDU, N_EDU),
                "race": (N_SEX, N_RACE, N_RACE),
                "int": (N_SEX, N_RACE, N_RACE, N_EDU, N_EDU)}

    def zero_f(self) -> dict:
        f = {k: np.zeros(v) for k, v in self.shapes().items()}
        if not self.form.interaction:
            f.pop("int")
        return f

    def gather_one(self, comp: str, fc: np.ndarray, rows: np.ndarray | None = None) -> np.ndarray:
        """log term (seekers x cells); `rows` restricts to those seeker types."""
        d = self.base
        sig = d.sig_s if rows is None else d.sig_s[rows]
        e_s = d.e_s if rows is None else d.e_s[rows]
        r_s = d.r_s if rows is None else d.r_s[rows]
        if comp == "age":
            ra = self.row_age if rows is None else self.row_age[rows]
            gap = d.gap if rows is None else d.gap[rows]
            return np.take_along_axis(fc.reshape(N_SEX * self.K, N_GAP)[ra], gap, axis=1)
        if comp == "edu":
            if self.form.edu_by_sex:
                return fc[sig[:, None], e_s[:, None], d.e_c[None, :]]
            return fc[e_s[:, None], d.e_c[None, :]]
        if comp == "race":
            return fc[sig[:, None], r_s[:, None], d.r_c[None, :]]
        if comp == "int":
            return fc[sig[:, None], r_s[:, None], d.r_c[None, :], e_s[:, None], d.e_c[None, :]]
        raise KeyError(comp)

    def gather(self, f: dict, rows: np.ndarray | None = None) -> np.ndarray:
        out = self.gather_one("age", f["age"], rows)
        out = out + self.gather_one("edu", f["edu"], rows)
        out += self.gather_one("race", f["race"], rows)
        if f.get("int") is not None:
            out += self.gather_one("int", f["int"], rows)
        return out

    def margins(self, arr: np.ndarray) -> dict[str, np.ndarray]:
        flat = arr.ravel()
        out = {"age": np.bincount(self.key_age, flat, self.n_age),
               "edu": np.bincount(self.key_edu, flat, self.n_edu),
               "race": np.bincount(self.key_race, flat, self.n_race)}
        if self.key_int is not None:
            out["int"] = np.bincount(self.key_int, flat, N_INT)
        return out


_DESIGNS: dict[Form, Design2] = {}


def design2(form: Form) -> Design2:
    if form not in _DESIGNS:
        _DESIGNS[form] = Design2(form)
    return _DESIGNS[form]


def log_avail(A: np.ndarray, same_sex: bool, rows: np.ndarray | None = None) -> np.ndarray:
    """log A(c) of the SOUGHT sex per seeker type (N_S or len(rows), N_C)."""
    d = K.design()
    sig = d.sig_s if rows is None else d.sig_s[rows]
    A_c = A[sig if same_sex else 1 - sig].reshape(len(sig), N_C)
    with np.errstate(divide="ignore"):
        return np.log(A_c)


# ---------------------------------------------------------------------------
# the fit
# ---------------------------------------------------------------------------

def _smooth_rows(f_rows: np.ndarray, T: np.ndarray, M: np.ndarray, h: np.ndarray) -> tuple[np.ndarray, float]:
    """kernel._smooth_age for any number of (sex x cohort) rows."""
    new = np.empty_like(f_rows)
    change = 0.0
    for i in range(f_rows.shape[0]):
        Mt = M[i] * np.exp(-f_rows[i])
        Kh = gauss_kernel(float(h[i]))
        num = Kh @ T[i]
        den = Kh @ Mt
        f = np.full(N_GAP, FLOOR)
        ok = (num > 0) & (den > 0)
        f[ok] = np.log(num[ok] / den[ok])
        f = np.maximum(f, FLOOR)
        moved = np.isfinite(f_rows[i]) & (T[i] > 0)
        if moved.any():
            change = max(change, float(np.abs(f[moved] - f_rows[i][moved]).max()))
        new[i] = f
    return new, change


def choose_bandwidths(T_rows: np.ndarray, M_rows: np.ndarray, f_rows: np.ndarray) -> dict:
    """Leave-one-gap-out Poisson deviance per (sex x cohort) row over
    kernel.BANDWIDTHS; smallest deviance wins, ties to the smaller h."""
    out = {"candidates": list(K.BANDWIDTHS), "deviance": [], "chosen": []}
    for i in range(T_rows.shape[0]):
        T = T_rows[i]
        Mt = M_rows[i] * np.exp(-f_rows[i])
        devs = []
        for h in K.BANDWIDTHS:
            Kh = gauss_kernel(h)
            np.fill_diagonal(Kh, 0.0)
            num = Kh @ T
            den = Kh @ Mt
            with np.errstate(invalid="ignore", divide="ignore"):
                pred = np.where(den > 0, Mt * num / den, 0.0)
            ok = (Mt > 0) & (den > 0)
            t, p = T[ok], np.maximum(pred[ok], 1e-12)
            with np.errstate(divide="ignore", invalid="ignore"):
                term = np.where(t > 0, t * np.log(t / p), 0.0) - (t - p)
            devs.append(float(2.0 * term.sum()))
        out["deviance"].append(devs)
        out["chosen"].append(float(K.BANDWIDTHS[int(np.argmin(devs))]))
    return out


def interaction_prior(T_int: np.ndarray, M_int: np.ndarray, mean_weight: float) -> dict:
    """Empirical-Bayes tau^2 for the interaction: the raw log ratio of
    observed to separable-fitted per cell, each with sampling variance
    1/n (n = observed couple-sides in allocated units), shrunk toward ZERO
    (no interaction) — method of moments around zero, so
    tau^2 = (sum n g^2 - k) / sum n over the cells with couples."""
    ok = (T_int > 0) & (M_int > 0)
    g = np.zeros_like(T_int)
    g[ok] = np.log(T_int[ok] / M_int[ok])
    n = T_int / mean_weight
    Q = float((n[ok] * g[ok] ** 2).sum())
    k = int(ok.sum())
    tau2 = max(0.0, (Q - k) / max(float(n[ok].sum()), 1e-9))
    return {"tau2": tau2, "tau": float(np.sqrt(tau2)), "cells_with_couples": k,
            "raw_log_ratio_sd": float(np.sqrt((g[ok] ** 2).mean())) if k else 0.0,
            "Q": Q}


def fit_form(C: np.ndarray, A: np.ndarray, form: Form, *, same_sex: bool = False,
             bandwidth: list[float] | None = None, tau2: float | None = None,
             init: dict | None = None, tol: float = K.IPF_TOL, max_iter: int = K.IPF_MAX_ITER,
             mean_weight: float | None = None, skip: tuple[str, ...] = ()) -> dict:
    """The two-stage fit for any Form: raw IPF of the main effects to
    convergence, bandwidth per (sex, cohort) by leave-one-gap-out
    cross-validation (unless given), the age term smoothed once and the
    other main effects refitted around it; then, if the form carries the
    interaction, tau^2 by empirical Bayes at the separable fit (unless
    given) and penalised coordinate ascent over (edu, race, int) with the
    age term fixed. `skip` holds a main effect at zero (sensitivity)."""
    d = design2(form)
    N_s = C.sum(axis=1)
    T = d.margins(C)
    logA = log_avail(A, same_sex)
    mw = mean_weight if mean_weight is not None else 1.0
    f = {k: v.copy() for k, v in (init or d.zero_f()).items()}
    if form.interaction and f.get("int") is None:
        f["int"] = np.zeros(d.shapes()["int"])
    if not form.interaction:
        f.pop("int", None)
    for k in skip:
        f[k] = np.zeros(d.shapes()[k])
    mains = [k for k in COMPONENTS if k not in skip]

    def run_ipf(active: list[str], fixed_age: bool, with_int: bool, tau2_: float | None,
                tol_: float, max_iter_: int) -> tuple[list[float], np.ndarray]:
        history = []
        mu = None
        for _ in range(max_iter_):
            worst = 0.0
            for comp in active:
                mu = K._mu(d.gather(f), logA, N_s)
                M = d.margins(mu)[comp]
                new, ch = K._raw_update(f[comp].ravel(), T[comp], M)
                f[comp] = new.reshape(d.shapes()[comp])
                worst = max(worst, ch)
            if with_int:
                mu = K._mu(d.gather(f), logA, N_s)
                M = d.margins(mu)["int"]
                Ti = T["int"]
                lam = mw / tau2_ if tau2_ > 0 else np.inf
                g = f["int"].ravel().copy()
                if np.isfinite(lam):
                    # one Newton step on  T g - M e^g - lam g^2 / 2  per cell
                    grad = Ti - M - lam * g
                    hess = M + lam
                    step = grad / np.maximum(hess, 1e-12)
                    step = np.clip(step, -1.0, 1.0)
                    g = g + step
                    g[M <= 0] = 0.0
                    ch = float(np.abs(step[(M > 0)]).max()) if (M > 0).any() else 0.0
                else:
                    ch = 0.0
                f["int"] = g.reshape(d.shapes()["int"])
                worst = max(worst, ch)
            history.append(worst)
            if worst < tol_:
                break
        if mu is None:
            mu = K._mu(d.gather(f), logA, N_s)
        return history, mu

    # stage 1: raw IPF of the main effects (interaction at zero)
    f_int_saved = f.pop("int", None)
    hist_raw, mu = run_ipf(mains, False, False, None, tol, max_iter)
    raw_f = {k: v.copy() for k, v in f.items()}
    raw_M = d.margins(mu)
    # stage 2: bandwidth per (sex, cohort), smooth, refit around the fixed age term
    rows = N_SEX * d.K
    cv = None
    if "age" in mains:
        T_rows = T["age"].reshape(rows, N_GAP)
        M_rows = raw_M["age"].reshape(rows, N_GAP)
        if bandwidth is None:
            cv = choose_bandwidths(T_rows, M_rows, f["age"].reshape(rows, N_GAP))
            h = np.array(cv["chosen"])
        else:
            h = np.array(bandwidth, float)
            assert len(h) == rows, (len(h), rows)
        f_age_s, _ = _smooth_rows(f["age"].reshape(rows, N_GAP), T_rows, M_rows, h)
        f["age"] = f_age_s.reshape(N_SEX, d.K, N_GAP)
        hist_sm, mu = run_ipf([k for k in mains if k != "age"], True, False, None, tol, max_iter)
    else:
        h = None
        hist_sm = []
    # stage 3: the interaction, penalised, with the age term fixed
    prior = None
    hist_int: list[float] = []
    if form.interaction:
        sep_M = d.margins(mu)
        if tau2 is None:
            prior = interaction_prior(T["int"], sep_M["int"], mw)
            tau2 = prior["tau2"]
        else:
            prior = {"tau2": tau2, "given": True}
        f["int"] = f_int_saved if f_int_saved is not None else np.zeros(d.shapes()["int"])
        hist_int, mu = run_ipf([k for k in mains if k != "age"], True, True, tau2,
                               tol, INT_MAX_ITER if max_iter >= K.IPF_MAX_ITER else max_iter)
    history = hist_raw + hist_sm + hist_int
    return {"f": f, "raw_f": raw_f, "mu": mu, "T": T, "M": d.margins(mu), "N_s": N_s,
            "bandwidth": (None if h is None else [float(x) for x in h]), "bandwidth_cv": cv,
            "tau2": tau2, "interaction_prior": prior,
            "raw_iterations": len(hist_raw), "smoothed_iterations": len(hist_sm),
            "interaction_iterations": len(hist_int),
            "iterations": len(history),
            "converged": bool(history and history[-1] < tol),
            "final_change": history[-1] if history else 0.0, "form": form,
            "same_sex": same_sex}


# ---------------------------------------------------------------------------
# gauge, normalisation, likelihood
# ---------------------------------------------------------------------------

def gauge_form(f: dict, A: np.ndarray, N_s: np.ndarray, form: Form, same_sex: bool = False) -> dict:
    """kernel.gauge for a Form: each main effect in the gauge 'availability-
    weighted mean multiplier 1 on its own margin under random pairing'
    (age per sex x cohort, education per sex when sex-specific); the
    interaction is left as fitted (its scale is fixed by the zero-centred
    prior; log_norm absorbs every constant in serving)."""
    d = design2(form)
    g: dict = {}
    partner = (lambda sig: sig) if same_sex else (lambda sig: 1 - sig)
    p_race = A.sum(axis=(1, 2))
    p_race = p_race / p_race.sum(axis=1, keepdims=True)
    fr = f["race"].copy()
    for sig in range(N_SEX):
        p = p_race[partner(sig)]
        for rs in range(N_RACE):
            mean = float((p * np.exp(fr[sig, rs])).sum())
            fr[sig, rs] -= np.log(mean) if mean > 0 else 0.0
    g["race"] = fr
    fe = f["edu"].copy()
    if form.edu_by_sex:
        p_edu_sex = A.sum(axis=(1, 3))
        p_edu_sex = p_edu_sex / p_edu_sex.sum(axis=1, keepdims=True)
        for sig in range(N_SEX):
            p = p_edu_sex[partner(sig)]
            for es in range(N_EDU):
                mean = float((p * np.exp(fe[sig, es])).sum())
                fe[sig, es] -= np.log(mean) if mean > 0 else 0.0
    else:
        p_edu = A.sum(axis=(0, 1, 3))
        p_edu = p_edu / p_edu.sum()
        for es in range(N_EDU):
            mean = float((p_edu * np.exp(fe[es])).sum())
            fe[es] -= np.log(mean) if mean > 0 else 0.0
    g["edu"] = fe
    Ns = N_s.reshape(N_SEX, N_AGE, N_EDU, N_RACE).sum(axis=(2, 3))
    A_age = A.sum(axis=(2, 3))
    fa = f["age"].copy()
    for sig in range(N_SEX):
        for c in range(d.K):
            p = np.zeros(N_GAP)
            for a_s in np.where(d.cohort_of_age == c)[0]:
                for a_c in range(N_AGE):
                    p[a_c - a_s + GAP0] += Ns[sig, a_s] * A_age[partner(sig), a_c]
            if p.sum() <= 0:
                continue
            p = p / p.sum()
            mean = float((p * np.exp(fa[sig, c])).sum())
            fa[sig, c] -= np.log(mean) if mean > 0 else 0.0
    g["age"] = fa
    if f.get("int") is not None:
        g["int"] = f["int"].copy()
    return g


def scaled(f: dict, theta: np.ndarray) -> dict:
    out = {k: f[k] * float(theta[i]) for i, k in enumerate(COMPONENTS)}
    if f.get("int") is not None:
        out["int"] = f["int"]
    return out


def log_norm_form(f: dict, A: np.ndarray, form: Form, theta: np.ndarray | None = None,
                  same_sex: bool = False) -> np.ndarray:
    """Per seeker type: -log of the availability-weighted mean multiplier
    over the national single population of the sought sex."""
    d = design2(form)
    fk = f if theta is None else scaled(f, theta)
    logK = d.gather(fk)
    sig = K.design().sig_s
    A_c = A[sig if same_sex else 1 - sig].reshape(N_S, N_C)
    tot = A_c.sum(axis=1)
    m = logK.max(axis=1, keepdims=True)
    mean = (A_c * np.exp(logK - m)).sum(axis=1) / np.maximum(tot, 1e-300)
    with np.errstate(divide="ignore"):
        ln = -(np.log(mean) + m[:, 0])
    ln[~np.isfinite(ln)] = 0.0
    return ln


def _dial_terms(f: dict, mc: MetroCouples, A_m: np.ndarray, form: Form, same_sex: bool = False) -> dict:
    d = design2(form)
    P = mc.present
    F = {k: d.gather_one(k, f[k], P) for k in COMPONENTS}
    G = d.gather_one("int", f["int"], P) if f.get("int") is not None else None
    rowF = {k: F[k][mc.row_pos, mc.c] for k in COMPONENTS}
    rowG = G[mc.row_pos, mc.c] if G is not None else np.zeros(len(mc.c))
    logA = log_avail(A_m, same_sex, P)
    return {"F": F, "G": G, "rowF": rowF, "rowG": rowG, "logA": logA, "N": mc.N_s[P], "w": mc.w}


def dial_loglik_grad_hess(theta: np.ndarray, terms: dict) -> tuple[float, np.ndarray, np.ndarray]:
    F, rowF, logA, N, w = terms["F"], terms["rowF"], terms["logA"], terms["N"], terms["w"]
    logK = sum(theta[i] * F[k] for i, k in enumerate(COMPONENTS)) + logA
    if terms["G"] is not None:
        logK = logK + terms["G"]
    m = logK.max(axis=1, keepdims=True)
    m[~np.isfinite(m)] = 0.0
    P = np.exp(logK - m)
    Z = P.sum(axis=1)
    P /= np.maximum(Z, 1e-300)[:, None]
    ll = float(sum(theta[i] * (w * rowF[k]).sum() for i, k in enumerate(COMPONENTS))
               + (w * terms["rowG"]).sum()
               - (N * (np.log(np.maximum(Z, 1e-300)) + m[:, 0])).sum())
    Ef = np.array([(P * F[k]).sum(axis=1) for k in COMPONENTS])
    grad = np.array([(w * rowF[k]).sum() - (N * Ef[i]).sum() for i, k in enumerate(COMPONENTS)])
    H = np.zeros((3, 3))
    for i, ki in enumerate(COMPONENTS):
        for j, kj in enumerate(COMPONENTS):
            if j < i:
                H[i, j] = H[j, i]
                continue
            Eij = (P * F[ki] * F[kj]).sum(axis=1)
            H[i, j] = -(N * (Eij - Ef[i] * Ef[j])).sum()
    return ll, grad, H


def fit_dials(f: dict, mc: MetroCouples, A_m: np.ndarray, form: Form, comps=COMPONENTS,
              max_iter: int = 40, same_sex: bool = False) -> dict:
    terms = _dial_terms(f, mc, A_m, form, same_sex)
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
            cand[free] = np.clip(theta[free] + lam * step, *K.THETA_BOUNDS)
            ll2, g2, H2 = dial_loglik_grad_hess(cand, terms)
            if ll2 >= ll - 1e-9:
                break
            lam *= 0.5
        moved = float(np.abs(cand - theta).max())
        theta, ll, g, H = cand, ll2, g2, H2
        if moved < 1e-6:
            break
    return {"theta": theta, "info": -H, "loglik": ll, "W": mc.W}


def loglik_at(theta: np.ndarray, f: dict, mc: MetroCouples, A_m: np.ndarray, form: Form,
              same_sex: bool = False) -> float:
    if len(mc.w) == 0:
        return 0.0
    ll, _, _ = dial_loglik_grad_hess(theta, _dial_terms(f, mc, A_m, form, same_sex))
    return ll


def predict_outgroup(f: dict, theta: np.ndarray, A_m: np.ndarray, pi: np.ndarray, form: Form) -> dict:
    d = design2(form)
    logK = d.gather(scaled(f, theta))
    b = K.design()
    A_opp = A_m[1 - b.sig_s].reshape(N_S, N_C)
    m = logK.max(axis=1, keepdims=True)
    m[~np.isfinite(m)] = 0.0
    P = A_opp * np.exp(logK - m)
    Z = P.sum(axis=1)
    out_mask = (b.r_s[:, None] != b.r_c[None, :])
    with np.errstate(invalid="ignore", divide="ignore"):
        p_out = np.where(Z > 0, (P * out_mask).sum(axis=1) / np.maximum(Z, 1e-300), np.nan)
        rand = np.where(A_opp.sum(1) > 0, (A_opp * out_mask).sum(1) / np.maximum(A_opp.sum(1), 1e-300), np.nan)
    seekers = A_m.ravel() * pi
    ok = np.isfinite(p_out) & (seekers > 0)
    tot = seekers[ok].sum()
    return {"predicted": float((seekers[ok] * p_out[ok]).sum() / tot) if tot > 0 else np.nan,
            "random_pairing": float((seekers[ok] * rand[ok]).sum() / tot) if tot > 0 else np.nan}


def face_validity(fg: dict, A: np.ndarray, form: Form, same_sex: bool = False) -> dict:
    """kernel.face_validity for a Form: the 30-year-old reads the cohort
    that holds age 30."""
    d = design2(form)
    c30 = int(d.cohort_of_age[30 - 18])
    f3 = {"age": fg["age"][:, c30, :], "edu": (fg["edu"] if not form.edu_by_sex else fg["edu"][0]),
          "race": fg["race"]}
    out = K.face_validity(f3, A if not same_sex else A[[1, 0]])
    if same_sex:
        # ADR 0010 (amended, m3.3.0): the same-sex education matrix is held
        # to own level above 1 and above every level two or more away;
        # diagonal dominance is kept as a soft reading
        fe = fg["edu"] if not form.edu_by_sex else fg["edu"][0]
        out["edu_diagonal_dominant_rows_soft"] = out.pop("edu_diagonal_dominant_rows")
        out["edu_own_level_above_1"] = [bool(fe[e, e] > 0.0) for e in range(N_EDU)]
        out["edu_own_level_above_two_or_more_away"] = [
            bool(all(fe[e, e] > fe[e, f] for f in range(N_EDU) if abs(f - e) >= 2)) for e in range(N_EDU)]
        out["edu_rule"] = "same-sex (ADR 0010 amended): own level > 1 and above every level >= 2 away"
        out["edu_pass"] = all(out["edu_own_level_above_1"]) and all(out["edu_own_level_above_two_or_more_away"])
        out["pass"] = out["age_pass"] and out["edu_pass"] and out["race_pass"]
    if form.edu_by_sex:
        rows = {SEX_LEVELS[s]: [bool(fg["edu"][s, e, e] == fg["edu"][s, e].max()) for e in range(N_EDU)]
                for s in range(N_SEX)}
        out["edu_diagonal_dominant_rows_by_sex"] = rows
        out["edu_pass"] = all(all(v) for v in rows.values())
        out["pass"] = out["age_pass"] and out["edu_pass"] and out["race_pass"]
    return out


def held_out_loglik(C_eval: np.ndarray, f: dict, A: np.ndarray, form: Form, same_sex: bool = False) -> float:
    """Conditional-logit log-likelihood of a couple table under a kernel
    with availability A (weight units), in the Phase 3 convention
    (kernel.dial_loglik_grad_hess): the couple's own log A(c) is a
    constant across kernels and is left out, so a couple whose partner
    type has no singles in the availability table scores finitely."""
    d = design2(form)
    logW = d.gather(f)
    logK = logW + log_avail(A, same_sex)
    m = logK.max(axis=1, keepdims=True)
    m[~np.isfinite(m)] = 0.0
    logZ = np.log(np.maximum(np.exp(logK - m).sum(axis=1), 1e-300)) + m[:, 0]
    ok = C_eval > 0
    return float((C_eval[ok] * (logW[ok] - logZ[np.nonzero(ok)[0]])).sum())


# ---------------------------------------------------------------------------
# tables and the split
# ---------------------------------------------------------------------------

def load_sample(sample: str, same_sex: bool = False) -> dict:
    tag = f"samesex_{sample}" if same_sex else sample
    nat = pd.read_parquet(DATA / f"couple_table_national_{tag}.parquet")
    C = K.table_to_dense(nat)
    n_alloc = K.table_to_dense(nat, "n_alloc")
    sumw2 = K.table_to_dense(nat, "sumw2")
    return {"nat": nat, "C": C, "n_alloc": n_alloc, "sumw2": sumw2,
            "mean_weight": float(C.sum() / n_alloc.sum())}


def fold_tables(sample: str, same_sex: bool = False) -> tuple[np.ndarray, np.ndarray]:
    """The national couple table split in half by household (the metro
    tables' fold summed over metros — they sum to the national table
    exactly)."""
    tag = f"samesex_{sample}" if same_sex else sample
    df = pd.read_parquet(DATA / f"couple_table_metro_{tag}.parquet")
    return tuple(K.table_to_dense(df[df["fold"] == k]) for k in (0, 1))


def cohort_sample(nat: pd.DataFrame, form: Form) -> list[dict]:
    """Effective couple-sides behind each (sex, cohort), with the thin gap
    cells within ten years named."""
    coh = form.cohort_of_age()
    df = nat.copy()
    df["cohort"] = coh[df["age_s"].to_numpy(int) - 18]
    df["gap"] = df["age_c"] - df["age_s"]
    out = []
    for (sex, c), g in df.groupby(["sex_s", "cohort"]):
        kish = float(g["w"].sum() ** 2 / g["sumw2"].sum())
        near = g[g["gap"].abs() <= 10].groupby("gap")
        gk = (near["w"].sum() ** 2 / near["sumw2"].sum())
        thin = sorted(int(x) for x in gk.index[gk < 100])
        out.append({"sex_s": sex, "cohort": form.cohort_labels()[c], "sides_weighted": round(float(g["w"].sum()), 1),
                    "sides_alloc": round(float(g["n_alloc"].sum()), 1), "sides_kish": round(kish, 1),
                    "gaps_within_10y_below_100_effective": thin,
                    "gap_cells_below_30_effective": int((g.groupby("gap")["w"].sum() ** 2
                                                        / g.groupby("gap")["sumw2"].sum() < 30).sum())})
    return out


# ---------------------------------------------------------------------------
# B1: the partition, by split-half held-out likelihood
# ---------------------------------------------------------------------------

def choose_partition(sample: str, A: np.ndarray, mean_weight: float) -> dict:
    """Fit each candidate partition on one household half of the national
    couple table (per-cohort bandwidth CV inside) and score the other half;
    both directions summed. The partition with the highest held-out
    log-likelihood wins; 'one' is the m3.1.0 baseline."""
    h0, h1 = fold_tables(sample)
    out = {"candidates": {}, "criterion": "split-half (household) held-out conditional-logit "
                                         "log-likelihood, both directions summed"}
    for name, edges in PARTITIONS.items():
        form = Form(age_edges=edges, name=f"age_{name}")
        t0 = time.time()
        ll = 0.0
        ll_in = 0.0
        for fit_half, eval_half in ((h0, h1), (h1, h0)):
            fit = fit_form(fit_half, A, form, mean_weight=mean_weight)
            ll += held_out_loglik(eval_half, fit["f"], A, form)
            ll_in += held_out_loglik(fit_half, fit["f"], A, form)
        out["candidates"][name] = {"edges": list(edges), "cohorts": form.cohort_labels(),
                                   "heldout_loglik": ll, "insample_loglik": ll_in,
                                   "seconds": round(time.time() - t0, 1)}
        print(f"  partition {name}: held-out {ll:.1f} ({time.time() - t0:.0f}s)", flush=True)
    base = out["candidates"]["one"]["heldout_loglik"]
    sides = float(h0.sum() + h1.sum())
    for c in out["candidates"].values():
        c["gain_vs_one_per_1000_weighted_sides"] = (c["heldout_loglik"] - base) / sides * 1000
    best = max(out["candidates"], key=lambda n: out["candidates"][n]["heldout_loglik"])
    out["chosen"] = best
    out["chosen_edges"] = list(PARTITIONS[best])
    return out


# ---------------------------------------------------------------------------
# the full fits (item: fit)
# ---------------------------------------------------------------------------

def forms_for(sample: str, partition_edges: tuple[int, ...]) -> dict[str, Form]:
    return {"baseline": Form(name="baseline"),
            "B1_age_cohorts": Form(age_edges=partition_edges, name="B1_age_cohorts"),
            "B2a_race_x_edu": Form(interaction=True, name="B2a_race_x_edu"),
            "B2b_edu_by_sex": Form(edu_by_sex=True, name="B2b_edu_by_sex"),
            # Phase 3c B3: the held-back refinements added to the shipped
            # form (baseline + race x education), the cohorts as chosen in 3b
            "C1_cohorts_plus_shipped": Form(age_edges=partition_edges, interaction=True,
                                            name="C1_cohorts_plus_shipped"),
            "C2_edu_by_sex_plus_shipped": Form(edu_by_sex=True, interaction=True,
                                               name="C2_edu_by_sex_plus_shipped"),
            "C3_both_plus_shipped": Form(age_edges=partition_edges, edu_by_sex=True, interaction=True,
                                         name="C3_both_plus_shipped")}


def fit_and_report(sample: str, form: Form, S: dict, A: np.ndarray, same_sex: bool = False) -> dict:
    """National fit of one form on the sample, with the report tables:
    face validity, separability, the age curves, cohort samples, the
    interaction table."""
    t0 = time.time()
    fit = fit_form(S["C"], A, form, mean_weight=S["mean_weight"], same_sex=same_sex)
    fg = gauge_form(fit["f"], A, fit["N_s"], form, same_sex)
    d = design2(form)
    tag = f"{form.name}{'_samesex' if same_sex else ''}"
    rec = {"form": form.describe(), "same_sex": same_sex,
           "ipf": {"raw_iterations": fit["raw_iterations"], "smoothed_iterations": fit["smoothed_iterations"],
                   "interaction_iterations": fit["interaction_iterations"], "converged": fit["converged"],
                   "final_change": fit["final_change"]},
           "bandwidth_by_sex_cohort": {f"{SEX_LEVELS[i // d.K]}:{form.cohort_labels()[i % d.K]}": fit["bandwidth"][i]
                                       for i in range(N_SEX * d.K)},
           "face_validity": face_validity(fg, A, form, same_sex),
           "separability": K.separability(S["C"], fit["mu"], S["mean_weight"]),
           "seconds": round(time.time() - t0, 1)}
    if form.age_edges:
        rec["cohort_sample"] = cohort_sample(S["nat"], form)
    if form.interaction:
        rec["interaction_prior"] = fit["interaction_prior"]
        g = fg["int"]
        Tn = fit["T"]["int"].reshape(g.shape) / S["mean_weight"]
        rows = []
        for s in range(N_SEX):
            for rs in range(N_RACE):
                for rc in range(N_RACE):
                    for es in range(N_EDU):
                        for ec in range(N_EDU):
                            rows.append({"sex_s": SEX_LEVELS[s], "race_s": RACE_LEVELS[rs], "race_c": RACE_LEVELS[rc],
                                         "edu_s": EDU_LEVELS[es], "edu_c": EDU_LEVELS[ec],
                                         "multiplier": round(float(np.exp(g[s, rs, rc, es, ec])), 4),
                                         "log": round(float(g[s, rs, rc, es, ec]), 5),
                                         "sides_alloc": round(float(Tn[s, rs, rc, es, ec]), 1)})
        pd.DataFrame(rows).to_csv(P3B / f"interaction_table_{tag}.csv", index=False)
        ag = np.abs(g)
        rec["interaction_summary"] = {
            "cells": int(g.size), "cells_with_couples": int((Tn > 0).sum()),
            "log_sd": round(float(g.std()), 4),
            "cells_abs_log_above_0_1": int((ag > 0.1).sum()),
            "cells_abs_log_above_0_5": int((ag > 0.5).sum()),
            "max_multiplier": round(float(np.exp(g.max())), 3), "min_multiplier": round(float(np.exp(g.min())), 3),
            "worst_phase3_cell_white_man_asian_woman_grad_grad": round(float(np.exp(
                g[0, RACE_LEVELS.index("nh_white"), RACE_LEVELS.index("nh_asian"),
                  EDU_LEVELS.index("graduate"), EDU_LEVELS.index("graduate")])), 3)}
    K.age_curves(S["C"], fit["mu"]).to_csv(P3B / f"age_curves_{tag}.csv", index=False)
    pd.DataFrame({"sex_s": np.repeat(SEX_LEVELS, d.K * N_GAP),
                  "cohort": np.tile(np.repeat(form.cohort_labels(), N_GAP), N_SEX),
                  "gap": np.tile(np.arange(N_GAP) - GAP0, N_SEX * d.K),
                  "raw_log_mult": fit["raw_f"]["age"].ravel(), "smoothed_log_mult": fit["f"]["age"].ravel(),
                  "gauged_log_mult": fg["age"].ravel()}).to_csv(P3B / f"age_term_{tag}.csv", index=False)
    mult = {"edu": (fg["edu"] if not form.edu_by_sex else fg["edu"]).round(4).tolist(),
            "race": {SEX_LEVELS[s]: np.exp(fg["race"][s]).round(4).tolist() for s in range(N_SEX)}}
    mult["edu"] = (np.exp(fg["edu"]).round(4).tolist())
    (P3B / f"multipliers_{tag}.json").write_text(json.dumps(mult, indent=1) + "\n")
    return {"record": rec, "fit": fit, "fg": fg}


# ---------------------------------------------------------------------------
# the leave-one-metro-out held-out test, all forms in one pass
# ---------------------------------------------------------------------------

_W: dict = {}


def _init_worker(state: dict) -> None:
    _W.update(state)


def _lomo_forms_one(cbsa: str) -> dict:
    """Leave `cbsa` out: for every form, refit the national kernel without
    it (warm-started, the full fit's bandwidths and tau^2), fit its three
    dials jointly on each household half, shrink them with the other
    metros' full-sample (mu, tau^2) for that form, and score the other
    half — the split-half held-out log-likelihood the Part B rule reads —
    plus the Pew out-group predictions for the record."""
    i = _W["midx"][cbsa]
    mc = _W["full"][cbsa]
    h0, h1 = _W["halves"][cbsa]
    A, A_m = _W["A"], _W["A_metro"][i]
    C_minus = _W["C"].copy()
    np.add.at(C_minus, (mc.s, mc.c), -mc.w)
    C_minus[C_minus < 0] = 0.0
    A_minus = np.maximum(A - A_m, 0.0)
    n_eff = _W["n_eff"].get(cbsa, {k: np.nan for k in COMPONENTS})
    others = np.array([j for j in range(len(_W["metro_levels"])) if j != i])
    out = {"cbsa": cbsa, "forms": {}}
    for name, form in _W["forms"].items():
        F = _W["fits"][name]
        fit = fit_form(C_minus, A_minus, form, bandwidth=F["bandwidth"], tau2=F["tau2"],
                       init={**F["raw_f"], **({"int": F["f"]["int"]} if form.interaction else {})},
                       tol=1e-4, max_iter=25, mean_weight=_W["mean_weight"])
        f_m = gauge_form(fit["f"], A_minus, fit["N_s"], form)
        shs = [K.shrink(_W["theta_hat"][name][others, k], _W["se2"][name][others, k]) for k in range(3)]
        rec = {"iterations": fit["iterations"], "national": 0.0, "shrunk": 0.0, "raw": 0.0, "sides": 0.0,
               "national_all": 0.0}
        for fit_half, eval_half in ((h0, h1), (h1, h0)):
            if fit_half.W <= 0 or eval_half.W <= 0:
                continue
            dh = fit_dials(f_m, fit_half, A_m, form)
            se2h = K.dial_se2(dh, {c: n_eff[c] / 2 for c in COMPONENTS})
            th = np.ones(3)
            for k in range(3):
                th[k], _ = K.shrink_one(dh["theta"][k], se2h[k], shs[k])
            rec["national"] += loglik_at(np.ones(3), f_m, eval_half, A_m, form)
            rec["shrunk"] += loglik_at(th, f_m, eval_half, A_m, form)
            rec["raw"] += loglik_at(dh["theta"], f_m, eval_half, A_m, form)
            rec["sides"] += eval_half.W
        rec["national_all"] = loglik_at(np.ones(3), f_m, mc, A_m, form)
        # the shipped-dial kernel's Pew prediction (all couples' dials, shrunk)
        d_all = fit_dials(f_m, mc, A_m, form)
        se2 = K.dial_se2(d_all, n_eff)
        tilde = np.ones(3)
        for k in range(3):
            tilde[k], _ = K.shrink_one(d_all["theta"][k], se2[k], shs[k])
        pi = K.formation_propensity(fit["N_s"], A_minus)
        pn = predict_outgroup(f_m, np.ones(3), A_m, pi, form)
        rec["pew_pred"] = {"national_only": pn["predicted"], "random_pairing": pn["random_pairing"],
                           "raw_dial": predict_outgroup(f_m, d_all["theta"], A_m, pi, form)["predicted"],
                           "shrunk_dial": predict_outgroup(f_m, tilde, A_m, pi, form)["predicted"],
                           "observed_fitting_sample": K.observed_outgroup(mc)}
        rec["theta_tilde"] = tilde.tolist()
        out["forms"][name] = rec
    return out


def run_lomo_forms(state: dict, metro_levels: list[str], workers: int) -> list[dict]:
    import multiprocessing as mp
    ctx = mp.get_context("fork")
    with ProcessPoolExecutor(max_workers=workers, mp_context=ctx,
                             initializer=_init_worker, initargs=(state,)) as ex:
        return list(ex.map(_lomo_forms_one, metro_levels, chunksize=2))


def full_dials(fg: dict, form: Form, full: dict, A_metro: np.ndarray, metro_levels: list[str],
               n_eff: dict) -> tuple[np.ndarray, np.ndarray, dict]:
    theta_hat = np.ones((len(metro_levels), 3))
    se2 = np.full((len(metro_levels), 3), np.inf)
    for i, cbsa in enumerate(metro_levels):
        mc = full.get(cbsa)
        if mc is None or mc.W <= 0:
            continue
        dm = fit_dials(fg, mc, A_metro[i], form)
        theta_hat[i] = dm["theta"]
        se2[i] = K.dial_se2(dm, n_eff.get(cbsa, {k: np.nan for k in COMPONENTS}))
    shr = {k: K.shrink(theta_hat[:, j], se2[:, j]) for j, k in enumerate(COMPONENTS)}
    return theta_hat, se2, shr


def _json(o):
    return K._json(o)


def load_common(sample: str) -> dict:
    con = open_pool()
    con.execute("SET enable_progress_bar=false")
    metro_levels = sorted(pd.read_csv(RESULTS / "metros.csv", dtype={"cbsa": str})["cbsa"])
    A, A_metro = K.load_singles(con, metro_levels)
    con.close()
    marg = pd.read_parquet(DATA / f"couple_marginals_metro_{sample}.parquet")
    marg["cbsa"] = marg["cbsa"].astype(str)
    ne = K.effective_counts(marg)
    n_eff = {c: {k: float(ne.loc[c, f"n_eff_{k}"]) for k in COMPONENTS} for c in ne.index}
    return {"metro_levels": metro_levels, "A": A, "A_metro": A_metro, "n_eff": n_eff}


def cmd_check(sample: str) -> None:
    """The generalised machinery must reproduce kernel.py's fit exactly
    on the baseline form (same bandwidths -> same log multipliers, same
    gauge, same dials) before anything heavier runs."""
    common = load_common(sample)
    A = common["A"]
    S = load_sample(sample)
    report = json.loads((P3 / "kernel_report.json").read_text())
    bw = report["samples"][sample]["bandwidth"]
    t0 = time.time()
    ref = K.fit_national(S["C"], A, bandwidth=tuple(bw))
    ref_g = K.gauge(ref["f"], A, ref["N_s"])
    t1 = time.time()
    new = fit_form(S["C"], A, Form(), bandwidth=bw, mean_weight=S["mean_weight"])
    new_g = gauge_form(new["f"], A, new["N_s"], Form())
    t2 = time.time()
    diffs = {"age": float(np.abs(ref_g["age"] - new_g["age"][:, 0, :]).max()),
             "edu": float(np.abs(ref_g["edu"] - new_g["edu"]).max()),
             "race": float(np.abs(ref_g["race"] - new_g["race"]).max()),
             "log_norm": float(np.abs(K.log_norm_for(ref_g, A) - log_norm_form(new_g, A, Form())).max())}
    cv_new = fit_form(S["C"], A, Form(), mean_weight=S["mean_weight"])["bandwidth"]
    full, halves = K.load_metro_tables(sample)
    cb = common["metro_levels"][100]
    d_ref = K.fit_dials(ref_g, full[cb], common["A_metro"][100])
    d_new = fit_dials(new_g, full[cb], common["A_metro"][100], Form())
    diffs["dials_metro_100"] = float(np.abs(d_ref["theta"] - d_new["theta"]).max())
    diffs["loglik_metro_100"] = float(abs(d_ref["loglik"] - d_new["loglik"]))
    print(json.dumps({"max_abs_diff_vs_kernel_py": diffs, "bandwidth_cv_baseline": cv_new,
                      "phase3_bandwidth": bw, "seconds_ref": round(t1 - t0, 1),
                      "seconds_form": round(t2 - t1, 1)}, indent=1))
    assert max(diffs.values()) < 1e-8, diffs
    print("check passed: the Form machinery reproduces kernel.py on the baseline form")


def cmd_fit(sample: str, only: list[str] | None = None) -> None:
    """The full-sample fits of every form with their report tables, the
    B1 partition choice first. `only` (Phase 3c) fits the named forms on
    the partition already chosen and appends them to the standing store
    without refitting the rest."""
    P3B.mkdir(parents=True, exist_ok=True)
    t0 = time.time()
    common = load_common(sample)
    A = common["A"]
    S = load_sample(sample)
    if only:
        report = json.loads((P3B / "refine_fits.json").read_text())
        part = report["partition"]
        print(f"[{sample}] partition as chosen: {part['chosen']} {part['chosen_edges']}", flush=True)
        forms = {n: f for n, f in forms_for(sample, tuple(part["chosen_edges"])).items() if n in only}
        assert forms, only
    else:
        print(f"[{sample}] choosing the age partition by split-half held-out likelihood ...", flush=True)
        part = choose_partition(sample, A, S["mean_weight"])
        print(f"  chosen: {part['chosen']} {part['chosen_edges']}", flush=True)
        forms = forms_for(sample, tuple(part["chosen_edges"]))
        report = {"sample": sample, "mean_weight_per_side": S["mean_weight"],
                  "couple_sides_weighted": float(S["C"].sum()), "n_alloc": float(S["n_alloc"].sum()),
                  "partition": part, "forms": {}, "fits": {}}
    fits = {}
    for name, form in forms.items():
        r = fit_and_report(sample, form, S, A)
        fits[name] = r
        report["forms"][name] = r["record"]
        print(f"  [{name}] fit {r['record']['ipf']} face {r['record']['face_validity']['pass']} "
              f"({r['record']['seconds']}s)", flush=True)
    # full-sample dials per form (the shrinkage each LOMO metro borrows)
    full, halves = K.load_metro_tables(sample)
    dials = {}
    for name, form in forms.items():
        th, se2, shr = full_dials(fits[name]["fg"], form, full, common["A_metro"],
                                  common["metro_levels"], common["n_eff"])
        dials[name] = {"theta_hat": th, "se2": se2}
        report["forms"][name]["dials"] = {k: {"tau": round(shr[k]["tau"], 4),
                                              "precision_weighted_mean_theta": round(shr[k]["precision_weighted_mean"], 4),
                                              "prior_share_median": round(float(np.median(shr[k]["prior_share"])), 4)}
                                          for k in COMPONENTS}
        dd = pd.DataFrame({"cbsa": common["metro_levels"]})
        for j, k in enumerate(COMPONENTS):
            dd[f"theta_hat_{k}"] = th[:, j]
            dd[f"se_{k}"] = np.sqrt(se2[:, j])
            dd[f"theta_tilde_{k}"] = shr[k]["theta_tilde"]
            dd[f"prior_share_{k}"] = shr[k]["prior_share"]
        dd.to_csv(P3B / f"dials_{name}.csv", index=False)
    # persist the fits for the LOMO step (arrays in npz, records in json)
    arrays = {f"{name}__{k}": v for name, r in fits.items()
              for k, v in {**{f"f_{c}": r["fit"]["f"][c] for c in r["fit"]["f"]},
                           **{f"raw_{c}": r["fit"]["raw_f"][c] for c in r["fit"]["raw_f"]},
                           **{f"fg_{c}": r["fg"][c] for c in r["fg"]},
                           "theta_hat": dials[name]["theta_hat"], "se2": dials[name]["se2"],
                           "N_s": r["fit"]["N_s"]}.items()}
    if only and (P3B / "_form_fits.npz").exists():
        prev = dict(np.load(P3B / "_form_fits.npz"))
        prev = {k: v for k, v in prev.items() if k.split("__")[0] not in forms}
        arrays = {**prev, **arrays}
    np.savez_compressed(P3B / "_form_fits.npz", **arrays)
    report.setdefault("fits", {}).update({name: {"bandwidth": r["fit"]["bandwidth"], "tau2": r["fit"]["tau2"]}
                                          for name, r in fits.items()})
    report["seconds"] = round(time.time() - t0, 1)
    (P3B / "refine_fits.json").write_text(json.dumps(report, indent=1, default=_json) + "\n")
    print(f"fits -> results/phase3b/refine_fits.json ({report['seconds']}s)")


def _load_fits(names: list[str]) -> dict:
    z = np.load(P3B / "_form_fits.npz")
    rep = json.loads((P3B / "refine_fits.json").read_text())
    out = {}
    for name in names:
        keys = [k for k in z.files if k.startswith(name + "__")]
        f = {k[len(name) + 4:]: z[k] for k in keys if k[len(name) + 2:].startswith("f_")}
        raw = {k[len(name) + 6:]: z[k] for k in keys if k[len(name) + 2:].startswith("raw_")}
        fg = {k[len(name) + 5:]: z[k] for k in keys if k[len(name) + 2:].startswith("fg_")}
        out[name] = {"f": f, "raw_f": raw, "fg": fg, "theta_hat": z[f"{name}__theta_hat"],
                     "se2": z[f"{name}__se2"], "N_s": z[f"{name}__N_s"],
                     "bandwidth": rep["fits"][name]["bandwidth"], "tau2": rep["fits"][name]["tau2"]}
    return out, rep


def cmd_lomo(sample: str, workers: int, only: list[str] | None = None) -> None:
    """The held-out test for every form in one pass over the 387 metros."""
    t0 = time.time()
    common = load_common(sample)
    S = load_sample(sample)
    rep = json.loads((P3B / "refine_fits.json").read_text())
    forms = forms_for(sample, tuple(rep["partition"]["chosen_edges"]))
    if "shipped" in rep["forms"]:
        fr = rep["forms"]["shipped"]["form"]
        forms["shipped"] = Form(age_edges=tuple(fr["age_edges"]), edu_by_sex=fr["edu_by_sex"],
                                interaction=fr["interaction"], name="shipped")
    if only:
        forms = {n: f for n, f in forms.items() if n in only}
    assert forms, f"no form to run: {only}"
    fits, _ = _load_fits(list(forms))
    full, halves = K.load_metro_tables(sample)
    state = {"C": S["C"], "A": common["A"], "A_metro": common["A_metro"],
             "metro_levels": common["metro_levels"],
             "midx": {c: i for i, c in enumerate(common["metro_levels"])},
             "forms": forms, "fits": fits, "full": full, "halves": halves, "n_eff": common["n_eff"],
             "theta_hat": {n: fits[n]["theta_hat"] for n in forms},
             "se2": {n: fits[n]["se2"] for n in forms}, "mean_weight": S["mean_weight"]}
    print(f"[{sample}] LOMO x{len(common['metro_levels'])} over forms {list(forms)} "
          f"with {workers} workers ...", flush=True)
    lomo = run_lomo_forms(state, common["metro_levels"], workers)
    path = P3B / "lomo_forms.json"
    if only and path.exists():
        # merge into the standing record (same metros, same halves), so the
        # summary reads every form fitted so far beside the baseline
        prev = {r["cbsa"]: r for r in json.loads(path.read_text())}
        for r in lomo:
            prev.setdefault(r["cbsa"], {"cbsa": r["cbsa"], "forms": {}})["forms"].update(r["forms"])
        lomo = [prev[c] for c in common["metro_levels"] if c in prev]
    path.write_text(json.dumps(lomo, indent=0, default=_json) + "\n")
    all_forms = {**forms_for(sample, tuple(rep["partition"]["chosen_edges"]))}
    if "shipped" in rep["forms"]:
        all_forms["shipped"] = Form(age_edges=tuple(rep["forms"]["shipped"]["form"]["age_edges"]),
                                    edu_by_sex=rep["forms"]["shipped"]["form"]["edu_by_sex"],
                                    interaction=rep["forms"]["shipped"]["form"]["interaction"], name="shipped")
    present = {n: f for n, f in all_forms.items() if all(n in r["forms"] for r in lomo)}
    summarise_lomo(sample, lomo, present, common, full)
    print(f"LOMO done ({time.time() - t0:.0f}s)")


def summarise_lomo(sample: str, lomo: list[dict], forms: dict, common: dict, full: dict) -> dict:
    base = "baseline"
    out = {"sample": sample, "metros": len(lomo), "forms": {}, "rule": (
        "a refinement ships when its total split-half held-out log-likelihood under the "
        "shrunk-dial kernel exceeds the baseline form's (same metros, same halves, same "
        "shrinkage machinery); metro counts and the national-only (no-dial) comparison are "
        "reported beside it")}
    sides = sum(r["forms"][base]["sides"] for r in lomo)
    for name in forms:
        tot = {k: sum(r["forms"][name][k] for r in lomo) for k in ("national", "shrunk", "raw", "national_all")}
        btot = {k: sum(r["forms"][base][k] for r in lomo) for k in ("national", "shrunk", "raw", "national_all")}
        wins = sum(1 for r in lomo if r["forms"][name]["shrunk"] > r["forms"][base]["shrunk"])
        wins_nat = sum(1 for r in lomo if r["forms"][name]["national"] > r["forms"][base]["national"])
        rec = {"heldout_loglik_shrunk": tot["shrunk"], "heldout_loglik_national": tot["national"],
               "heldout_loglik_raw": tot["raw"], "heldout_sides": sides,
               "gain_vs_baseline_shrunk_per_1000_sides": (tot["shrunk"] - btot["shrunk"]) / sides * 1000,
               "gain_vs_baseline_national_per_1000_sides": (tot["national"] - btot["national"]) / sides * 1000,
               "gain_all_couples_national_per_1000_sides": (tot["national_all"] - btot["national_all"])
               / sum(full[c].W for c in common["metro_levels"]) * 1000,
               "metros_where_better_than_baseline_shrunk": wins,
               "metros_where_better_than_baseline_national": wins_nat,
               "dial_gain_shrunk_minus_national_per_1000_sides": (tot["shrunk"] - tot["national"]) / sides * 1000,
               "lomo_iterations_median": float(np.median([r["forms"][name]["iterations"] for r in lomo])),
               "ships": bool(name != base and tot["shrunk"] > btot["shrunk"])}
        if "shipped" in forms and all("shipped" in r["forms"] for r in lomo):
            # Phase 3c B3: the candidates are judged against the SHIPPED
            # form (baseline + race x education), not the baseline
            stot = sum(r["forms"]["shipped"]["shrunk"] for r in lomo)
            rec["gain_vs_shipped_shrunk_per_1000_sides"] = (tot["shrunk"] - stot) / sides * 1000
            rec["metros_where_better_than_shipped_shrunk"] = sum(
                1 for r in lomo if r["forms"][name]["shrunk"] > r["forms"]["shipped"]["shrunk"])
            rec["improves_on_shipped"] = bool(tot["shrunk"] > stot)
        # the Pew comparison for the record
        pew_rec, comp = K.pew_comparison(
            [{"cbsa": r["cbsa"], "pew_pred": r["forms"][name]["pew_pred"]} for r in lomo],
            K.pew_table(common["metro_levels"]), K.pew_national(),
            json.loads((P3 / "kernel_report.json").read_text())["samples"][sample]["national_outgroup_share"],
            common["metro_levels"], full, P3B / f"pew_lomo_{name}.csv")
        rec["pew"] = {"corrected_errors": pew_rec["corrected_errors"], "paired": pew_rec["paired"],
                      "level_offset_ratio_ours_over_pew": pew_rec["level_offset_ratio_ours_over_pew"]}
        out["forms"][name] = rec
        print(f"  [{name}] held-out gain vs baseline (shrunk) {rec['gain_vs_baseline_shrunk_per_1000_sides']:+.3f} "
              f"per 1,000 sides, better in {wins}/{len(lomo)} metros; ships={rec['ships']}; "
              f"Pew shrunk {pew_rec['corrected_errors']['shrunk_dial']['median_abs_pts']}", flush=True)
    (P3B / "refine_heldout.json").write_text(json.dumps(out, indent=1, default=_json) + "\n")
    return out


# ---------------------------------------------------------------------------
# the combined form, the artifact (kernel_v2) and shipping
# ---------------------------------------------------------------------------

def cmd_combine(sample: str, only: list[str] | None = None, reason: str | None = None) -> None:
    """The shipped opposite-sex form = the baseline plus every refinement
    whose held-out test says it ships (refine_heldout.json); fitted on the
    full sample with its dials and appended to the fit record as
    'shipped' (a LOMO run with --only shipped then puts its held-out
    figure and Pew comparison on the record)."""
    rep = json.loads((P3B / "refine_fits.json").read_text())
    ho = json.loads((P3B / "refine_heldout.json").read_text())
    # the Part B rule: improves total held-out likelihood AND does not
    # break rank stability (stability_check.json, the candidate loaded
    # into the m3.1.0 build); latency is measured on the shipped build
    st = json.loads((P3B / "stability_check.json").read_text())["candidates"]
    ships = {}
    for n, r in ho["forms"].items():
        if n == "baseline":
            continue
        ships[n] = {"improves_heldout": bool(r["ships"]),
                    "heldout_gain_per_1000_sides": r["gain_vs_baseline_shrunk_per_1000_sides"],
                    "rank_stability_pass": bool(st[n]["pass"]) if n in st else None,
                    "rank_stability_min_share": st[n]["min_share"] if n in st else None,
                    "ships": bool(r["ships"] and n in st and st[n]["pass"])}
    if only is not None:
        # the combination of individually-passing refinements failed the
        # gate: ship the named subset and record why
        for n in ships:
            ships[n]["ships_in_combination"] = n in only
            ships[n]["combination_note"] = reason
    use = {n: (n in only) if only is not None else v["ships"] for n, v in ships.items()}
    form = Form(age_edges=tuple(rep["partition"]["chosen_edges"]) if use.get("B1_age_cohorts") else (),
                edu_by_sex=bool(use.get("B2b_edu_by_sex")),
                interaction=bool(use.get("B2a_race_x_edu")), name="shipped")
    common = load_common(sample)
    S = load_sample(sample)
    r = fit_and_report(sample, form, S, common["A"])
    full, _ = K.load_metro_tables(sample)
    th, se2, shr = full_dials(r["fg"], form, full, common["A_metro"], common["metro_levels"], common["n_eff"])
    rec = r["record"]
    rec["dials"] = {k: {"tau": round(shr[k]["tau"], 4),
                        "precision_weighted_mean_theta": round(shr[k]["precision_weighted_mean"], 4),
                        "prior_share_median": round(float(np.median(shr[k]["prior_share"])), 4),
                        "metros_prior_share_above_0_9": int((shr[k]["prior_share"] > 0.9).sum())}
                    for k in COMPONENTS}
    rec["refinements"] = ships
    dd = pd.DataFrame({"cbsa": common["metro_levels"]})
    for j, k in enumerate(COMPONENTS):
        dd[f"theta_hat_{k}"] = th[:, j]
        dd[f"se_{k}"] = np.sqrt(se2[:, j])
        dd[f"theta_tilde_{k}"] = shr[k]["theta_tilde"]
        dd[f"prior_share_{k}"] = shr[k]["prior_share"]
    dd.to_csv(P3B / "dials_shipped.csv", index=False)
    z = dict(np.load(P3B / "_form_fits.npz"))
    z = {k: v for k, v in z.items() if not k.startswith("shipped__")}
    z.update({f"shipped__f_{c}": r["fit"]["f"][c] for c in r["fit"]["f"]})
    z.update({f"shipped__raw_{c}": r["fit"]["raw_f"][c] for c in r["fit"]["raw_f"]})
    z.update({f"shipped__fg_{c}": r["fg"][c] for c in r["fg"]})
    z.update({"shipped__theta_hat": th, "shipped__se2": se2, "shipped__N_s": r["fit"]["N_s"]})
    np.savez_compressed(P3B / "_form_fits.npz", **z)
    rep["forms"]["shipped"] = rec
    rep["fits"]["shipped"] = {"bandwidth": r["fit"]["bandwidth"], "tau2": r["fit"]["tau2"]}
    (P3B / "refine_fits.json").write_text(json.dumps(rep, indent=1, default=_json) + "\n")
    print(json.dumps({"shipped_form": form.describe(), "refinements": ships,
                      "face_validity": rec["face_validity"]["pass"], "dials": rec["dials"]}, indent=1))


def served_log_kernel(fg_os: dict, form_os: Form, theta: np.ndarray, fg_ss: dict | None, form_ss: Form | None,
                      ss_components: tuple[str, ...], ss_interaction: bool | None = None) -> np.ndarray:
    """log w(s, c) for every seeker type under the served composition: a
    same-sex search takes the components in `ss_components` from the
    same-sex fit at dial 1 and the rest from the opposite-sex fit with
    the metro's dial. Whether the opposite-sex interaction rides on a
    same-sex search is `ss_interaction`; None means m3.2.0's rule (only
    when both education and race come from the opposite-sex fit)."""
    d_os = design2(form_os)
    logK = np.zeros((N_S, N_C))
    for j, k in enumerate(COMPONENTS):
        if k in ss_components:
            logK += design2(form_ss).gather_one(k, fg_ss[k])
        else:
            logK += float(theta[j]) * d_os.gather_one(k, fg_os[k])
    if ss_interaction is None:
        ss_interaction = "edu" not in ss_components and "race" not in ss_components
    if fg_os.get("int") is not None and ss_interaction:
        logK += d_os.gather_one("int", fg_os["int"])
    return logK


def log_norm_served(logK: np.ndarray, A: np.ndarray, same_sex: bool) -> np.ndarray:
    sig = K.design().sig_s
    A_c = A[sig if same_sex else 1 - sig].reshape(N_S, N_C)
    tot = A_c.sum(axis=1)
    m = logK.max(axis=1, keepdims=True)
    mean = (A_c * np.exp(logK - m)).sum(axis=1) / np.maximum(tot, 1e-300)
    with np.errstate(divide="ignore"):
        ln = -(np.log(mean) + m[:, 0])
    ln[~np.isfinite(ln)] = 0.0
    return ln


def write_artifact_v2(out_dir: Path, form_os: Form, fg_os: dict, dials: np.ndarray, earned: list[str],
                      A: np.ndarray, metro_levels: list[str], ss: dict | None, meta: dict) -> dict:
    """kernel.json + kernel.npz, version kernel_v2: the opposite-sex terms
    (age per sex x cohort, education per sex, race per sex, the optional
    interaction), the dials, the per-metro normalisers for opposite-sex
    searches and — when same-sex terms ship — the same-sex terms with the
    normalisers of the served composition over the SAME sex's singles."""
    out_dir.mkdir(parents=True, exist_ok=True)
    n = len(metro_levels)
    f_edu = fg_os["edu"] if form_os.edu_by_sex else np.stack([fg_os["edu"], fg_os["edu"]])
    log_norm = np.stack([log_norm_served(served_log_kernel(fg_os, form_os, dials[i], None, None, ()), A, False)
                         for i in range(n)]).reshape(n, N_SEX, N_AGE, N_EDU, N_RACE)
    arrays = {"f_age": fg_os["age"], "f_edu": f_edu, "f_race": fg_os["race"],
              "cohort_edges": np.array(form_os.age_edges, int),
              "dials": dials, "log_norm": log_norm.astype(np.float32),
              "avail_national": A, "metro_levels": np.array(metro_levels)}
    if fg_os.get("int") is not None:
        arrays["f_int"] = fg_os["int"]
    same_sex_block = None
    if ss is not None and ss["components"]:
        comps = tuple(ss["components"])
        form_ss, fg_ss = ss["form"], ss["fg"]
        ss_int = ss.get("interaction")
        if ss_int is None:
            ss_int = "edu" not in comps and "race" not in comps
        ss_int = bool(ss_int and fg_os.get("int") is not None)
        ln_ss = np.stack([log_norm_served(served_log_kernel(fg_os, form_os, dials[i], fg_ss, form_ss, comps, ss_int),
                                          A, True) for i in range(n)]).reshape(n, N_SEX, N_AGE, N_EDU, N_RACE)
        arrays.update({"ss_f_age": fg_ss["age"],
                       "ss_f_edu": (fg_ss["edu"] if form_ss.edu_by_sex else np.stack([fg_ss["edu"], fg_ss["edu"]])),
                       "ss_f_race": fg_ss["race"], "ss_cohort_edges": np.array(form_ss.age_edges, int),
                       "ss_log_norm": ln_ss.astype(np.float32)})
        same_sex_block = {"components_from_same_sex_couples": list(comps),
                          "fallback_components": [k for k in COMPONENTS if k not in comps],
                          "dials_on_same_sex_terms": "none (national terms at dial 1); the fallback "
                                                     "components keep the metro's dial",
                          "interaction_applies": ss_int,
                          **ss.get("record", {})}
    np.savez_compressed(out_dir / "kernel.npz", **arrays)
    payload = {
        "version": KERNEL_VERSION_V2,
        "form": "w = exp(theta_age f_age(gap; sex_s, cohort(age_s)) + theta_edu f_edu(edu_s, edu_c; sex_s) "
                "+ theta_race f_race(race_s, race_c; sex_s) + g(race_s, race_c, edu_s, edu_c; sex_s) "
                "+ log_norm(metro, seeker)); a same-sex search takes the listed components from the "
                "same-sex fit at dial 1",
        "gauge": "each main effect: availability-weighted mean multiplier 1 on its own margin under "
                 "random pairing (age per sex x cohort); the interaction is centred by its zero-mean "
                 "prior; log_norm makes the full kernel average exactly 1 over the national single "
                 "adult population of the sought sex per seeker type",
        "sex_levels": SEX_LEVELS, "age_levels": list(range(18, 71)),
        "edu_levels": EDU_LEVELS, "race_levels": RACE_LEVELS,
        "gap_offset": GAP0, "floor_log": FLOOR,
        "age_cohort_edges": list(form_os.age_edges), "age_cohorts": form_os.cohort_labels(),
        "edu_by_sex": form_os.edu_by_sex, "interaction": form_os.interaction,
        "dial_components": earned, "components": list(COMPONENTS),
        "dials": {c: [round(float(x), 6) for x in dials[i]] for i, c in enumerate(metro_levels)},
        "same_sex": same_sex_block,
        "npz": "kernel.npz: f_age (sex x cohort x gap), f_edu (sex x edu x edu), f_race, f_int "
               "(sex x race x race x edu x edu, when present), cohort_edges, dials, log_norm "
               "(metro x sex x age x edu x race, float32), avail_national; ss_* the same-sex terms "
               "and normalisers when present",
        **meta,
    }
    (out_dir / "kernel.json").write_text(json.dumps(payload, indent=1, default=_json) + "\n")
    return payload


def cmd_candidate(sample: str, form_name: str, out_dir: Path) -> None:
    """A kernel_v2 artifact for any fitted form (its full-sample gauge and
    its shrunk dials, every component dialled), so the served effect of a
    refinement can be measured by loading it into the build in memory
    (phase3b_refine_effects.py) and the rank-stability harness can run on
    it. No same-sex terms."""
    rep = json.loads((P3B / "refine_fits.json").read_text())
    fits, _ = _load_fits([form_name])
    fr = rep["forms"][form_name]["form"]
    form = Form(age_edges=tuple(fr["age_edges"]), edu_by_sex=fr["edu_by_sex"],
                interaction=fr["interaction"], name=form_name)
    common = load_common(sample)
    dd = pd.read_csv(P3B / f"dials_{form_name}.csv", dtype={"cbsa": str}).set_index("cbsa").loc[common["metro_levels"]]
    dials = np.stack([dd[f"theta_tilde_{k}"].to_numpy(float) for k in COMPONENTS], axis=1)
    meta = {"fitting_sample": sample, "candidate_form": form_name, "provisional": True,
            "bandwidth_years": rep["fits"][form_name]["bandwidth"], "interaction_tau2": rep["fits"][form_name]["tau2"],
            "dials_tau": {k: rep["forms"][form_name]["dials"][k]["tau"] for k in COMPONENTS},
            "generated_at": time.strftime("%Y-%m-%dT%H:%M:%S%z")}
    write_artifact_v2(out_dir, form, fits[form_name]["fg"], dials, list(COMPONENTS), common["A"],
                      common["metro_levels"], None, meta)
    print(f"candidate {form_name} -> {out_dir}")


def cmd_ship(sample: str, out_dir: Path | None = None, form_name: str = "shipped",
             extra_meta: dict | None = None) -> None:
    """Write the artifact from a fitted form's full fit, its dials and the
    same-sex decision (samesex_fit.json: the served components and, since
    m3.3.0, whether the interaction applies), to data/ or a candidate
    directory. `form_name` names the opposite-sex form ("shipped" for
    m3.2.0; Phase 3c ships the B3 winner by name)."""
    rep = json.loads((P3B / "refine_fits.json").read_text())
    ho = json.loads((P3B / "refine_heldout.json").read_text())
    fits, _ = _load_fits([form_name])
    fr = rep["forms"][form_name]["form"]
    form_os = Form(age_edges=tuple(fr["age_edges"]), edu_by_sex=fr["edu_by_sex"],
                   interaction=fr["interaction"], name=form_name)
    common = load_common(sample)
    dd = pd.read_csv(P3B / f"dials_{form_name}.csv", dtype={"cbsa": str}).set_index("cbsa").loc[common["metro_levels"]]
    # every component keeps its dial where the Phase 3 rule still earns it
    earned = [k for k in COMPONENTS if ho["forms"][form_name]["dial_gain_shrunk_minus_national_per_1000_sides"] > 0]
    dials = np.ones((len(common["metro_levels"]), 3))
    for j, k in enumerate(COMPONENTS):
        if k in earned:
            dials[:, j] = dd[f"theta_tilde_{k}"].to_numpy(float)
    ss = None
    ss_path = P3B / "samesex_fit.json"
    if ss_path.exists():
        srep = json.loads(ss_path.read_text())
        z = np.load(P3B / "_samesex_fit.npz")
        comps = tuple(srep["heldout"]["served_from_same_sex_couples"])
        ss = {"components": comps, "form": Form(name="samesex"),
              "fg": {k[3:]: z[k] for k in z.files if k.startswith("fg_")},
              "interaction": srep["heldout"].get("interaction_applies"),
              "record": {"support": srep["support"]["supported"],
                         "heldout_gain_per_1000_sides": srep["heldout"]["gain_per_1000_sides"],
                         "couple_sides_weighted": srep["couple_sides_weighted"], "n_alloc": srep["n_alloc"],
                         **({"interaction_decision": srep["heldout"]["interaction_decision"]}
                            if "interaction_decision" in srep["heldout"] else {})}}
    meta = {"fitting_sample": sample, "fitting_sample_spec": json.loads((P3 / "kernel_report.json").read_text())
            ["samples"][sample]["spec"],
            "couple_sides_weighted": rep["couple_sides_weighted"], "n_alloc": rep["n_alloc"],
            "bandwidth_years": rep["fits"][form_name]["bandwidth"],
            "interaction_tau2": rep["fits"][form_name]["tau2"],
            "refinements": rep["forms"][form_name].get("refinements"),
            "dials_tau": {k: rep["forms"][form_name]["dials"][k]["tau"] for k in COMPONENTS},
            "dials_centre": {k: rep["forms"][form_name]["dials"][k]["precision_weighted_mean_theta"]
                             for k in COMPONENTS},
            "shipped_form_name": form_name,
            "provisional": False, "generated_at": time.strftime("%Y-%m-%dT%H:%M:%S%z"),
            **(extra_meta or {})}
    out = out_dir or DATA
    write_artifact_v2(out, form_os, fits[form_name]["fg"], dials, earned, common["A"],
                      common["metro_levels"], ss, meta)
    print(f"artifact -> {out} (form {form_os.describe()}, dials {earned}, "
          f"same-sex components {ss['components'] if ss else None}, "
          f"same-sex interaction {ss['interaction'] if ss else None})")


# ---------------------------------------------------------------------------
# B3: same-sex pairing terms
# ---------------------------------------------------------------------------

SUPPORT_MIN_EFFECTIVE = 100.0


def samesex_support(nat: pd.DataFrame) -> dict:
    """Effective couple-sides per cell of each component's margin, per
    seeker sex, and the stated support rule (the Phase 3 stability
    criterion applied per component): education — every cell of the 4x4
    holds >= 100 effective sides; race — every own-group cell holds
    >= 100; age — every gap within ten years holds >= 100. A component is
    served from same-sex couples only when both sexes support it."""
    df = nat.copy()
    df["gap"] = df["age_c"] - df["age_s"]

    def kish(g):
        return g["w"].sum() ** 2 / g["sumw2"].sum()

    out = {"rule": {"edu": "every 4x4 cell >= 100 effective sides", "race": "every own-group cell >= 100",
                    "age": "every gap within 10 years >= 100"}, "by_sex": {}, "supported": {}}
    for sex, gs in df.groupby("sex_s"):
        edu = gs.groupby(["edu_s", "edu_c"]).apply(kish)
        race = gs.groupby(["race_s", "race_c"]).apply(kish)
        own = race[[a == b for a, b in race.index]]
        age = gs[gs["gap"].abs() <= 10].groupby("gap").apply(kish)
        out["by_sex"][sex] = {
            "sides_weighted": round(float(gs["w"].sum()), 1), "sides_alloc": round(float(gs["n_alloc"].sum()), 1),
            "sides_kish": round(float(kish(gs)), 1),
            "edu_cells_kish": {f"{a}->{b}": round(float(v), 1) for (a, b), v in edu.items()},
            "edu_min_kish": round(float(edu.min()), 1),
            "race_own_group_kish": {a: round(float(v), 1) for (a, _), v in own.items()},
            "race_cells_below_30": int((race < 30).sum()), "race_cells_empty": int(64 - len(race)),
            "race_own_min_kish": round(float(own.min()), 1), "race_own_groups_present": int(len(own)),
            "age_gap_within_10_min_kish": round(float(age.min()), 1),
            "age_gaps_within_10_below_100": [int(g) for g in age.index[age < SUPPORT_MIN_EFFECTIVE]],
            "supported": {"edu": bool(edu.min() >= SUPPORT_MIN_EFFECTIVE),
                          "race": bool(len(own) == N_RACE and own.min() >= SUPPORT_MIN_EFFECTIVE),
                          "age": bool(age.min() >= SUPPORT_MIN_EFFECTIVE)}}
    for k in COMPONENTS:
        out["supported"][k] = all(v["supported"][k] for v in out["by_sex"].values())
    return out


def _lomo_samesex_one(cbsa: str) -> dict:
    """Leave `cbsa` out: refit the same-sex kernel without its same-sex
    couples and the opposite-sex (shipped-form) kernel without its
    opposite-sex couples, then score its same-sex couples under the
    fallback (opposite-sex terms with the metro's dials), under each
    single component swapped for the same-sex term, and under all three."""
    i = _W["midx"][cbsa]
    A, A_m = _W["A"], _W["A_metro"][i]
    A_minus = np.maximum(A - A_m, 0.0)
    form_os, form_ss = _W["form_os"], _W["form_ss"]
    mc_ss = _W["full_ss"].get(cbsa)
    if mc_ss is None or mc_ss.W <= 0:
        return {"cbsa": cbsa, "sides": 0.0}
    # opposite-sex kernel without the metro's opposite-sex couples
    mc_os = _W["full_os"].get(cbsa)
    C_os = _W["C_os"].copy()
    if mc_os is not None:
        np.add.at(C_os, (mc_os.s, mc_os.c), -mc_os.w)
        C_os[C_os < 0] = 0.0
    F = _W["fit_os"]
    fit_os = fit_form(C_os, A_minus, form_os, bandwidth=F["bandwidth"], tau2=F["tau2"],
                      init={**F["raw_f"], **({"int": F["f"]["int"]} if form_os.interaction else {})},
                      tol=1e-4, max_iter=25, mean_weight=_W["mean_weight_os"])
    fg_os = gauge_form(fit_os["f"], A_minus, fit_os["N_s"], form_os)
    # same-sex kernel without the metro's same-sex couples
    C_ss = _W["C_ss"].copy()
    np.add.at(C_ss, (mc_ss.s, mc_ss.c), -mc_ss.w)
    C_ss[C_ss < 0] = 0.0
    G = _W["fit_ss"]
    fit_ss = fit_form(C_ss, A_minus, form_ss, same_sex=True, bandwidth=G["bandwidth"], init=G["raw_f"],
                      tol=1e-4, max_iter=25, mean_weight=_W["mean_weight_ss"])
    fg_ss = gauge_form(fit_ss["f"], A_minus, fit_ss["N_s"], form_ss, same_sex=True)
    theta = np.array(_W["theta"][i], float)
    d_os, d_ss = design2(form_os), design2(form_ss)

    def loglik(which: dict, interaction: bool | None = None) -> float:
        # log kernel per present seeker over cells, from whichever source
        # each component takes; `interaction` None = m3.2.0's rule (rides
        # only when education and race both stay opposite-sex)
        P = mc_ss.present
        logK = np.zeros((len(P), N_C))
        for j, k in enumerate(COMPONENTS):
            if which[k] == "ss":
                logK += d_ss.gather_one(k, fg_ss[k], P)
            else:
                logK += theta[j] * d_os.gather_one(k, fg_os[k], P)
        if interaction is None:
            interaction = which["edu"] == "os" and which["race"] == "os"
        if fg_os.get("int") is not None and interaction:
            logK += d_os.gather_one("int", fg_os["int"], P)
        logW = logK
        logK = logW + log_avail(A_m, True, P)
        m = logK.max(axis=1, keepdims=True)
        m[~np.isfinite(m)] = 0.0
        logZ = np.log(np.maximum(np.exp(logK - m).sum(axis=1), 1e-300)) + m[:, 0]
        # the couple's own log A(c) is a constant across the kernels compared
        return float((mc_ss.w * (logW[mc_ss.row_pos, mc_ss.c] - logZ[mc_ss.row_pos])).sum())

    fallback = {k: "os" for k in COMPONENTS}
    rec = {"cbsa": cbsa, "sides": mc_ss.W, "fallback": loglik(fallback),
           "all_samesex": loglik({k: "ss" for k in COMPONENTS}),
           "iterations": [fit_os["iterations"], fit_ss["iterations"]]}
    for k in COMPONENTS:
        rec[f"only_{k}"] = loglik({**fallback, k: "ss"})
    # Phase 3c B2: what m3.2.0 serves (age same-sex, education and race
    # opposite-sex, the interaction riding), and the education term added
    # to it with the interaction off (m3.2.0's rule) and forced on
    served = {"age": "ss", "edu": "os", "race": "os"}
    rec["served_m3_2_0"] = loglik(served, interaction=True)
    rec["age_edu_ss_no_interaction"] = loglik({**served, "edu": "ss"}, interaction=False)
    rec["age_edu_ss_with_interaction"] = loglik({**served, "edu": "ss"}, interaction=True)
    return rec


def cmd_samesex(sample: str, workers: int, shipped_form_name: str = "shipped", fit_only: bool = False,
                decide_only: bool = False) -> None:
    """B3 end to end: the same-sex tables (built if missing), the national
    same-sex fit and its report tables, the effective sample per cell and
    the support rule, then the leave-one-metro-out test of each component
    against the opposite-sex fallback the site serves today."""
    from atlas.pipeline.build import pairing
    t0 = time.time()
    P3B.mkdir(parents=True, exist_ok=True)
    if not (DATA / f"couple_table_national_samesex_{sample}.parquet").exists():
        pairing.build_same_sex_tables(sample)
    common = load_common(sample)
    A = common["A"]
    S_os = load_sample(sample)
    S_ss = load_sample(sample, same_sex=True)
    form_ss = Form(name="samesex")
    support = samesex_support(S_ss["nat"])
    r = fit_and_report(sample, form_ss, S_ss, A, same_sex=True)
    report = {"sample": sample, "support": support, "fit": r["record"],
              "couple_sides_weighted": float(S_ss["C"].sum()), "n_alloc": float(S_ss["n_alloc"].sum())}
    np.savez_compressed(P3B / "_samesex_fit.npz", **{f"fg_{k}": v for k, v in r["fg"].items()},
                        **{f"f_{k}": v for k, v in r["fit"]["f"].items()})
    (P3B / "samesex_fit.json").write_text(json.dumps(report, indent=1, default=_json) + "\n")
    print(f"[samesex] support {support['supported']}; fit face {r['record']['face_validity']['pass']}", flush=True)
    if fit_only:
        return
    rep = json.loads((P3B / "refine_fits.json").read_text())
    fits, _ = _load_fits([shipped_form_name])
    fr = rep["forms"][shipped_form_name]["form"]
    form_os = Form(age_edges=tuple(fr["age_edges"]), edu_by_sex=fr["edu_by_sex"],
                   interaction=fr["interaction"], name=shipped_form_name)
    report["fallback_form"] = form_os.describe()
    # LOMO: the metro's dials for the fallback components come from the
    # shipped form's full-sample shrunk dials
    dials = pd.read_csv(P3B / f"dials_{shipped_form_name}.csv", dtype={"cbsa": str}).set_index("cbsa")
    theta = np.stack([dials.loc[common["metro_levels"], f"theta_tilde_{k}"].to_numpy(float)
                      for k in COMPONENTS], axis=1)
    full_os, _ = K.load_metro_tables(sample)
    df = pd.read_parquet(DATA / f"couple_table_metro_samesex_{sample}.parquet")
    df["cbsa"] = df["cbsa"].astype(str)
    full_ss = {c: K.metro_from_table(g) for c, g in df.groupby("cbsa", sort=False)}
    state = {"A": A, "A_metro": common["A_metro"], "midx": {c: i for i, c in enumerate(common["metro_levels"])},
             "form_os": form_os, "form_ss": form_ss, "C_os": S_os["C"], "C_ss": S_ss["C"],
             "full_os": full_os, "full_ss": full_ss, "fit_os": fits[shipped_form_name],
             "fit_ss": {"raw_f": r["fit"]["raw_f"], "bandwidth": r["fit"]["bandwidth"]},
             "mean_weight_os": S_os["mean_weight"], "mean_weight_ss": S_ss["mean_weight"], "theta": theta}
    metros = [c for c in common["metro_levels"] if c in full_ss]
    if decide_only and (P3B / "lomo_samesex.json").exists():
        lomo = json.loads((P3B / "lomo_samesex.json").read_text())
    else:
        print(f"[samesex] LOMO x{len(metros)} with {workers} workers ...", flush=True)
        import multiprocessing as mp
        ctx = mp.get_context("fork")
        with ProcessPoolExecutor(max_workers=workers, mp_context=ctx,
                                 initializer=_init_worker, initargs=(state,)) as ex:
            lomo = list(ex.map(_lomo_samesex_one, metros, chunksize=2))
    lomo = [x for x in lomo if x["sides"] > 0]
    sides = sum(x["sides"] for x in lomo)
    keys = ["fallback", "all_samesex"] + [f"only_{c}" for c in COMPONENTS]
    keys += [k for k in ("served_m3_2_0", "age_edu_ss_no_interaction", "age_edu_ss_with_interaction")
             if all(k in x for x in lomo)]
    tot = {k: sum(x[k] for x in lomo) for k in keys}
    heldout = {"metros": len(lomo), "sides": sides, "totals": tot,
               "gain_per_1000_sides": {k: (v - tot["fallback"]) / sides * 1000 for k, v in tot.items()},
               "metros_better_than_fallback": {k: sum(1 for x in lomo if x[k] > x["fallback"])
                                               for k in tot if k != "fallback"},
               "components": {}}
    # a component is served from same-sex couples when its sample supports
    # it, it predicts held-out same-sex couples better than the fallback,
    # AND its term passes the standing face-validity check (the battery's
    # hard gate reads every served matrix; a same-sex education matrix
    # that is not diagonal-dominant would fail the build)
    face = {"age": bool(r["record"]["face_validity"]["age_pass"]),
            "edu": bool(r["record"]["face_validity"]["edu_pass"]),
            "race": bool(r["record"]["face_validity"]["race_pass"])}
    for k in COMPONENTS:
        improves = tot[f"only_{k}"] > tot["fallback"]
        heldout["components"][k] = {"supported": support["supported"][k], "improves_heldout": bool(improves),
                                    "face_validity_pass": face[k],
                                    "ships": bool(support["supported"][k] and improves and face[k])}
    heldout["served_from_same_sex_couples"] = [k for k in COMPONENTS if heldout["components"][k]["ships"]]
    heldout["fallback_components"] = [k for k in COMPONENTS if not heldout["components"][k]["ships"]]
    if "served_m3_2_0" in tot:
        # Phase 3c B2 (ADR 0010 amended): the education term's gain is
        # re-measured against what m3.2.0 serves, and the interaction is
        # decided by which composition predicts held-out same-sex couples
        # better. Race stays borrowed (its support has not changed).
        base = tot["served_m3_2_0"]
        g_no = (tot["age_edu_ss_no_interaction"] - base) / sides * 1000
        g_int = (tot["age_edu_ss_with_interaction"] - base) / sides * 1000
        use_int = tot["age_edu_ss_with_interaction"] > tot["age_edu_ss_no_interaction"]
        heldout["vs_m3_2_0_served"] = {
            "baseline": "age from same-sex couples, education and race from opposite-sex couples, "
                        "the interaction riding (what m3.2.0 serves)",
            "gain_per_1000_sides": {"age_edu_ss_no_interaction": g_no, "age_edu_ss_with_interaction": g_int},
            "metros_better_than_served": {
                k: sum(1 for x in lomo if x[k] > x["served_m3_2_0"])
                for k in ("age_edu_ss_no_interaction", "age_edu_ss_with_interaction")},
            "education_term_improves_on_served": bool(max(g_no, g_int) > 0)}
        heldout["interaction_decision"] = {
            "rule": "serve whichever of {interaction off, interaction on} predicts held-out same-sex "
                    "couples better, education and age from same-sex couples, race borrowed",
            "interaction_applies": bool(use_int),
            "margin_per_1000_sides": (tot["age_edu_ss_with_interaction"] - tot["age_edu_ss_no_interaction"])
            / sides * 1000}
        heldout["interaction_applies"] = bool(use_int)
        heldout["stop_condition_education_no_longer_improves"] = not heldout["vs_m3_2_0_served"][
            "education_term_improves_on_served"]
    report["heldout"] = heldout
    report["seconds"] = round(time.time() - t0, 1)
    (P3B / "lomo_samesex.json").write_text(json.dumps(lomo, indent=0, default=_json) + "\n")
    (P3B / "samesex_fit.json").write_text(json.dumps(report, indent=1, default=_json) + "\n")
    print(json.dumps({"gain_per_1000_sides": heldout["gain_per_1000_sides"],
                      "components": heldout["components"], "seconds": report["seconds"]}, indent=1))


if __name__ == "__main__":
    argv = sys.argv[1:]
    sample = argv[argv.index("--sample") + 1] if "--sample" in argv else "decay_h5"
    workers = int(argv[argv.index("--workers") + 1]) if "--workers" in argv else 8
    if "--dir" in argv:
        P3B = Path(argv[argv.index("--dir") + 1])
        assert (P3B / "refine_fits.json").exists(), f"seed {P3B} with the Phase 3b records first"
    if argv[:1] == ["check"]:
        cmd_check(sample)
    elif argv[:1] == ["fit"]:
        cmd_fit(sample, argv[argv.index("--only") + 1].split(",") if "--only" in argv else None)
    elif argv[:1] == ["lomo"]:
        only = argv[argv.index("--only") + 1].split(",") if "--only" in argv else None
        cmd_lomo(sample, workers, only)
    elif argv[:1] == ["samesex"]:
        cmd_samesex(sample, workers, argv[argv.index("--form") + 1] if "--form" in argv else "shipped",
                    fit_only="--fit-only" in argv, decide_only="--decide-only" in argv)
    elif argv[:1] == ["combine"]:
        cmd_combine(sample, argv[argv.index("--only") + 1].split(",") if "--only" in argv else None,
                    argv[argv.index("--reason") + 1] if "--reason" in argv else None)
    elif argv[:1] == ["candidate"]:
        cmd_candidate(sample, argv[argv.index("--form") + 1], Path(argv[argv.index("--out") + 1]))
    elif argv[:1] == ["ship"]:
        cmd_ship(sample, Path(argv[argv.index("--out") + 1]) if "--out" in argv else None,
                 argv[argv.index("--form") + 1] if "--form" in argv else "shipped")
    else:
        print(__doc__)
