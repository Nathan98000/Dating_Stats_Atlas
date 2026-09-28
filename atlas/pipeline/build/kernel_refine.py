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
gauge, dials, shrinkage, split-half test and intermarriage comparison as
kernel.py (whose data loading, metro tables, shrinkage and comparison code are reused as
they are). The two-way term is estimated by penalised coordinate ascent:
the main effects take exact IPF steps, the interaction takes a Newton step
on the ridge-penalised Poisson objective per cell, in weight units with
the penalty scaled by the mean weight per side so tau^2 is on the scale of
one allocated couple-side. Artifact version kernel_v2 (loader.py reads v1
and v2).

    python -m atlas.pipeline.build.kernel_refine check
    python -m atlas.pipeline.build.kernel_refine fit  [--sample decay_h5]
    python -m atlas.pipeline.build.kernel_refine lomo [--workers 8]
    python -m atlas.pipeline.build.kernel_refine samesex [--workers 8] [--race-free] [--form <name>]
    python -m atlas.pipeline.build.kernel_refine ship
    python -m atlas.pipeline.build.kernel_refine ship_v3 --served <build_dir> [--out <dir>]

Phase 4 (m4.0.0, ADR 0018): `lomo --only C1_cohorts_plus_shipped,
D0_race_free,C1_race_zeroed` fits the race-free form (D0: the cohort age
term and the education matrix, refitted with no race component and no
interaction) beside C1 and C1 with its race terms set to zero;
`samesex --race-free` refits the same-sex terms with no race; `ship_v3`
writes the kernel_v3 artifact — C1 copied from the served build byte for
byte (race on), D0 with its dials (race off), the same-sex form (no race,
no interaction, no dial) — which loader.py reads beside v1 and v2.

Phase 3d R (ADR 0014): every held-out comparison goes through `beats` and
`select_form` — a difference smaller than HELDOUT_TIE_MARGIN_PER_1000 per
1,000 weighted couple-sides is a tie, and a tie goes to the simpler form.
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
    education two-way term is present.

    Phase 4 (ADR 0018): `race` False is the race-free form — no race
    component at all and no interaction, refitted by the same machinery
    with the race term held at zero and no race dial. `zero_race` is the
    comparison ADR 0018 asks for, never served: the form fitted as it is,
    then its race term and interaction set to zero (what a race-free
    kernel would be without the refit)."""
    age_edges: tuple[int, ...] = ()
    edu_by_sex: bool = False
    interaction: bool = False
    name: str = "baseline"
    race: bool = True
    zero_race: bool = False

    def __post_init__(self) -> None:
        assert self.race or not self.interaction, "a race-free form carries no interaction"
        assert not (self.zero_race and not self.race), "zero_race zeroes a fitted race term"

    @property
    def has_race(self) -> bool:
        """Whether the served kernel of this form carries a race term."""
        return self.race and not self.zero_race

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
        out = {"name": self.name, "age_edges": list(self.age_edges),
               "age_cohorts": self.cohort_labels(), "edu_by_sex": self.edu_by_sex,
               "interaction": self.interaction}
        if not self.race or self.zero_race:
            out.update({"race": self.race, "zero_race": self.zero_race})
        return out


def form_from_record(fr: dict, name: str) -> Form:
    """A Form from its describe() record (race and zero_race default to the
    forms fitted before Phase 4)."""
    return Form(age_edges=tuple(fr["age_edges"]), edu_by_sex=fr["edu_by_sex"],
                interaction=fr["interaction"], name=name, race=fr.get("race", True),
                zero_race=fr.get("zero_race", False))


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


# ---------------------------------------------------------------------------
# Phase 3d A1: the sweep keeps the model table between component updates
# ---------------------------------------------------------------------------

STOP_RULE = "couples"
# Couple-weighted stopping (Phase 3d A1, item 2): a stage stops when the
# share of fitted couple-sides that moved between cells over one pass —
# sum |mu_after - mu_before| / sum N_s — falls below COUPLE_TOL, one side
# in ten million. m3.3.0 stopped on the largest single-cell change, which
# a near-empty cell held above 1e-6 for the whole 200-pass cap while the
# table itself had stopped moving at pass 7 (results/phase3d/speedup/
# a1_trajectories.json). The raw stage only seeds the smoothing and may
# stop looser; the trajectories showed no need (7 passes at 1e-7 against
# 6 at 1e-5) and the bandwidth choice is shown not to depend on it, so it
# keeps the same tolerance. The interaction stage also waits for the
# penalised objective's gain over the pass, per 1,000 couple-sides, to
# fall below OBJECTIVE_TOL: the directions of the interaction the table
# cannot see move under the ridge alone (A2's projection removes them).
COUPLE_TOL = 1e-7
RAW_COUPLE_TOL = 1e-7
OBJECTIVE_TOL = 1e-6
# Phase 3d A2: after each Newton step on the interaction, the parts of g
# the penalised objective cannot see are taken out: the seeker-only part
# (a per-seeker constant, dropped — the row normalisation absorbs it and
# the ridge wants it at zero) and the education-pair and race-pair parts
# (moved into the main effects, where an unpenalised optimum puts them).
# Without the projection those directions decay under the ridge alone at
# under 1% per pass, which is why m3.3.0's interaction stage stopped at
# its 200-pass cap. Off reproduces the A1 fit to 1e-9.
PROJECT_INTERACTION = True
# Phase 3d R (ADR 0014): a held-out difference smaller than this, per 1,000
# weighted couple-sides of the set scored, is a tie, and a tie goes to the
# simpler form. Written after the A2 flip was seen (C3 over C1 by 0.007
# where Phase 3c read C1 ahead by 0.001); its anchors are in the ADR and
# results/phase3d/tie_rule.json: about four times the largest margin the
# finished fit moved with the same forms and data (0.066), about 17 times
# the paired, metro-clustered standard error of the C3 - C1 difference
# (0.014), about a twelfth of the smallest margin that has decided a
# served term (+2.90). It changes only by a new ADR, written before the
# comparison it would decide is measured. Applies to held-out likelihood
# comparisons of kernel forms (opposite- and same-sex), not to the ADR
# 0011 stability gate nor to Part B's wobble-based selection (ADR 0013).
HELDOUT_TIE_MARGIN_PER_1000 = 0.25
HELDOUT_TIE_ADR = "0014"


class Projection:
    """The interaction's blind directions for a Form, built once: the 2,048
    cells (sex, seeker race, partner race, seeker education, partner
    education) against indicator columns for the seeker type (sex, seeker
    race, seeker education: 64), the education pair as the form's
    education main effect keys it (16 pooled, 32 per sex) and the race
    pair per sex (128). An orthonormal basis of their span by SVD (the
    columns overlap, so the rank is below the count) and the minimum-norm
    coefficients that write the projection back onto the three blocks."""

    def __init__(self, form: Form) -> None:
        sig, rs, rc, es, ec = np.indices((N_SEX, N_RACE, N_RACE, N_EDU, N_EDU)).reshape(5, -1)
        self.form = form
        self.seek_key = (sig * N_RACE + rs) * N_EDU + es
        n_seek = N_SEX * N_RACE * N_EDU
        if form.edu_by_sex:
            edu_key = (sig * N_EDU + es) * N_EDU + ec
            n_edu = N_SEX * N_EDU * N_EDU
        else:
            edu_key = es * N_EDU + ec
            n_edu = N_EDU * N_EDU
        race_key = (sig * N_RACE + rs) * N_RACE + rc
        n_race = N_SEX * N_RACE * N_RACE
        n = len(sig)
        X = np.zeros((n, n_seek + n_edu + n_race))
        X[np.arange(n), self.seek_key] = 1.0
        X[np.arange(n), n_seek + edu_key] = 1.0
        X[np.arange(n), n_seek + n_edu + race_key] = 1.0
        U, sv, Vt = np.linalg.svd(X, full_matrices=False)
        keep = sv > 1e-10 * sv[0]
        self.columns = int(X.shape[1])
        self.rank = int(keep.sum())
        self.Q = U[:, keep]                                          # orthonormal basis of the span
        self.pinv = (Vt[keep].T / sv[keep]) @ U[:, keep].T           # minimum-norm coefficients
        self.blocks = (n_seek, n_edu, n_race)
        self.edu_shape = (N_SEX, N_EDU, N_EDU) if form.edu_by_sex else (N_EDU, N_EDU)

    def split(self, g_flat: np.ndarray) -> tuple[np.ndarray, np.ndarray, np.ndarray, np.ndarray]:
        """(the residual g - Pg; the seeker-only, education-pair and race-
        pair coefficients whose indicator sums equal Pg)."""
        Pg = self.Q @ (self.Q.T @ g_flat)
        beta = self.pinv @ Pg
        n_seek, n_edu, n_race = self.blocks
        return (g_flat - Pg, beta[:n_seek].reshape(N_SEX, N_RACE, N_EDU),
                beta[n_seek:n_seek + n_edu].reshape(self.edu_shape),
                beta[n_seek + n_edu:].reshape(N_SEX, N_RACE, N_RACE))


_PROJECTIONS: dict[Form, Projection] = {}


def projection(form: Form) -> Projection:
    if form not in _PROJECTIONS:
        _PROJECTIONS[form] = Projection(form)
    return _PROJECTIONS[form]


# ---------------------------------------------------------------------------
# ADR 0014: held-out comparisons — a margin, and the simpler form on a tie
# ---------------------------------------------------------------------------

def beats(gain_per_1000: float, margin: float = HELDOUT_TIE_MARGIN_PER_1000) -> bool:
    """ADR 0014 §1-2. Form A beats form B on held-out fit only if A's total
    held-out log-likelihood exceeds B's by at least `margin` per 1,000
    weighted couple-sides of the set scored (`gain_per_1000` is that
    difference, A minus B; the held-out measure is the usual one — leave
    one metro out, shrunk dials). Anything less, in either direction, is
    a tie. Wherever a rule requires a candidate to improve on a reference
    it must beat it in this sense, and a yes/no choice (whether a term
    ships, whether the interaction rides) takes the richer option only if
    it beats the simpler one (§4): a tie keeps the simpler one."""
    return bool(gain_per_1000 >= margin)


def nested_in(a: Form, b: Form) -> bool:
    """Whether form `a` is nested in form `b` — b only adds terms: every
    cohort boundary of a is one of b's (a's cohorts are unions of b's),
    the education matrix is per sex only if b's is, the interaction is
    present only if b has it. A form is nested in itself."""
    return bool(set(a.age_edges) <= set(b.age_edges) and a.edu_by_sex <= b.edu_by_sex
                and a.interaction <= b.interaction)


def free_parameters(form: Form) -> dict:
    """The kernel's free parameters under a Form, as the fit estimates
    them: each main effect's log-multiplier cells less one gauge per row
    (the availability-weighted mean multiplier is 1 on every row's own
    margin), and the interaction's 2,048 cells less the directions the fit
    projects out after every Newton step (Projection.rank: the seeker-only
    part and the education-pair and race-pair parts, which the main
    effects carry). With the interaction present the per-sex education
    matrix therefore adds no free direction to the kernel — it moves
    twelve directions out from under the ridge — so C2 counts the same as
    the shipped form and C3 the same as C1; nesting, which select_form
    checks first, is what separates those pairs. Builds the projection
    (an SVD): call it in the parent process, never in a forked worker."""
    age = N_SEX * form.n_cohorts * (N_GAP - 1)
    edu = (N_SEX if form.edu_by_sex else 1) * N_EDU * (N_EDU - 1)
    race = N_SEX * N_RACE * (N_RACE - 1)
    out = {"age": age, "edu": edu, "race": race,
           "interaction_cells": N_INT if form.interaction else 0,
           "interaction_projected_out": projection(form).rank if form.interaction else 0}
    out["interaction"] = out["interaction_cells"] - out["interaction_projected_out"]
    out["unpenalised"] = age + edu + race
    out["total"] = out["unpenalised"] + out["interaction"]
    return out


def select_form(candidates: dict[str, dict], *, served: str | None = None,
                margin: float = HELDOUT_TIE_MARGIN_PER_1000) -> dict:
    """ADR 0014 §3 — choosing among candidates measured against one
    reference. `candidates` maps each name, in the brief's table order, to
    {"form": Form, "gain_per_1000": its held-out gain over the reference,
    "qualifies": whether its other conditions hold (the gate, support, the
    face check; default True), "gate_ratio": the ADR 0011 ratio or None}.
    A candidate qualifies only if it also beats the reference (§2). Take
    the largest gain among the qualifying candidates; every qualifying
    candidate within `margin` of it is tied for first; of those the
    simplest ships — a tied form in which another tied form is nested is
    dropped, and if one form remains it ships; otherwise the fewest free
    parameters; if that does not settle it, in order: the lower gate
    ratio, the form already served (`served`), the earlier form in the
    table. Returns the record: the winner, how it was settled, the
    qualifying and tied sets and every candidate's reading."""
    order = list(candidates)
    forms = {n: c["form"] for n, c in candidates.items()}
    reading = {}
    for n, c in candidates.items():
        r = {"gain_per_1000": float(c["gain_per_1000"]),
             "beats_reference": beats(c["gain_per_1000"], margin),
             "other_conditions": bool(c.get("qualifies", True)),
             "gate_ratio": c.get("gate_ratio"),
             "free_parameters": free_parameters(c["form"])["total"],
             "tied_for_first": False, "tied_forms_nested_in_it": []}
        r["qualifies"] = bool(r["beats_reference"] and r["other_conditions"])
        reading[n] = r
    qualifying = [n for n in order if reading[n]["qualifies"]]
    out = {"adr": HELDOUT_TIE_ADR, "margin_per_1000": margin, "candidates": reading,
           "qualifying": qualifying, "largest_gain": None, "tied_for_first": [],
           "winner": None, "settled_by": None}
    if not qualifying:
        out["settled_by"] = "no candidate qualifies"
        return out
    largest = max(qualifying, key=lambda n: reading[n]["gain_per_1000"])
    best = reading[largest]["gain_per_1000"]
    tied = [n for n in qualifying if best - reading[n]["gain_per_1000"] < margin]
    for n in tied:
        reading[n]["tied_for_first"] = True
    out["largest_gain"], out["tied_for_first"] = largest, tied
    if len(tied) == 1:
        out["winner"], out["settled_by"] = tied[0], "the largest gain beats every other qualifying candidate"
        return out
    # nesting first: a tied form in which another tied form is nested only adds terms
    for n in tied:
        reading[n]["tied_forms_nested_in_it"] = [
            o for o in tied if o != n and nested_in(forms[o], forms[n]) and not nested_in(forms[n], forms[o])]
    remaining = [n for n in tied if not reading[n]["tied_forms_nested_in_it"]]
    if len(remaining) == 1:
        out["winner"], out["settled_by"] = remaining[0], "nesting: the other tied forms only add terms to it"
        return out
    # then the fewest free parameters in the kernel
    fewest = min(reading[n]["free_parameters"] for n in remaining)
    remaining = [n for n in remaining if reading[n]["free_parameters"] == fewest]
    if len(remaining) == 1:
        out["winner"], out["settled_by"] = remaining[0], "fewer free parameters in the kernel"
        return out
    # then the lower ADR 0011 gate ratio
    ratios = [reading[n]["gate_ratio"] for n in remaining]
    if all(r is not None for r in ratios):
        lowest = min(ratios)
        remaining = [n for n in remaining if reading[n]["gate_ratio"] == lowest]
        if len(remaining) == 1:
            out["winner"], out["settled_by"] = remaining[0], "the lower ADR 0011 gate ratio"
            return out
    # then the form already served, then the earlier form in the table
    if served in remaining:
        out["winner"], out["settled_by"] = served, "the form already served"
    else:
        out["winner"], out["settled_by"] = remaining[0], "the earlier form in the brief's table"
    return out


class Table:
    """The model couple table mu (seekers x partner cells, rows summing to
    N_s), kept between component updates and moved MULTIPLICATIVELY: a
    component's change is a per-seeker factor over the partner axes it
    keys on, applied on the (seeker, partner age, edu, race) view of the
    table, after which the rows are re-normalised — instead of regathering
    the four log-kernel blocks and exponentiating the whole 3,392 x 1,696
    table at every step. Margins are reshape-sums over the seven-axis view
    (seeker sex, age, edu, race; partner age, edu, race) instead of
    bincounts over 5.75 million keys. log Z per seeker rides along so the
    conditional log-likelihood is available at every pass."""

    def __init__(self, d: Design2, logA: np.ndarray, N_s: np.ndarray) -> None:
        b = d.base
        self.d, self.logA, self.N_s = d, logA, N_s
        self.sig, self.e_s, self.r_s = b.sig_s, b.e_s, b.r_s
        self.gap53 = (np.arange(N_AGE)[None, :] - b.a_s[:, None]) + GAP0        # (S, 53)
        self.row_age = d.row_age
        sig3 = np.repeat(np.arange(N_SEX), N_AGE * N_AGE)
        as3 = np.tile(np.repeat(np.arange(N_AGE), N_AGE), N_SEX)
        ac3 = np.tile(np.arange(N_AGE), N_SEX * N_AGE)
        self.key_age3 = (sig3 * d.K + d.cohort_of_age[as3]) * N_GAP + (ac3 - as3 + GAP0)
        self.n_age = N_SEX * d.K * N_GAP
        self.Ntot = float(N_s.sum())
        self.mu = None
        self.logZ = None
        self.zok = None
        self.seconds = {"rebuild": 0.0, "apply": 0.0, "margin": 0.0, "update": 0.0,
                        "objective": 0.0, "move": 0.0}

    def rebuild(self, f: dict) -> None:
        t0 = time.perf_counter()
        lm = self.d.gather(f) + self.logA
        m = lm.max(axis=1, keepdims=True)
        m[~np.isfinite(m)] = 0.0
        mu = np.exp(lm - m)
        Z = mu.sum(axis=1)
        self.zok = Z > 0
        self.logZ = np.where(self.zok, np.log(np.maximum(Z, 1e-300)) + m[:, 0], 0.0)
        with np.errstate(invalid="ignore", divide="ignore"):
            scale = np.where(self.zok, self.N_s / np.maximum(Z, 1e-300), 0.0)
        mu *= scale[:, None]
        self.mu = mu
        self.seconds["rebuild"] += time.perf_counter() - t0

    def apply(self, comp: str, delta: np.ndarray) -> None:
        """mu <- mu * exp(delta gathered), rows re-normalised to N_s."""
        t0 = time.perf_counter()
        mu4 = self.mu.reshape(N_S, N_AGE, N_EDU, N_RACE)
        g = np.exp(delta)
        if comp == "age":
            G = np.take_along_axis(g.reshape(N_SEX * self.d.K, N_GAP)[self.row_age], self.gap53, axis=1)
            mu4 *= G[:, :, None, None]
        elif comp == "edu":
            G = g[self.sig, self.e_s] if self.d.form.edu_by_sex else g[self.e_s]
            mu4 *= G[:, None, :, None]
        elif comp == "race":
            mu4 *= g[self.sig, self.r_s][:, None, None, :]
        elif comp == "int":
            mu4 *= g[self.sig, self.r_s, :, self.e_s, :].transpose(0, 2, 1)[:, None, :, :]
        else:
            raise KeyError(comp)
        Z = self.mu.sum(axis=1)
        ok = self.zok & (Z > 0)
        with np.errstate(invalid="ignore", divide="ignore"):
            self.logZ = np.where(ok, self.logZ + np.log(np.maximum(Z, 1e-300) / np.maximum(self.N_s, 1e-300)), self.logZ)
            scale = np.where(ok, self.N_s / np.maximum(Z, 1e-300), 0.0)
        self.mu *= scale[:, None]
        self.seconds["apply"] += time.perf_counter() - t0

    def margin(self, comp: str) -> np.ndarray:
        t0 = time.perf_counter()
        mu7 = self.mu.reshape(N_SEX, N_AGE, N_EDU, N_RACE, N_AGE, N_EDU, N_RACE)
        if comp == "age":
            out = np.bincount(self.key_age3, mu7.sum(axis=(2, 3, 5, 6)).ravel(), self.n_age)
        elif comp == "edu":
            out = (mu7.sum(axis=(1, 3, 4, 6)) if self.d.form.edu_by_sex else mu7.sum(axis=(0, 1, 3, 4, 6))).ravel()
        elif comp == "race":
            out = mu7.sum(axis=(1, 2, 4, 5)).ravel()
        elif comp == "int":
            out = mu7.sum(axis=(1, 4)).transpose(0, 2, 4, 1, 3).ravel()
        else:
            raise KeyError(comp)
        self.seconds["margin"] += time.perf_counter() - t0
        return out

    def objective(self, f: dict, T: dict, lam: float) -> float:
        """The penalised conditional log-likelihood in weight units, up to
        the constant sum C log A: sum over every component of T . f, minus
        sum_s N_s log Z_s, minus lam/2 sum g^2 (weight units, as the
        Newton step's penalty)."""
        t0 = time.perf_counter()
        ll = 0.0
        for k, v in f.items():
            if v is None:
                continue
            ll += float(T[k] @ v.ravel())
        if f.get("int") is not None and np.isfinite(lam):
            ll -= 0.5 * lam * float((f["int"] ** 2).sum())
        ll -= float((self.N_s * self.logZ)[self.zok].sum())
        self.seconds["objective"] += time.perf_counter() - t0
        return ll


def _objective_of(f: dict, T: dict, logA: np.ndarray, N_s: np.ndarray, lam: float, d: Design2) -> float:
    """The same objective from scratch (a fresh table), for the record."""
    tab = Table(d, logA, N_s)
    tab.rebuild(f)
    return tab.objective(f, T, lam)


def fit_form(C: np.ndarray, A: np.ndarray, form: Form, *, same_sex: bool = False,
             bandwidth: list[float] | None = None, tau2: float | None = None,
             init: dict | None = None, tol: float = K.IPF_TOL, max_iter: int = K.IPF_MAX_ITER,
             mean_weight: float | None = None, skip: tuple[str, ...] = (),
             stop: str = STOP_RULE, ctol: float = COUPLE_TOL, raw_ctol: float = RAW_COUPLE_TOL,
             otol: float = OBJECTIVE_TOL, project: bool = PROJECT_INTERACTION) -> dict:
    """The two-stage fit for any Form: raw IPF of the main effects to
    convergence, bandwidth per (sex, cohort) by leave-one-gap-out
    cross-validation (unless given), the age term smoothed once and the
    other main effects refitted around it; then, if the form carries the
    interaction, tau^2 by empirical Bayes at the separable fit (unless
    given) and penalised coordinate ascent over (edu, race, int) with the
    age term fixed. `skip` holds a main effect at zero (sensitivity).

    Phase 3d A1: the sweep moves one model table in place (Table) instead
    of regathering the log-kernel at every step, and stops on a rule
    chosen by `stop`: "cell" is m3.3.0's (the largest single-cell change
    below `tol`, the table returned as it stood before the pass's last
    update), "couples" stops a stage when fewer than `ctol` of the fitted
    couple-sides moved over a pass (`raw_ctol` for the raw stage, which
    only seeds the smoothing; the interaction stage also waits for the
    penalised objective's gain per pass, per 1,000 sides, to fall below
    `otol`). Every pass's largest cell change, couple-weighted move and
    objective are on the record. Phase 3d A2: with `project` the
    interaction's seeker-only part is dropped and its pair-shaped parts
    are moved into the education and race main effects after every Newton
    step (Projection); the cells the step forces to zero stay zero."""
    assert stop in ("cell", "couples"), stop
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
    if not form.race:
        skip = tuple(skip) + ("race",)       # Phase 4: the race-free form
    for k in skip:
        f[k] = np.zeros(d.shapes()[k])
    mains = [k for k in COMPONENTS if k not in skip]
    tab = Table(d, logA, N_s)
    per_1000 = 1000.0 / max(tab.Ntot, 1e-300)
    profile = {"stages": {}, "table_seconds": tab.seconds}
    proj = projection(form) if (project and form.interaction) else None
    moved = {"edu": None, "race": None, "seeker_dropped_max_abs": 0.0, "passes": 0}

    def run_ipf(stage: str, active: list[str], with_int: bool, tau2_: float | None,
                tol_: float, max_iter_: int, ctol_: float) -> tuple[dict, np.ndarray]:
        t_stage = time.perf_counter()
        hist = {"cell_change": [], "couple_move": [], "objective": []}
        lam = (mw / tau2_ if tau2_ > 0 else np.inf) if with_int else np.inf
        tab.rebuild(f)
        last = None                      # (component, its value before the pass's last update)
        stopped_on = "cap"
        for _ in range(max_iter_):
            worst = 0.0
            t0 = time.perf_counter()
            mu_start = tab.mu.copy()
            tab.seconds["move"] += time.perf_counter() - t0
            for comp in active:
                M = tab.margin(comp)
                t0 = time.perf_counter()
                new, ch = K._raw_update(f[comp].ravel(), T[comp], M)
                new = new.reshape(d.shapes()[comp])
                delta = new - f[comp]
                last = (comp, f[comp])
                f[comp] = new
                tab.seconds["update"] += time.perf_counter() - t0
                tab.apply(comp, delta)
                worst = max(worst, ch)
            if with_int:
                M = tab.margin("int")
                t0 = time.perf_counter()
                Ti = T["int"]
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
                new = g.reshape(d.shapes()["int"])
                delta = new - f["int"]
                last = ("int", f["int"])
                f["int"] = new
                tab.seconds["update"] += time.perf_counter() - t0
                tab.apply("int", delta)
                worst = max(worst, ch)
                if proj is not None and np.isfinite(lam):
                    # A2: take the blind directions out of g. The table
                    # does not move (the seeker-only part is a per-row
                    # constant; the pair parts go into the main effects
                    # exactly), only log Z carries the dropped constant.
                    t0 = time.perf_counter()
                    resid, b_seek, b_edu, b_race = proj.split(f["int"].ravel())
                    resid[M <= 0] = 0.0
                    f["int"] = resid.reshape(d.shapes()["int"])
                    f["edu"] = f["edu"] + b_edu
                    f["race"] = f["race"] + b_race
                    row_const = b_seek[tab.sig, tab.r_s, tab.e_s]
                    tab.logZ = np.where(tab.zok, tab.logZ - row_const, tab.logZ)
                    moved["edu"] = b_edu if moved["edu"] is None else moved["edu"] + b_edu
                    moved["race"] = b_race if moved["race"] is None else moved["race"] + b_race
                    moved["seeker_dropped_max_abs"] = max(moved["seeker_dropped_max_abs"], float(np.abs(b_seek).max()))
                    moved["passes"] += 1
                    tab.seconds["update"] += time.perf_counter() - t0
            hist["cell_change"].append(worst)
            obj = tab.objective(f, T, lam)
            gain = (obj - hist["objective"][-1]) * per_1000 if hist["objective"] else np.inf
            hist["objective"].append(obj)
            t0 = time.perf_counter()
            move = float(np.abs(tab.mu - mu_start).sum()) / max(tab.Ntot, 1e-300)
            tab.seconds["move"] += time.perf_counter() - t0
            hist["couple_move"].append(move)
            if stop == "couples":
                if move < ctol_ and (not with_int or abs(gain) < otol):
                    stopped_on = "tolerance"
                    break
            elif worst < tol_:
                stopped_on = "tolerance"
                break
        if stop == "cell" and last is not None:
            # m3.3.0 handed the next stage the table as it stood before the
            # pass's last update; reproduced exactly under the old rule
            mu = K._mu(d.gather({**f, last[0]: last[1]}), logA, N_s)
        else:
            mu = tab.mu.copy()
        hist["stopped_on"] = stopped_on
        hist["passes"] = len(hist["cell_change"])
        profile["stages"][stage] = {"seconds": round(time.perf_counter() - t_stage, 3),
                                    "passes": hist["passes"], "stopped_on": stopped_on}
        return hist, mu

    # stage 1: raw IPF of the main effects (interaction at zero)
    f_int_saved = f.pop("int", None)
    hist_raw, mu = run_ipf("raw", mains, False, None, tol, max_iter, raw_ctol)
    raw_f = {k: v.copy() for k, v in f.items()}
    raw_M = d.margins(mu)
    # stage 2: bandwidth per (sex, cohort), smooth, refit around the fixed age term
    rows = N_SEX * d.K
    cv = None
    t_sm = time.perf_counter()
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
        profile["stages"]["smoothing"] = {"seconds": round(time.perf_counter() - t_sm, 3),
                                          "bandwidth_cv": bandwidth is None}
        hist_sm, mu = run_ipf("smoothed", [k for k in mains if k != "age"], False, None, tol, max_iter, ctol)
    else:
        h = None
        hist_sm = {"cell_change": [], "couple_move": [], "objective": [], "passes": 0, "stopped_on": None}
    # stage 3: the interaction, penalised, with the age term fixed
    prior = None
    hist_int = {"cell_change": [], "couple_move": [], "objective": [], "passes": 0, "stopped_on": None}
    if form.interaction:
        sep_M = d.margins(mu)
        if tau2 is None:
            prior = interaction_prior(T["int"], sep_M["int"], mw)
            tau2 = prior["tau2"]
        else:
            prior = {"tau2": tau2, "given": True}
        f["int"] = f_int_saved if f_int_saved is not None else np.zeros(d.shapes()["int"])
        hist_int, mu = run_ipf("interaction", [k for k in mains if k != "age"], True, tau2,
                               tol, INT_MAX_ITER if max_iter >= K.IPF_MAX_ITER else max_iter, ctol)
    profile["seconds_total"] = round(sum(v["seconds"] for v in profile["stages"].values()), 3)
    if form.zero_race:
        # Phase 4 (ADR 0018): the comparison form, never served — fitted as
        # it is, then its race term and interaction set to zero
        f["race"] = np.zeros(d.shapes()["race"])
        f.pop("int", None)
    cell_hist = hist_raw["cell_change"] + hist_sm["cell_change"] + hist_int["cell_change"]
    move_hist = hist_raw["couple_move"] + hist_sm["couple_move"] + hist_int["couple_move"]
    last_hist = hist_int if form.interaction else hist_sm if "age" in mains else hist_raw
    lam_final = (mw / tau2 if (form.interaction and tau2 and tau2 > 0) else np.inf)
    if stop == "cell":
        converged = bool(cell_hist and cell_hist[-1] < tol)
    else:
        converged = bool(last_hist["stopped_on"] == "tolerance")
    return {"f": f, "raw_f": raw_f, "mu": mu, "T": T, "M": d.margins(mu), "N_s": N_s,
            "bandwidth": (None if h is None else [float(x) for x in h]), "bandwidth_cv": cv,
            "tau2": tau2, "interaction_prior": prior,
            "raw_iterations": hist_raw["passes"], "smoothed_iterations": hist_sm["passes"],
            "interaction_iterations": hist_int["passes"],
            "iterations": len(cell_hist),
            "converged": converged,
            "final_change": cell_hist[-1] if cell_hist else 0.0,
            "final_move": move_hist[-1] if move_hist else None,
            "stop_rule": stop,
            "tolerances": ({"tol": tol} if stop == "cell" else {"ctol": ctol, "raw_ctol": raw_ctol, "otol": otol}),
            "history": {"raw": hist_raw, "smoothed": hist_sm, "interaction": hist_int},
            "objective": (last_hist["objective"][-1] if last_hist["objective"] else None),
            "objective_from_scratch": _objective_of(f, T, logA, N_s, lam_final, d),
            "couple_sides": tab.Ntot,
            "profile": profile,
            "projection": (None if proj is None else {
                "applied": True, "columns": proj.columns, "rank": proj.rank, "passes": moved["passes"],
                "moved_to_edu_max_abs": float(np.abs(moved["edu"]).max()) if moved["edu"] is not None else 0.0,
                "moved_to_race_max_abs": float(np.abs(moved["race"]).max()) if moved["race"] is not None else 0.0,
                "seeker_only_dropped_max_abs": moved["seeker_dropped_max_abs"],
                "residual_norm2": float((f["int"] ** 2).sum()) if f.get("int") is not None else 0.0}),
            "form": form, "same_sex": same_sex}


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
    free = np.array([k in comps and (k != "race" or form.has_race) for k in COMPONENTS])
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
    if not form.has_race:
        # Phase 4 (ADR 0018): no race term to check; the race checks read a
        # zero term and are dropped, the form is held to age and education
        for key in [k for k in out if k.startswith("race")]:
            out.pop(key)
        out["race_pass"] = None
        out["race_rule"] = "no race term (race-free form)"
        out["pass"] = out["age_pass"] and out["edu_pass"]
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
                                         name="C3_both_plus_shipped"),
            # Phase 4 (ADR 0018): the race-free default form — the cohort
            # age term and the education matrix, no race component, no
            # interaction, refitted — and, for the record only, C1 with its
            # race term and interaction zeroed after the fit
            "D0_race_free": Form(age_edges=partition_edges, race=False, name="D0_race_free"),
            "C1_race_zeroed": Form(age_edges=partition_edges, interaction=True, zero_race=True,
                                   name="C1_race_zeroed")}


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
                   "final_change": fit["final_change"],
                   # Phase 3d A1: the rule the stages stopped on, the last
                   # pass's couple-weighted move, the penalised objective
                   # (weight units, up to the constant sum C log A) and
                   # where the seconds went
                   "stop_rule": fit["stop_rule"], "tolerances": fit["tolerances"],
                   "stopped_on": {k: fit["history"][k]["stopped_on"] for k in ("raw", "smoothed", "interaction")},
                   "final_move": fit["final_move"], "objective": fit["objective_from_scratch"],
                   "couple_sides": fit["couple_sides"], "profile": fit["profile"]},
           "bandwidth_by_sex_cohort": {f"{SEX_LEVELS[i // d.K]}:{form.cohort_labels()[i % d.K]}": fit["bandwidth"][i]
                                       for i in range(N_SEX * d.K)},
           "face_validity": face_validity(fg, A, form, same_sex),
           "separability": K.separability(S["C"], fit["mu"], S["mean_weight"]),
           "seconds": round(time.time() - t0, 1)}
    if form.age_edges:
        rec["cohort_sample"] = cohort_sample(S["nat"], form)
    if form.interaction and not form.zero_race:
        rec["interaction_prior"] = fit["interaction_prior"]
        rec["interaction_projection"] = fit["projection"]
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
    plus the out-group predictions the intermarriage check reads (ADR 0016)."""
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
        # Phase 3d A1 (item 3): warm-started from the full fit's smoothed-
        # stage terms (age smoothed, education and race refitted around it,
        # the interaction) and stopped on the couple-weighted rule; the
        # 25-sweep cap that every interaction form hit in Phase 3c is gone
        fit = fit_form(C_minus, A_minus, form, bandwidth=F["bandwidth"], tau2=F["tau2"],
                       init={**F["f"]}, max_iter=K.IPF_MAX_ITER, mean_weight=_W["mean_weight"])
        f_m = gauge_form(fit["f"], A_minus, fit["N_s"], form)
        shs = [K.shrink(_W["theta_hat"][name][others, k], _W["se2"][name][others, k]) for k in range(3)]
        rec = {"iterations": fit["iterations"], "national": 0.0, "shrunk": 0.0, "raw": 0.0, "sides": 0.0,
               "national_all": 0.0,
               "stages": {k: {"passes": fit["history"][k]["passes"], "stopped_on": fit["history"][k]["stopped_on"]}
                          for k in ("raw", "smoothed", "interaction")},
               "seconds_refit": fit["profile"]["seconds_total"] if "seconds_total" in fit["profile"] else None}
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
        # the shipped-dial kernel's out-group prediction (all couples' dials, shrunk)
        d_all = fit_dials(f_m, mc, A_m, form)
        se2 = K.dial_se2(d_all, n_eff)
        tilde = np.ones(3)
        for k in range(3):
            tilde[k], _ = K.shrink_one(d_all["theta"][k], se2[k], shs[k])
        pi = K.formation_propensity(fit["N_s"], A_minus)
        pn = predict_outgroup(f_m, np.ones(3), A_m, pi, form)
        rec["outgroup_pred"] = {"national_only": pn["predicted"], "random_pairing": pn["random_pairing"],
                           "raw_dial": predict_outgroup(f_m, d_all["theta"], A_m, pi, form)["predicted"],
                           "shrunk_dial": predict_outgroup(f_m, tilde, A_m, pi, form)["predicted"],
                           "observed_fitting_sample": K.observed_outgroup(mc)}
        rec["theta_tilde"] = tilde.tolist()
        out["forms"][name] = rec
    return out


def run_lomo_forms(state: dict, metro_levels: list[str], workers: int) -> list[dict]:
    import multiprocessing as mp
    ctx = mp.get_context("fork")
    # Phase 3d A2: the projections are built in the parent (an SVD) before
    # forking, so the workers inherit them instead of calling LAPACK in a
    # forked child, which macOS terminates abruptly
    for form in state["forms"].values():
        if form.interaction and PROJECT_INTERACTION:
            projection(form)
    t0 = time.time()
    out = []
    with ProcessPoolExecutor(max_workers=workers, mp_context=ctx,
                             initializer=_init_worker, initargs=(state,)) as ex:
        for r in ex.map(_lomo_forms_one, metro_levels, chunksize=2):
            out.append(r)
            if len(out) % 40 == 0 or len(out) == len(metro_levels):
                print(f"  lomo {len(out)}/{len(metro_levels)} metros ({time.time() - t0:.0f}s)", flush=True)
    return out


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
    # the check is of the Form machinery against kernel.py, so it runs
    # under kernel.py's stopping rule (Phase 3d A1 keeps it as stop="cell")
    new = fit_form(S["C"], A, Form(), bandwidth=bw, mean_weight=S["mean_weight"], stop="cell")
    new_g = gauge_form(new["f"], A, new["N_s"], Form())
    t2 = time.time()
    diffs = {"age": float(np.abs(ref_g["age"] - new_g["age"][:, 0, :]).max()),
             "edu": float(np.abs(ref_g["edu"] - new_g["edu"]).max()),
             "race": float(np.abs(ref_g["race"] - new_g["race"]).max()),
             "log_norm": float(np.abs(K.log_norm_for(ref_g, A) - log_norm_form(new_g, A, Form())).max())}
    cv_new = fit_form(S["C"], A, Form(), mean_weight=S["mean_weight"], stop="cell")["bandwidth"]
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
        if "shipped" in only and "shipped" in report["forms"]:
            # Phase 3d: the m3.2.0 form refitted by name, so a re-scored
            # held-out comparison reads every form from the same code
            fr = report["forms"]["shipped"]["form"]
            forms["shipped"] = form_from_record(fr, "shipped")
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
        forms["shipped"] = form_from_record(fr, "shipped")
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
        all_forms["shipped"] = form_from_record(rep["forms"]["shipped"]["form"], "shipped")
    present = {n: f for n, f in all_forms.items() if all(n in r["forms"] for r in lomo)}
    summarise_lomo(sample, lomo, present, common, full)
    print(f"LOMO done ({time.time() - t0:.0f}s)")


def summarise_lomo(sample: str, lomo: list[dict], forms: dict, common: dict, full: dict) -> dict:
    base = "baseline"
    out = {"sample": sample, "metros": len(lomo), "forms": {}, "rule": (
        "a refinement ships when its total split-half held-out log-likelihood under the "
        "shrunk-dial kernel exceeds the baseline form's (same metros, same halves, same "
        "shrinkage machinery) by at least the ADR 0014 margin per 1,000 weighted couple-sides "
        "(anything less is a tie, and a tie goes to the simpler form); metro counts and the "
        "national-only (no-dial) comparison are reported beside it"),
        "heldout_tie_margin_per_1000_sides": HELDOUT_TIE_MARGIN_PER_1000, "tie_rule_adr": HELDOUT_TIE_ADR}
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
               "ships": bool(name != base and beats((tot["shrunk"] - btot["shrunk"]) / sides * 1000))}
        if "shipped" in forms and all("shipped" in r["forms"] for r in lomo):
            # Phase 3c B3: the candidates are judged against the SHIPPED
            # form (baseline + race x education), not the baseline
            stot = sum(r["forms"]["shipped"]["shrunk"] for r in lomo)
            rec["gain_vs_shipped_shrunk_per_1000_sides"] = (tot["shrunk"] - stot) / sides * 1000
            rec["metros_where_better_than_shipped_shrunk"] = sum(
                1 for r in lomo if r["forms"][name]["shrunk"] > r["forms"]["shipped"]["shrunk"])
            rec["improves_on_shipped"] = beats(rec["gain_vs_shipped_shrunk_per_1000_sides"])
        # the intermarriage check for the record (ADR 0016: the Census PUMS
        # newlywed rate; Pew's table until Phase 4)
        ref_rec, comp = K.outgroup_comparison(
            # stores written before Phase 4 name the same predictions pew_pred
            [{"cbsa": r["cbsa"], "outgroup_pred": r["forms"][name].get("outgroup_pred",
                                                                     r["forms"][name].get("pew_pred"))}
             for r in lomo],
            K.outgroup_reference(common["metro_levels"]), K.outgroup_reference_national(),
            json.loads((P3 / "kernel_report.json").read_text())["samples"][sample]["national_outgroup_share"],
            common["metro_levels"], full, P3B / f"outgroup_lomo_{name}.csv")
        rec["intermarriage"] = {"corrected_errors": ref_rec["corrected_errors"], "paired": ref_rec["paired"],
                                "level_offset_ratio_ours_over_reference":
                                    ref_rec["level_offset_ratio_ours_over_reference"]}
        out["forms"][name] = rec
        print(f"  [{name}] held-out gain vs baseline (shrunk) {rec['gain_vs_baseline_shrunk_per_1000_sides']:+.3f} "
              f"per 1,000 sides, better in {wins}/{len(lomo)} metros; ships={rec['ships']}; "
              f"intermarriage shrunk {ref_rec['corrected_errors']['shrunk_dial']['median_abs_pts']}", flush=True)
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
    figure and intermarriage comparison on the record)."""
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
        improves = beats(r["gain_vs_baseline_shrunk_per_1000_sides"])        # ADR 0014 §2
        ships[n] = {"improves_heldout": improves,
                    "heldout_gain_per_1000_sides": r["gain_vs_baseline_shrunk_per_1000_sides"],
                    "heldout_tie_margin_per_1000_sides": HELDOUT_TIE_MARGIN_PER_1000,
                    "rank_stability_pass": bool(st[n]["pass"]) if n in st else None,
                    "rank_stability_min_share": st[n]["min_share"] if n in st else None,
                    "ships": bool(improves and n in st and st[n]["pass"])}
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
    form = form_from_record(fr, form_name)
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
    form_os = form_from_record(fr, form_name)
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
            # ADR 0014: the held-out tie rule the form choice was made under
            "heldout_tie_rule_adr": HELDOUT_TIE_ADR,
            "heldout_tie_margin_per_1000_sides": HELDOUT_TIE_MARGIN_PER_1000,
            "provisional": False, "generated_at": time.strftime("%Y-%m-%dT%H:%M:%S%z"),
            **(extra_meta or {})}
    out = out_dir or DATA
    write_artifact_v2(out, form_os, fits[form_name]["fg"], dials, earned, common["A"],
                      common["metro_levels"], ss, meta)
    print(f"artifact -> {out} (form {form_os.describe()}, dials {earned}, "
          f"same-sex components {ss['components'] if ss else None}, "
          f"same-sex interaction {ss['interaction'] if ss else None})")


# ---------------------------------------------------------------------------
# Phase 4 (ADR 0018): kernel_v3 — three forms in one artifact
# ---------------------------------------------------------------------------

KERNEL_VERSION_V3 = "kernel_v3"


def _race_invariant(ln_flat: np.ndarray, n_metros: int | None = None) -> np.ndarray:
    """A race-free kernel's normaliser does not depend on the seeker's
    race: reshape per seeker type and keep one race slice, asserting the
    others equal it."""
    shape = (N_SEX, N_AGE, N_EDU, N_RACE) if n_metros is None else (n_metros, N_SEX, N_AGE, N_EDU, N_RACE)
    ln = ln_flat.reshape(shape)
    assert np.allclose(ln, ln[..., :1], atol=1e-9), "a race-free normaliser varies with the seeker's race"
    return ln[..., 0]


def write_artifact_v3(out_dir: Path, served_kernel: Path, form_rf: Form, fg_rf: dict, dials_rf: np.ndarray,
                      earned_rf: list[str], form_ss: Form, fg_ss: dict, A: np.ndarray,
                      metro_levels: list[str], meta: dict) -> dict:
    """kernel.json + kernel.npz, version kernel_v3 (m4.0.0, ADR 0018):

      race on   C1 exactly as m3.5.0 serves it — its arrays copied from the
                served artifact (`served_kernel`), byte for byte: f_age,
                f_edu, f_race, f_int, cohort_edges, dials, log_norm;
      race off  the race-free form (rf_*): the cohort age term and the
                education matrix, refitted with no race component and no
                interaction, its own dials (no race dial) and normalisers
                (metro x sex x age x education — a seeker's race does not
                enter);
      same-sex  the same-sex age and education terms (ss_*), refitted with
                no race component, no interaction and no dial, so the
                normaliser is national (sex x age x education)."""
    out_dir.mkdir(parents=True, exist_ok=True)
    served = np.load(served_kernel / "kernel.npz", allow_pickle=False)
    served_meta = json.loads((served_kernel / "kernel.json").read_text())
    assert served_meta["version"] == KERNEL_VERSION_V2, served_meta["version"]
    assert list(served["metro_levels"]) == metro_levels, "served kernel metro order differs"
    # the store recomputes the national availability with a different
    # summation order (relative differences ~1e-16); the new forms'
    # normalisers are computed on the SERVED array, the one the artifact
    # carries and seeker_weights reads, so each form averages exactly 1
    A_served = np.asarray(served["avail_national"], dtype=np.float64)
    assert np.allclose(A_served, A, rtol=1e-12, atol=0), \
        "the served kernel's national availability differs from this build's beyond summation noise"
    assert not form_rf.has_race and not form_ss.has_race
    n = len(metro_levels)
    ln_rf = np.stack([_race_invariant(log_norm_served(served_log_kernel(fg_rf, form_rf, dials_rf[i], None, None, ()),
                                                      A_served, False))
                      for i in range(n)])                                             # (n, 2, 53, 4)
    logK_ss = design2(form_ss).gather({k: v for k, v in fg_ss.items() if k != "int"})
    ln_ss = _race_invariant(log_norm_served(logK_ss, A_served, True))                 # (2, 53, 4)
    arrays = {k: np.asarray(served[k]) for k in served.files
              if not k.startswith("ss_")}                         # C1 as served
    arrays.update({
        "rf_f_age": fg_rf["age"], "rf_f_edu": (fg_rf["edu"] if form_rf.edu_by_sex
                                               else np.stack([fg_rf["edu"], fg_rf["edu"]])),
        "rf_cohort_edges": np.array(form_rf.age_edges, int), "rf_dials": dials_rf,
        "rf_log_norm": ln_rf.astype(np.float32),
        "ss_f_age": fg_ss["age"], "ss_f_edu": (fg_ss["edu"] if form_ss.edu_by_sex
                                               else np.stack([fg_ss["edu"], fg_ss["edu"]])),
        "ss_cohort_edges": np.array(form_ss.age_edges, int),
        "ss_log_norm": ln_ss.astype(np.float32)})
    np.savez_compressed(out_dir / "kernel.npz", **arrays)
    payload = {
        "version": KERNEL_VERSION_V3,
        "form": "three forms (ADR 0018). Race on (the seeker's race given): w = exp(theta_age f_age(gap; "
                "sex_s, cohort) + theta_edu f_edu + theta_race f_race + g(race x edu) + log_norm), C1 as "
                "m3.5.0 serves it. Race off: w = exp(theta_age rf_f_age(gap; sex_s, cohort) + theta_edu "
                "rf_f_edu + rf_log_norm), no race term, no interaction. Same-sex: w = exp(ss_f_age(gap; "
                "sex_s) + ss_f_edu + ss_log_norm), no race term, no interaction, no dial",
        "gauge": served_meta["gauge"],
        "sex_levels": SEX_LEVELS, "age_levels": list(range(18, 71)),
        "edu_levels": EDU_LEVELS, "race_levels": RACE_LEVELS,
        "gap_offset": GAP0, "floor_log": FLOOR,
        # race on: C1, as served
        "age_cohort_edges": served_meta["age_cohort_edges"], "age_cohorts": served_meta["age_cohorts"],
        "edu_by_sex": served_meta["edu_by_sex"], "interaction": served_meta["interaction"],
        "dial_components": served_meta["dial_components"], "components": list(COMPONENTS),
        "dials": served_meta["dials"],
        "race_on": {"form": served_meta.get("shipped_form_name"), "as_served_by": served_meta.get("generated_at"),
                    "copied_from": str(served_kernel.name)},
        "race_off": {"form": form_rf.describe(), "dial_components": earned_rf,
                     "dials": {c: [round(float(x), 6) for x in dials_rf[i]] for i, c in enumerate(metro_levels)}},
        "same_sex": {"components_from_same_sex_couples": ["age", "edu"], "fallback_components": [],
                     "race": "none", "interaction_applies": False,
                     "dials_on_same_sex_terms": "none (national terms at dial 1)",
                     "form": form_ss.describe()},
        "npz": "kernel.npz: C1 (race on) as served — f_age, f_edu, f_race, f_int, cohort_edges, dials, "
               "log_norm (metro x sex x age x edu x race); race off — rf_f_age, rf_f_edu, rf_cohort_edges, "
               "rf_dials, rf_log_norm (metro x sex x age x edu); same-sex — ss_f_age, ss_f_edu, "
               "ss_cohort_edges, ss_log_norm (sex x age x edu); avail_national, metro_levels",
        **meta,
    }
    (out_dir / "kernel.json").write_text(json.dumps(payload, indent=1, default=_json) + "\n")
    return payload


def cmd_ship_v3(sample: str, served_build: Path, out_dir: Path | None = None) -> None:
    """The m4.0.0 artifact from this store: C1 from the served build, the
    race-free form's full fit and shrunk dials (the dials it earns by the
    Phase 3 rule), and the race-free same-sex refit (samesex --race-free)."""
    rep = json.loads((P3B / "refine_fits.json").read_text())
    ho = json.loads((P3B / "refine_heldout.json").read_text())
    name = "D0_race_free"
    fits, _ = _load_fits([name])
    form_rf = form_from_record(rep["forms"][name]["form"], name)
    common = load_common(sample)
    dd = pd.read_csv(P3B / f"dials_{name}.csv", dtype={"cbsa": str}).set_index("cbsa").loc[common["metro_levels"]]
    earned = [k for k in COMPONENTS if k != "race"
              and ho["forms"][name]["dial_gain_shrunk_minus_national_per_1000_sides"] > 0]
    dials = np.ones((len(common["metro_levels"]), 3))
    for j, k in enumerate(COMPONENTS):
        if k in earned:
            dials[:, j] = dd[f"theta_tilde_{k}"].to_numpy(float)
    srep = json.loads((P3B / "samesex_fit.json").read_text())
    assert "race_free_fit" in srep, "run samesex --race-free first"
    z = np.load(P3B / "_samesex_fit.npz")
    fg_ss = {k[6:]: z[k] for k in z.files if k.startswith("rf_fg_")}
    form_ss = Form(name="samesex_race_free", race=False)
    meta = {"fitting_sample": sample, "fitting_sample_spec": json.loads((P3 / "kernel_report.json").read_text())
            ["samples"][sample]["spec"],
            "couple_sides_weighted": rep["couple_sides_weighted"], "n_alloc": rep["n_alloc"],
            "bandwidth_years": rep["fits"][name]["bandwidth"],
            "dials_tau": {k: rep["forms"][name]["dials"][k]["tau"] for k in COMPONENTS},
            "dials_centre": {k: rep["forms"][name]["dials"][k]["precision_weighted_mean_theta"]
                             for k in COMPONENTS},
            "same_sex_bandwidth_years": srep["race_free_fit"].get("bandwidth_by_sex_cohort"),
            "heldout_tie_rule_adr": HELDOUT_TIE_ADR,
            "heldout_tie_margin_per_1000_sides": HELDOUT_TIE_MARGIN_PER_1000,
            "provisional": False, "generated_at": time.strftime("%Y-%m-%dT%H:%M:%S%z")}
    out = out_dir or DATA
    write_artifact_v3(out, served_build, form_rf, fits[name]["fg"], dials, earned, form_ss, fg_ss,
                      common["A"], common["metro_levels"], meta)
    print(f"artifact v3 -> {out} (race off {form_rf.describe()['name']}, dials {earned}; race on C1 as "
          f"served by {served_build.name}; same-sex age + edu, no race)")


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
    # Phase 3d A1 (item 3): both refits warm-start from the smoothed-stage
    # terms and stop on the couple-weighted rule (run_lomo_forms's treatment)
    fit_os = fit_form(C_os, A_minus, form_os, bandwidth=F["bandwidth"], tau2=F["tau2"],
                      init={**F["f"]}, max_iter=K.IPF_MAX_ITER, mean_weight=_W["mean_weight_os"])
    fg_os = gauge_form(fit_os["f"], A_minus, fit_os["N_s"], form_os)
    # same-sex kernel without the metro's same-sex couples
    C_ss = _W["C_ss"].copy()
    np.add.at(C_ss, (mc_ss.s, mc_ss.c), -mc_ss.w)
    C_ss[C_ss < 0] = 0.0
    G = _W["fit_ss"]
    fit_ss = fit_form(C_ss, A_minus, form_ss, same_sex=True, bandwidth=G["bandwidth"], init=G["f"],
                      max_iter=K.IPF_MAX_ITER, mean_weight=_W["mean_weight_ss"])
    fg_ss = gauge_form(fit_ss["f"], A_minus, fit_ss["N_s"], form_ss, same_sex=True)
    # Phase 4 (ADR 0018): the race-free same-sex refit, without the metro
    fg_rf = None
    if _W.get("fit_ss_rf") is not None:
        G2, form_rf = _W["fit_ss_rf"], _W["form_ss_rf"]
        fit_rf = fit_form(C_ss, A_minus, form_rf, same_sex=True, bandwidth=G2["bandwidth"], init=G2["f"],
                          max_iter=K.IPF_MAX_ITER, mean_weight=_W["mean_weight_ss"])
        fg_rf = gauge_form(fit_rf["f"], A_minus, fit_rf["N_s"], form_rf, same_sex=True)
    theta = np.array(_W["theta"][i], float)
    d_os, d_ss = design2(form_os), design2(form_ss)

    def loglik(which: dict, interaction: bool | None = None, ss_terms: dict | None = None) -> float:
        # log kernel per present seeker over cells, from whichever source
        # each component takes ("ss", "os", or since Phase 4 "none": left
        # out); `interaction` None = m3.2.0's rule (rides only when
        # education and race both stay opposite-sex); `ss_terms` swaps in
        # another same-sex fit (the race-free refit)
        P = mc_ss.present
        src = fg_ss if ss_terms is None else ss_terms
        logK = np.zeros((len(P), N_C))
        for j, k in enumerate(COMPONENTS):
            if which[k] == "none":
                continue
            if which[k] == "ss":
                logK += d_ss.gather_one(k, src[k], P)
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
           "iterations": [fit_os["iterations"], fit_ss["iterations"]],
           "stages": {"os": {k: {"passes": fit_os["history"][k]["passes"], "stopped_on": fit_os["history"][k]["stopped_on"]}
                             for k in ("raw", "smoothed", "interaction")},
                      "ss": {k: {"passes": fit_ss["history"][k]["passes"], "stopped_on": fit_ss["history"][k]["stopped_on"]}
                             for k in ("raw", "smoothed")}},
           "seconds_refit": [fit_os["profile"].get("seconds_total"), fit_ss["profile"].get("seconds_total")]}
    for k in COMPONENTS:
        rec[f"only_{k}"] = loglik({**fallback, k: "ss"})
    # Phase 3c B2: what m3.2.0 serves (age same-sex, education and race
    # opposite-sex, the interaction riding), and the education term added
    # to it with the interaction off (m3.2.0's rule) and forced on
    served = {"age": "ss", "edu": "os", "race": "os"}
    rec["served_m3_2_0"] = loglik(served, interaction=True)
    rec["age_edu_ss_no_interaction"] = loglik({**served, "edu": "ss"}, interaction=False)
    rec["age_edu_ss_with_interaction"] = loglik({**served, "edu": "ss"}, interaction=True)
    # Phase 4 (ADR 0018): no race at all on a same-sex search — the
    # race-free same-sex refit, and for the record the joint fit's age and
    # education terms with race dropped (what the refit replaces)
    no_race = {"age": "ss", "edu": "ss", "race": "none"}
    rec["age_edu_ss_joint_race_dropped"] = loglik(no_race, interaction=False)
    if fg_rf is not None:
        rec["age_edu_ss_race_free_refit"] = loglik(no_race, interaction=False, ss_terms=fg_rf)
    return rec


def samesex_decision(lomo: list[dict], support: dict, face: dict) -> dict:
    """B3's decision from the same-sex leave-one-metro-out record, every
    held-out comparison through ADR 0014's `beats`: a component is served
    from same-sex couples when its sample supports it, its term beats the
    opposite-sex fallback on held-out same-sex couples and it passes the
    face check. Since Phase 3c B2 (ADR 0010 amended) the education term is
    judged against what m3.2.0 serves — it ships if either composition
    (interaction off or on) beats the served one — and the interaction
    rides only if the composition with it beats the one without (§4: a
    tie keeps the simpler composition, the interaction off). Race stays
    borrowed (its support has not changed)."""
    sides = sum(x["sides"] for x in lomo)
    per_1000 = 1000.0 / sides
    keys = ["fallback", "all_samesex"] + [f"only_{c}" for c in COMPONENTS]
    keys += [k for k in ("served_m3_2_0", "age_edu_ss_no_interaction", "age_edu_ss_with_interaction")
             if all(k in x for x in lomo)]
    tot = {k: sum(x[k] for x in lomo) for k in keys}
    heldout = {"metros": len(lomo), "sides": sides, "totals": tot,
               "gain_per_1000_sides": {k: (v - tot["fallback"]) * per_1000 for k, v in tot.items()},
               "metros_better_than_fallback": {k: sum(1 for x in lomo if x[k] > x["fallback"])
                                               for k in tot if k != "fallback"},
               "tie_rule": {"adr": HELDOUT_TIE_ADR, "margin_per_1000_sides": HELDOUT_TIE_MARGIN_PER_1000,
                            "rule": "a component beats the fallback, and the richer composition beats the "
                                    "simpler one, only by at least the margin; a tie keeps the simpler one"},
               "components": {}}
    for k in COMPONENTS:
        improves = beats(heldout["gain_per_1000_sides"][f"only_{k}"])
        heldout["components"][k] = {"supported": support["supported"][k], "improves_heldout": bool(improves),
                                    "face_validity_pass": face[k],
                                    "ships": bool(support["supported"][k] and improves and face[k])}
    heldout["served_from_same_sex_couples"] = [k for k in COMPONENTS if heldout["components"][k]["ships"]]
    heldout["fallback_components"] = [k for k in COMPONENTS if not heldout["components"][k]["ships"]]
    if "served_m3_2_0" in tot:
        base = tot["served_m3_2_0"]
        g_no = (tot["age_edu_ss_no_interaction"] - base) * per_1000
        g_int = (tot["age_edu_ss_with_interaction"] - base) * per_1000
        margin_int = (tot["age_edu_ss_with_interaction"] - tot["age_edu_ss_no_interaction"]) * per_1000
        use_int = beats(margin_int)
        heldout["vs_m3_2_0_served"] = {
            "baseline": "age from same-sex couples, education and race from opposite-sex couples, "
                        "the interaction riding (what m3.2.0 serves)",
            "gain_per_1000_sides": {"age_edu_ss_no_interaction": g_no, "age_edu_ss_with_interaction": g_int},
            "metros_better_than_served": {
                k: sum(1 for x in lomo if x[k] > x["served_m3_2_0"])
                for k in ("age_edu_ss_no_interaction", "age_edu_ss_with_interaction")},
            "education_term_improves_on_served": bool(beats(max(g_no, g_int)))}
        heldout["interaction_decision"] = {
            "rule": "serve the composition with the interaction only if it beats the one without on "
                    "held-out same-sex couples by the ADR 0014 margin (education and age from same-sex "
                    "couples, race borrowed); a tie keeps the interaction off",
            "interaction_applies": bool(use_int),
            "margin_per_1000_sides": margin_int}
        heldout["interaction_applies"] = bool(use_int)
        heldout["stop_condition_education_no_longer_improves"] = not heldout["vs_m3_2_0_served"][
            "education_term_improves_on_served"]
    return heldout


def samesex_race_free_reading(lomo: list[dict]) -> dict:
    """Phase 4 (ADR 0018): what taking race out of same-sex searches costs
    on held-out same-sex couples, and why the race-free terms are refitted
    rather than read off the joint fit — every comparison per 1,000
    weighted same-sex couple-sides, through ADR 0014's margin."""
    sides = sum(x["sides"] for x in lomo)
    per_1000 = 1000.0 / sides
    tot = {k: sum(x[k] for x in lomo) for k in ("age_edu_ss_with_interaction",
                                                   "age_edu_ss_joint_race_dropped",
                                                   "age_edu_ss_race_free_refit")}
    served = "age_edu_ss_with_interaction"
    refit, dropped = "age_edu_ss_race_free_refit", "age_edu_ss_joint_race_dropped"
    return {"metros": len(lomo), "sides": sides,
            "served_m3_5_0": "age and education from same-sex couples, race borrowed from "
                             "opposite-sex couples with the metro's dial, the interaction riding",
            "refit_vs_served_per_1000_sides": (tot[refit] - tot[served]) * per_1000,
            "refit_vs_joint_race_dropped_per_1000_sides": (tot[refit] - tot[dropped]) * per_1000,
            "metros_refit_better_than_served": sum(1 for x in lomo if x[refit] > x[served]),
            "metros_refit_better_than_joint_race_dropped": sum(1 for x in lomo if x[refit] > x[dropped]),
            "refit_beats_joint_race_dropped": bool(beats((tot[refit] - tot[dropped]) * per_1000)),
            "joint_race_dropped_beats_refit": bool(beats((tot[dropped] - tot[refit]) * per_1000)),
            "tie_rule": {"adr": HELDOUT_TIE_ADR, "margin_per_1000_sides": HELDOUT_TIE_MARGIN_PER_1000}}


def cmd_samesex(sample: str, workers: int, shipped_form_name: str = "shipped", fit_only: bool = False,
                decide_only: bool = False, race_free: bool = False) -> None:
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
    rf = None
    if race_free:
        # Phase 4 (ADR 0018): the same-sex form with no race component,
        # refitted on the same-sex couples by the same machinery
        form_ss_rf = Form(name="samesex_race_free", race=False)
        rf = fit_and_report(sample, form_ss_rf, S_ss, A, same_sex=True)
        report["race_free_fit"] = rf["record"]
    np.savez_compressed(P3B / "_samesex_fit.npz", **{f"fg_{k}": v for k, v in r["fg"].items()},
                        **{f"f_{k}": v for k, v in r["fit"]["f"].items()},
                        **({f"rf_fg_{k}": v for k, v in rf["fg"].items()} if rf else {}),
                        **({f"rf_f_{k}": v for k, v in rf["fit"]["f"].items()} if rf else {}))
    (P3B / "samesex_fit.json").write_text(json.dumps(report, indent=1, default=_json) + "\n")
    print(f"[samesex] support {support['supported']}; fit face {r['record']['face_validity']['pass']}", flush=True)
    if fit_only:
        return
    rep = json.loads((P3B / "refine_fits.json").read_text())
    fits, _ = _load_fits([shipped_form_name])
    fr = rep["forms"][shipped_form_name]["form"]
    form_os = form_from_record(fr, shipped_form_name)
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
             "fit_ss": {"raw_f": r["fit"]["raw_f"], "f": r["fit"]["f"], "bandwidth": r["fit"]["bandwidth"]},
             "fit_ss_rf": ({"f": rf["fit"]["f"], "bandwidth": rf["fit"]["bandwidth"]} if rf else None),
             "form_ss_rf": (Form(name="samesex_race_free", race=False) if rf else None),
             "mean_weight_os": S_os["mean_weight"], "mean_weight_ss": S_ss["mean_weight"], "theta": theta}
    metros = [c for c in common["metro_levels"] if c in full_ss]
    if decide_only and (P3B / "lomo_samesex.json").exists():
        lomo = json.loads((P3B / "lomo_samesex.json").read_text())
    else:
        print(f"[samesex] LOMO x{len(metros)} with {workers} workers ...", flush=True)
        import multiprocessing as mp
        ctx = mp.get_context("fork")
        if form_os.interaction and PROJECT_INTERACTION:
            projection(form_os)          # built in the parent, as run_lomo_forms does
        with ProcessPoolExecutor(max_workers=workers, mp_context=ctx,
                                 initializer=_init_worker, initargs=(state,)) as ex:
            lomo = list(ex.map(_lomo_samesex_one, metros, chunksize=2))
    lomo = [x for x in lomo if x["sides"] > 0]
    # a component is served from same-sex couples when its sample supports
    # it, it beats the opposite-sex fallback on held-out same-sex couples
    # (ADR 0014), AND its term passes the standing face-validity check (the
    # battery's hard gate reads every served matrix; a same-sex education
    # matrix that is not diagonal-dominant would fail the build)
    face = {"age": bool(r["record"]["face_validity"]["age_pass"]),
            "edu": bool(r["record"]["face_validity"]["edu_pass"]),
            "race": bool(r["record"]["face_validity"]["race_pass"])}
    heldout = samesex_decision(lomo, support, face)
    if rf is not None:
        heldout["race_free"] = samesex_race_free_reading(lomo)
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
                    fit_only="--fit-only" in argv, decide_only="--decide-only" in argv,
                    race_free="--race-free" in argv)
    elif argv[:1] == ["combine"]:
        cmd_combine(sample, argv[argv.index("--only") + 1].split(",") if "--only" in argv else None,
                    argv[argv.index("--reason") + 1] if "--reason" in argv else None)
    elif argv[:1] == ["candidate"]:
        cmd_candidate(sample, argv[argv.index("--form") + 1], Path(argv[argv.index("--out") + 1]))
    elif argv[:1] == ["ship_v3"]:
        cmd_ship_v3(sample, Path(argv[argv.index("--served") + 1]),
                    Path(argv[argv.index("--out") + 1]) if "--out" in argv else None)
    elif argv[:1] == ["ship"]:
        cmd_ship(sample, Path(argv[argv.index("--out") + 1]) if "--out" in argv else None,
                 argv[argv.index("--form") + 1] if "--form" in argv else "shipped")
    else:
        print(__doc__)
