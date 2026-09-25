"""Phase 3d R2 (ADR 0014): every held-out decision on the record — Phase
3b, Phase 3c and the A2 re-run — read from the stored records only (no
refit), under the old rule (improves = a strict > 0; the largest gain among
the qualifying candidates) and under ADR 0014 (beats = at least δ per 1,000
weighted couple-sides; a tie goes to the simpler form), side by side; the
δ interval over which every verdict is unchanged; the three anchors for
δ = 0.25; and, for the record and not as a gate, each decision's margin,
its paired, metro-clustered standard error and the number of metros where
the richer form is better, from lomo_forms.json and lomo_samesex.json in
the A2 store and in Phase 3c (Phase 3b's records, which Phase 3c carried
forward unchanged, are read where a decision was Phase 3b's).

The standard error: the per-metro differences d_m of held-out
log-likelihood between the two forms (the same metro left out, the same
household halves, the same shrinkage) are treated as M independent draws;
the standard error of their total is sqrt(M * s_d^2) with s_d^2 the sample
variance (M - 1), then per 1,000 sides. Paired because both forms are
scored on the same halves; clustered because a metro is the unit.

    PYTHONPATH=. .venv/bin/python atlas/results/phase3d/tie_rule.py
        -> results/phase3d/tie_rule.json  (exit 1 if an expected verdict differs)
"""
import json, sys
from pathlib import Path

import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parents[3]))
from atlas.pipeline.build import kernel_refine as KR
from atlas.pipeline.fetch import RESULTS

P3B, P3C = RESULTS / "phase3b", RESULTS / "phase3c"
A2 = RESULTS / "phase3d" / "speedup" / "a2"
OUT = RESULTS / "phase3d" / "tie_rule.json"
DELTA = KR.HELDOUT_TIE_MARGIN_PER_1000
CANDS = ("C1_cohorts_plus_shipped", "C2_edu_by_sex_plus_shipped", "C3_both_plus_shipped")
EPS = 1e-9


def rel(p: Path) -> str:
    return str(p.relative_to(RESULTS.parent))


def load(p: Path):
    return json.loads(p.read_text())


def paired(diffs, sides: float) -> dict:
    d = np.asarray(diffs, float)
    M = len(d)
    tot = float(d.sum() / sides * 1000)
    se = float(np.sqrt(M / (M - 1) * ((d - d.mean()) ** 2).sum()) / sides * 1000)
    return {"margin_per_1000": tot, "se_per_1000": se, "z": (tot / se if se > 0 else None),
            "metros_richer_better": int((d > 0).sum()), "metros": M}


def forms_stats(store: Path, richer: str, simpler: str) -> dict:
    lomo = load(store / "lomo_forms.json")
    sides = sum(r["forms"][simpler]["sides"] for r in lomo)
    return paired([r["forms"][richer]["shrunk"] - r["forms"][simpler]["shrunk"] for r in lomo], sides) | {
        "source": rel(store / "lomo_forms.json")}


def samesex_stats(store: Path, richer: str, simpler: str) -> dict:
    lomo = [x for x in load(store / "lomo_samesex.json") if x["sides"] > 0]
    sides = sum(x["sides"] for x in lomo)
    return paired([x[richer] - x[simpler] for x in lomo], sides) | {"source": rel(store / "lomo_samesex.json")}


def gate_verdict(p: Path) -> dict | None:
    if not p.exists():
        return None
    v = load(p)["verdict"]
    return {"pass": bool(v["pass"]), "ratio": v["ratio"], "source": rel(p)}


# ---------------------------------------------------------------------------
# the decisions on the record
# ---------------------------------------------------------------------------

def collect() -> tuple[list[dict], dict]:
    """Every held-out decision, with its margin (the richer form minus the
    simpler), its non-held-out conditions and its old-rule reading."""
    D = []
    # ---- Phase 3b (Part B, ADR 0010): three refinements against the baseline; same-sex per component
    ho3b = load(P3B / "refine_heldout.json")["forms"]
    st3b = load(P3B / "stability_check.json")["candidates"]
    for name, label, gate_name in (("B1_age_cohorts", "the cohort age term", "B1_age_cohorts"),
                                   ("B2a_race_x_edu", "race x education", "B2a_race_x_edu"),
                                   ("B2b_edu_by_sex", "the sex-specific education matrix", "B2b_edu_by_sex")):
        g = ho3b[name]["gain_vs_baseline_shrunk_per_1000_sides"]
        gate_pass = bool(st3b[gate_name]["pass"])
        note = None
        if name == "B2b_edu_by_sex":
            gate_pass = bool(st3b["B2a_plus_B2b"]["pass"])
            note = ("passes the old gate alone (0.825) but the combination with race x education fails it "
                    "(0.750): dropped for the combination's failure, whichever rule reads the held-out margin")
        D.append({"id": f"3b:{name}:improves_on_baseline", "phase": "3b", "kind": "improves",
                  "decision": f"{label} improves held-out fit over the baseline form",
                  "richer": name, "simpler": "baseline", "margin_per_1000": g,
                  "stats": forms_stats(P3B, name, "baseline"),
                  "other_conditions": {"old_overlap_gate_pass": gate_pass,
                                       "old_overlap_min_share": st3b[gate_name]["min_share"]},
                  "outcome_if_yes": gate_pass, "note": note,
                  "sources": [rel(P3B / "refine_heldout.json"), rel(P3B / "stability_check.json")]})
    ss3b = load(P3B / "samesex_fit.json")
    for k in KR.COMPONENTS:
        c = ss3b["heldout"]["components"][k]
        D.append({"id": f"3b:samesex_{k}:improves_on_fallback", "phase": "3b", "kind": "improves",
                  "decision": f"the same-sex {k} term predicts held-out same-sex couples better than the "
                              f"opposite-sex fallback",
                  "richer": f"only_{k}", "simpler": "fallback",
                  "margin_per_1000": ss3b["heldout"]["gain_per_1000_sides"][f"only_{k}"],
                  "stats": samesex_stats(P3B, f"only_{k}", "fallback"),
                  "other_conditions": {"supported": bool(c["supported"]), "face_validity_pass": bool(c["face_validity_pass"])},
                  "outcome_if_yes": bool(c["supported"] and c["face_validity_pass"]),
                  "sources": [rel(P3B / "samesex_fit.json")]})
    # ---- Phase 3c (B2: the same-sex education term against what m3.2.0 serves; B3: C1/C2/C3)
    ss3c = load(P3C / "samesex_fit.json")["heldout"]
    g_no, g_int = (ss3c["vs_m3_2_0_served"]["gain_per_1000_sides"][k]
                   for k in ("age_edu_ss_no_interaction", "age_edu_ss_with_interaction"))
    D.append({"id": "3c:samesex_edu:improves_on_served", "phase": "3c", "kind": "improves",
              "decision": "the same-sex education term ships: a composition with it (interaction off or on) "
                          "improves on what m3.2.0 serves",
              "richer": "age_edu_ss_with_interaction", "simpler": "served_m3_2_0",
              "margin_per_1000": max(g_no, g_int), "margins_both_settings": {"interaction_off": g_no, "interaction_on": g_int},
              "stats": samesex_stats(P3C, "age_edu_ss_with_interaction", "served_m3_2_0"),
              "stats_interaction_off": samesex_stats(P3C, "age_edu_ss_no_interaction", "served_m3_2_0"),
              "other_conditions": {"face_validity_pass_amended_rule": True,
                                   "gate": gate_verdict(P3C / "gate_B2_samesex_edu.json")},
              "outcome_if_yes": True, "sources": [rel(P3C / "samesex_fit.json")]})
    D.append({"id": "3c:samesex_interaction:rides", "phase": "3c", "kind": "yes_no",
              "decision": "the opposite-sex race x education interaction rides on same-sex searches",
              "richer": "age_edu_ss_with_interaction", "simpler": "age_edu_ss_no_interaction",
              "margin_per_1000": ss3c["interaction_decision"]["margin_per_1000_sides"],
              "stats": samesex_stats(P3C, "age_edu_ss_with_interaction", "age_edu_ss_no_interaction"),
              "other_conditions": {}, "outcome_if_yes": True, "sources": [rel(P3C / "samesex_fit.json")]})
    ho3c = load(P3C / "refine_heldout.json")["forms"]
    edges3c = tuple(load(P3C / "refine_fits.json")["partition"]["chosen_edges"])
    D.append({"id": "3c:C:choice", "phase": "3c", "kind": "choice",
              "decision": "of C1, C2 and C3, those improving on the shipped form (m3.2.0's) and passing the "
                          "ADR 0011 gate; which ships",
              "reference": "shipped", "edges": edges3c,
              "candidates": {n: {"gain_per_1000": ho3c[n]["gain_vs_shipped_shrunk_per_1000_sides"],
                                 "gate": gate_verdict(P3C / f"gate_{n}.json"),
                                 "stats": forms_stats(P3C, n, "shipped")} for n in CANDS},
              "pairs": {"C3_minus_C1": forms_stats(P3C, "C3_both_plus_shipped", "C1_cohorts_plus_shipped"),
                        "C2_minus_C1": forms_stats(P3C, "C2_edu_by_sex_plus_shipped", "C1_cohorts_plus_shipped")},
              "sources": [rel(P3C / "refine_heldout.json")] + [rel(P3C / f"gate_{n}.json") for n in CANDS]})
    # ---- the A2 re-run (the finished fit, the a2 store)
    hoa2 = load(A2 / "refine_heldout.json")["forms"]
    g = hoa2["B2a_race_x_edu"]["gain_vs_baseline_shrunk_per_1000_sides"]
    gv = gate_verdict(A2 / "gate_B2a_race_x_edu.json")
    D.append({"id": "a2:B2a_race_x_edu:improves_on_baseline", "phase": "a2", "kind": "improves",
              "decision": "race x education improves held-out fit over the baseline form (Phase 3b's "
                          "decision re-run on the finished fit; the gate read is ADR 0011's)",
              "richer": "B2a_race_x_edu", "simpler": "baseline", "margin_per_1000": g,
              "stats": forms_stats(A2, "B2a_race_x_edu", "baseline"),
              "other_conditions": {"gate": gv}, "outcome_if_yes": bool(gv and gv["pass"]),
              "sources": [rel(A2 / "refine_heldout.json"), rel(A2 / "gate_B2a_race_x_edu.json")]})
    ssa2 = load(A2 / "samesex_fit.json")
    for k in KR.COMPONENTS:
        c = ssa2["heldout"]["components"][k]
        D.append({"id": f"a2:samesex_{k}:improves_on_fallback", "phase": "a2", "kind": "improves",
                  "decision": f"the same-sex {k} term predicts held-out same-sex couples better than the "
                              f"opposite-sex fallback (re-run)",
                  "richer": f"only_{k}", "simpler": "fallback",
                  "margin_per_1000": ssa2["heldout"]["gain_per_1000_sides"][f"only_{k}"],
                  "stats": samesex_stats(A2, f"only_{k}", "fallback"),
                  "other_conditions": {"supported": bool(c["supported"]), "face_validity_pass": bool(c["face_validity_pass"])},
                  "outcome_if_yes": bool(c["supported"] and c["face_validity_pass"]),
                  "sources": [rel(A2 / "samesex_fit.json")]})
    g_no, g_int = (ssa2["heldout"]["vs_m3_2_0_served"]["gain_per_1000_sides"][k]
                   for k in ("age_edu_ss_no_interaction", "age_edu_ss_with_interaction"))
    D.append({"id": "a2:samesex_edu:improves_on_served", "phase": "a2", "kind": "improves",
              "decision": "the same-sex education term ships: a composition with it improves on what m3.2.0 "
                          "serves (re-run)",
              "richer": "age_edu_ss_with_interaction", "simpler": "served_m3_2_0",
              "margin_per_1000": max(g_no, g_int), "margins_both_settings": {"interaction_off": g_no, "interaction_on": g_int},
              "stats": samesex_stats(A2, "age_edu_ss_with_interaction", "served_m3_2_0"),
              "stats_interaction_off": samesex_stats(A2, "age_edu_ss_no_interaction", "served_m3_2_0"),
              "other_conditions": {"face_validity_pass_amended_rule": bool(ssa2["fit"]["face_validity"]["edu_pass"]),
                                   "gate_shipped_form_with_same_sex_decision": gate_verdict(A2 / "gate_shipped.json")},
              "outcome_if_yes": True, "sources": [rel(A2 / "samesex_fit.json")]})
    D.append({"id": "a2:samesex_interaction:rides", "phase": "a2", "kind": "yes_no",
              "decision": "the opposite-sex race x education interaction rides on same-sex searches (re-run)",
              "richer": "age_edu_ss_with_interaction", "simpler": "age_edu_ss_no_interaction",
              "margin_per_1000": ssa2["heldout"]["interaction_decision"]["margin_per_1000_sides"],
              "stats": samesex_stats(A2, "age_edu_ss_with_interaction", "age_edu_ss_no_interaction"),
              "other_conditions": {}, "outcome_if_yes": True, "sources": [rel(A2 / "samesex_fit.json")]})
    edgesa2 = tuple(load(A2 / "refine_fits.json")["partition"]["chosen_edges"])
    D.append({"id": "a2:C:choice", "phase": "a2", "kind": "choice",
              "decision": "of C1, C2 and C3 on the finished fit, those improving on the shipped form and "
                          "passing the ADR 0011 gate; which ships",
              "reference": "shipped", "edges": edgesa2,
              "candidates": {n: {"gain_per_1000": hoa2[n]["gain_vs_shipped_shrunk_per_1000_sides"],
                                 "gate": gate_verdict(A2 / f"gate_{n}.json"),
                                 "stats": forms_stats(A2, n, "shipped")} for n in CANDS},
              "pairs": {"C3_minus_C1": forms_stats(A2, "C3_both_plus_shipped", "C1_cohorts_plus_shipped"),
                        "C2_minus_C1": forms_stats(A2, "C2_edu_by_sex_plus_shipped", "C1_cohorts_plus_shipped")},
              "sources": [rel(A2 / "refine_heldout.json")] + [rel(A2 / f"gate_{n}.json") for n in CANDS]})
    context = {"phase3c_forms_shipped_form": "shipped = m3.2.0's form (baseline + race x education)",
               "edges_3c": edges3c, "edges_a2": edgesa2}
    return D, context


# ---------------------------------------------------------------------------
# the rules
# ---------------------------------------------------------------------------

def read_old(d: dict) -> dict:
    """The old rule: improves = a strict > 0; a yes/no takes the richer option
    if it is ahead at all; among candidates the largest gain of those
    improving and passing the gate."""
    if d["kind"] in ("improves", "yes_no"):
        yes = bool(d["margin_per_1000"] > 0)
        return {"verdict": yes, "outcome": bool(yes and d["outcome_if_yes"])}
    c = d["candidates"]
    qual = [n for n in CANDS if c[n]["gain_per_1000"] > 0 and c[n]["gate"] and c[n]["gate"]["pass"]]
    winner = max(qual, key=lambda n: c[n]["gain_per_1000"]) if qual else None
    return {"verdict": {"qualifying": qual, "winner": winner}, "outcome": winner,
            "qualifies": {n: n in qual for n in CANDS}}


def read_new(d: dict, delta: float) -> dict:
    """ADR 0014 at margin `delta`, through the shared functions."""
    if d["kind"] in ("improves", "yes_no"):
        yes = KR.beats(d["margin_per_1000"], delta)
        return {"verdict": yes, "outcome": bool(yes and d["outcome_if_yes"])}
    forms = KR.forms_for("decay_h5", tuple(d["edges"]))
    c = d["candidates"]
    sel = KR.select_form({n: {"form": forms[n], "gain_per_1000": c[n]["gain_per_1000"],
                              "qualifies": bool(c[n]["gate"] and c[n]["gate"]["pass"]),
                              "gate_ratio": c[n]["gate"]["ratio"] if c[n]["gate"] else None} for n in CANDS},
                         margin=delta)
    return {"verdict": {"qualifying": sel["qualifying"], "winner": sel["winner"]}, "outcome": sel["winner"],
            "qualifies": {n: sel["candidates"][n]["qualifies"] for n in CANDS},
            "tied_for_first": sel["tied_for_first"], "settled_by": sel["settled_by"],
            "beats_reference": {n: sel["candidates"][n]["beats_reference"] for n in CANDS}}


def verdict_vector(D: list[dict], delta: float) -> tuple[dict, dict]:
    """Every verdict flag and every outcome at margin `delta`."""
    verdicts, outcomes = {}, {}
    for d in D:
        r = read_new(d, delta)
        if d["kind"] == "choice":
            for n in CANDS:
                verdicts[f"{d['id']}:{n}:qualifies"] = r["qualifies"][n]
            verdicts[f"{d['id']}:winner"] = r["outcome"]
            outcomes[f"{d['id']}:winner"] = r["outcome"]
        else:
            verdicts[d["id"]] = r["verdict"]
            outcomes[f"{d['id']}:outcome"] = r["outcome"]
    return verdicts, outcomes


def unchanged_interval(D: list[dict], which: str) -> dict:
    """The maximal interval of δ around DELTA over which every verdict (or
    every outcome) equals its reading at DELTA. Candidate breakpoints are
    every margin on the record and every pairwise difference among the
    C candidates; each is tested on both sides and at the point itself,
    since a gain of exactly δ beats."""
    idx = 0 if which == "verdicts" else 1
    at = verdict_vector(D, DELTA)[idx]
    pts = set()
    for d in D:
        if d["kind"] == "choice":
            gains = [d["candidates"][n]["gain_per_1000"] for n in CANDS]
            pts.update(abs(g) for g in gains)
            pts.update(abs(a - b) for a in gains for b in gains)
        else:
            pts.add(abs(d["margin_per_1000"]))
    pts = sorted(p for p in pts if p > 0)

    def same(delta: float) -> bool:
        return verdict_vector(D, delta)[idx] == at

    def first_change(delta: float) -> str:
        v = verdict_vector(D, delta)[idx]
        return next(k for k in at if at[k] != v[k])

    lo, lo_set_by, lo_inclusive = 0.0, None, True
    for p in [q for q in pts if q < DELTA][::-1]:
        # crossing p downward: the reading at p, then just below it
        if not same(p):
            lo, lo_inclusive, lo_set_by = p, False, f"at δ = {p:.6g}: {first_change(p)}"
            break
        if not same(p - EPS):
            lo, lo_inclusive, lo_set_by = p, True, f"below δ = {p:.6g}: {first_change(p - EPS)}"
            break
    hi, hi_set_by, hi_inclusive = None, None, True
    for p in [q for q in pts if q >= DELTA]:
        if not same(p):
            hi, hi_inclusive, hi_set_by = p, False, f"at δ = {p:.6g}: {first_change(p)}"
            break
        if not same(p + EPS):
            hi, hi_inclusive, hi_set_by = p, True, f"above δ = {p:.6g}: {first_change(p + EPS)}"
            break
    return {"lower": lo, "lower_inclusive": lo_inclusive, "lower_set_by": lo_set_by,
            "upper": hi, "upper_inclusive": hi_inclusive, "upper_set_by": hi_set_by,
            "reading": f"{'[' if lo_inclusive else '('}{lo:.4f}, {hi:.4f}{']' if hi_inclusive else ')'}"}


# ---------------------------------------------------------------------------
# the anchors and the record
# ---------------------------------------------------------------------------

def main() -> int:
    D, context = collect()
    table = []
    for d in D:
        old, new = read_old(d), read_new(d, DELTA)
        row = {k: v for k, v in d.items() if k not in ("outcome_if_yes",)}
        row["old_rule"] = old
        row["adr0014"] = new
        if d["kind"] == "choice":
            row["verdict_unchanged"] = bool(old["verdict"] == new["verdict"])
        else:
            row["verdict_unchanged"] = bool(old["verdict"] == new["verdict"])
        row["outcome_unchanged"] = bool(old["outcome"] == new["outcome"])
        table.append(row)
    # the C forms: nesting and the free-parameter count, read from the Form
    forms = KR.forms_for("decay_h5", context["edges_a2"])
    forms["shipped"] = KR.Form(interaction=True, name="shipped")
    form_rec = {}
    for n in ("shipped", *CANDS):
        f = forms[n]
        form_rec[n] = {"form": f.describe(), "free_parameters": KR.free_parameters(f),
                       "nested_in": [m for m in ("shipped", *CANDS) if m != n and KR.nested_in(f, forms[m])
                                     and not KR.nested_in(forms[m], f)]}
    # anchors
    by = {d["id"]: d for d in D}
    c3c, ca2 = by["3c:C:choice"]["candidates"], by["a2:C:choice"]["candidates"]
    race_3 = by["3b:B2a_race_x_edu:improves_on_baseline"]["margin_per_1000"]
    race_a2 = by["a2:B2a_race_x_edu:improves_on_baseline"]["margin_per_1000"]
    c3c1_3 = c3c["C3_both_plus_shipped"]["gain_per_1000"] - c3c["C1_cohorts_plus_shipped"]["gain_per_1000"]
    c3c1_a2 = ca2["C3_both_plus_shipped"]["gain_per_1000"] - ca2["C1_cohorts_plus_shipped"]["gain_per_1000"]
    c2_3, c2_a2 = c3c["C2_edu_by_sex_plus_shipped"]["gain_per_1000"], ca2["C2_edu_by_sex_plus_shipped"]["gain_per_1000"]
    shifts_os = {"race_x_edu_vs_baseline": {"phase3c": race_3, "a2": race_a2, "moved": abs(race_a2 - race_3)},
                 "C3_minus_C1": {"phase3c": c3c1_3, "a2": c3c1_a2, "moved": abs(c3c1_a2 - c3c1_3)},
                 "C2_vs_shipped": {"phase3c": c2_3, "a2": c2_a2, "moved": abs(c2_a2 - c2_3)},
                 "C1_vs_shipped": {"phase3c": c3c["C1_cohorts_plus_shipped"]["gain_per_1000"],
                                   "a2": ca2["C1_cohorts_plus_shipped"]["gain_per_1000"]},
                 "C3_vs_shipped": {"phase3c": c3c["C3_both_plus_shipped"]["gain_per_1000"],
                                   "a2": ca2["C3_both_plus_shipped"]["gain_per_1000"]}}
    for v in ("C1_vs_shipped", "C3_vs_shipped"):
        shifts_os[v]["moved"] = abs(shifts_os[v]["a2"] - shifts_os[v]["phase3c"])
    ss3, ssa = by["3c:samesex_edu:improves_on_served"], by["a2:samesex_edu:improves_on_served"]
    shifts_ss = {"interaction_rides_margin": {"phase3c": by["3c:samesex_interaction:rides"]["margin_per_1000"],
                                              "a2": by["a2:samesex_interaction:rides"]["margin_per_1000"]},
                 "edu_term_vs_served_interaction_off": {"phase3c": ss3["margins_both_settings"]["interaction_off"],
                                                        "a2": ssa["margins_both_settings"]["interaction_off"]},
                 "edu_term_vs_served_interaction_on": {"phase3c": ss3["margins_both_settings"]["interaction_on"],
                                                       "a2": ssa["margins_both_settings"]["interaction_on"]}}
    for v in shifts_ss.values():
        v["moved"] = abs(v["a2"] - v["phase3c"])
    largest_os = max(v["moved"] for k, v in shifts_os.items() if k in ("race_x_edu_vs_baseline", "C3_minus_C1", "C2_vs_shipped"))
    pair_a2 = by["a2:C:choice"]["pairs"]["C3_minus_C1"]
    served_margins = sorted([
        {"decision": "3b: race x education ships", "margin_per_1000": race_3},
        {"decision": "3b: the same-sex age term is served", "margin_per_1000": by["3b:samesex_age:improves_on_fallback"]["margin_per_1000"]},
        {"decision": "3c: the same-sex education term ships (the larger of the two settings)", "margin_per_1000": ss3["margin_per_1000"]},
        {"decision": "3c: the interaction rides on same-sex searches", "margin_per_1000": by["3c:samesex_interaction:rides"]["margin_per_1000"]},
        {"decision": "3c: C1 ships over the shipped form", "margin_per_1000": c3c["C1_cohorts_plus_shipped"]["gain_per_1000"]},
        {"decision": "a2: race x education ships (re-run)", "margin_per_1000": race_a2},
        {"decision": "a2: the same-sex education term ships (re-run)", "margin_per_1000": ssa["margin_per_1000"]},
        {"decision": "a2: the interaction rides on same-sex searches (re-run)", "margin_per_1000": by["a2:samesex_interaction:rides"]["margin_per_1000"]},
        {"decision": "a2: C1 ships over the shipped form (re-run)", "margin_per_1000": ca2["C1_cohorts_plus_shipped"]["gain_per_1000"]},
    ], key=lambda r: r["margin_per_1000"])
    smallest = served_margins[0]
    anchors = {
        "fitting_method_shift": {
            "what": "finishing the fit (the A2 projection; the same forms, the same data, the same held-out "
                    "test) moved these margins between the Phase 3c records and the A2 records",
            "opposite_sex_margins": shifts_os,
            "largest_of_the_three_named": largest_os,
            "delta_over_largest": DELTA / largest_os,
            "same_sex_margins": shifts_ss,
            "same_sex_note": "the same-sex margins moved far more than delta: the projection moves the "
                             "education-pair and race-pair parts of the opposite-sex interaction into the "
                             "opposite-sex main effects, and a same-sex search takes its education term from "
                             "same-sex couples, so the borrowed interaction carries less on same-sex searches "
                             "after the projection than before (the interaction's margin fell from 8.92 to "
                             "2.90) while the composition without it gained (6.98 to 12.26); a change in what "
                             "the term contains, not in where the optimiser stopped. delta does not cover a "
                             "shift of that size and does not claim to; the same-sex verdicts hold under it "
                             "because their margins are above delta on both fits"},
        "sampling_noise": {
            "what": "the paired, metro-clustered standard error of the C3 - C1 held-out difference on the "
                    "finished fit, and the metros where C3 is better",
            "C3_minus_C1_a2": pair_a2, "delta_over_se": DELTA / pair_a2["se_per_1000"]},
        "smallest_real_decision": {
            "what": "the smallest margin that has decided a served term on the record",
            "decision": smallest["decision"], "margin_per_1000": smallest["margin_per_1000"],
            "margin_over_delta": smallest["margin_per_1000"] / DELTA,
            "every_served_term_margin": served_margins}}
    interval = {"every_verdict_unchanged": unchanged_interval(D, "verdicts"),
                "every_outcome_unchanged": unchanged_interval(D, "outcomes"),
                "note": "verdicts are every improves / beats flag, every qualifies flag and every winner; "
                        "outcomes are what ships or is served. A gain of exactly delta beats, so an upper end "
                        "at a margin is inclusive and a lower end at a margin is exclusive."}
    # findings, not gates: decisions whose margin is under two standard errors
    under2 = []
    for d in D:
        if d["kind"] == "choice":
            p = d["pairs"]["C3_minus_C1"]
            under2.append({"id": d["id"], "comparison": "C3 - C1", **{k: p[k] for k in ("margin_per_1000", "se_per_1000", "z", "metros_richer_better", "metros")}})
            q = d["candidates"]["C2_edu_by_sex_plus_shipped"]["stats"]
            under2.append({"id": d["id"], "comparison": "C2 - shipped", **{k: q[k] for k in ("margin_per_1000", "se_per_1000", "z", "metros_richer_better", "metros")}})
        else:
            s = d["stats"]
            if s["z"] is not None and abs(s["z"]) < 2:
                under2.append({"id": d["id"], "comparison": f"{d['richer']} - {d['simpler']}",
                               **{k: s[k] for k in ("margin_per_1000", "se_per_1000", "z", "metros_richer_better", "metros")}})
    under2 = [u for u in under2 if u["z"] is None or abs(u["z"]) < 2]
    # the expected verdicts (the brief's list); any difference is a stop condition
    n = {d["id"]: d for d in table}
    a2c = n["a2:C:choice"]["adr0014"]
    expected = {
        "race_x_education_ships_+14.07_gate_pass": bool(n["a2:B2a_race_x_edu:improves_on_baseline"]["adr0014"]["outcome"]
                                                     and abs(race_a2 - 14.07) < 0.005),
        "samesex_education_term_ships_+12.26_+15.16": bool(n["a2:samesex_edu:improves_on_served"]["adr0014"]["outcome"]
                                                          and abs(ssa["margins_both_settings"]["interaction_off"] - 12.26) < 0.005
                                                          and abs(ssa["margins_both_settings"]["interaction_on"] - 15.16) < 0.005),
        "interaction_rides_by_+2.90": bool(n["a2:samesex_interaction:rides"]["adr0014"]["outcome"]
                                          and abs(by["a2:samesex_interaction:rides"]["margin_per_1000"] - 2.90) < 0.005),
        "C2_does_not_qualify_0.007_below_delta": bool(not a2c["qualifies"]["C2_edu_by_sex_plus_shipped"] and 0 < c2_a2 < DELTA),
        "C1_and_C3_tied_0.007_apart": bool(a2c["tied_for_first"] == ["C1_cohorts_plus_shipped", "C3_both_plus_shipped"]
                                           and abs(abs(c3c1_a2) - 0.007) < 0.001),
        "C1_ships_nested_in_C3": bool(a2c["verdict"]["winner"] == "C1_cohorts_plus_shipped" and a2c["settled_by"].startswith("nesting")),
        "every_phase3b_verdict_unchanged": all(r["verdict_unchanged"] and r["outcome_unchanged"] for r in table if r["phase"] == "3b"),
        "every_phase3c_verdict_unchanged": all(r["verdict_unchanged"] and r["outcome_unchanged"] for r in table if r["phase"] == "3c"),
        "every_other_samesex_component_unchanged": all(r["verdict_unchanged"] and r["outcome_unchanged"]
                                                       for r in table if "samesex_" in r["id"] and r["kind"] == "improves"),
        "a2_verdicts_that_change_from_the_old_rule": sorted(r["id"] for r in table if not r["verdict_unchanged"]),
    }
    expected["all_as_expected"] = all(v for k, v in expected.items() if k != "a2_verdicts_that_change_from_the_old_rule") \
        and expected["a2_verdicts_that_change_from_the_old_rule"] == ["a2:C:choice"]
    out = {"rule": {"adr": KR.HELDOUT_TIE_ADR,
                    "title": "Held-out comparisons: a margin, and the simpler form on a tie",
                    "margin_per_1000_sides": DELTA, "constant": "kernel_refine.HELDOUT_TIE_MARGIN_PER_1000",
                    "held_out_measure": "leave one metro out, split the metro's couples in half by household, "
                                        "score the held-out half under the shrunk dials; totals over 387 metros",
                    "written_after": "the A2 flip was seen (C3 over C1 by 0.007 per 1,000 sides where Phase 3c "
                                     "read C1 ahead by 0.001; C2 from -0.003 to +0.007)",
                    "old_rule": "improves = a strict > 0; a yes/no takes the richer option if it is ahead at all; "
                                "among candidates the largest gain of those improving and passing the gate"},
           "se_method": "per-metro differences of held-out log-likelihood between the two forms (same metro "
                        "left out, same household halves, same shrinkage) treated as M independent draws; the "
                        "standard error of their total is sqrt(M * s_d^2), s_d^2 the sample variance (M - 1), "
                        "then per 1,000 sides; paired and metro-clustered",
           "decisions": table, "forms": form_rec, "delta_interval": interval, "anchors": anchors,
           "under_two_standard_errors": under2, "expected_verdicts": expected,
           "context": {k: (list(v) if isinstance(v, tuple) else v) for k, v in context.items()}}
    OUT.write_text(json.dumps(out, indent=1, default=lambda o: o.item() if hasattr(o, "item") else list(o)) + "\n")
    print("δ =", DELTA)
    for r in table:
        if r["kind"] == "choice":
            print(f"  [{r['phase']}] {r['id']}: old {r['old_rule']['verdict']} | ADR 0014 {r['adr0014']['verdict']} "
                  f"({r['adr0014']['settled_by']}) | verdict unchanged {r['verdict_unchanged']}")
        else:
            s = r["stats"]
            print(f"  [{r['phase']}] {r['id']}: {r['margin_per_1000']:+.4f} (SE {s['se_per_1000']:.4f}, z {s['z']:.2f}, "
                  f"{s['metros_richer_better']}/{s['metros']}) old {r['old_rule']['verdict']} | ADR 0014 {r['adr0014']['verdict']} "
                  f"| unchanged {r['verdict_unchanged']}")
    print("interval (verdicts):", interval["every_verdict_unchanged"]["reading"], "|", interval["every_verdict_unchanged"]["lower_set_by"], "|", interval["every_verdict_unchanged"]["upper_set_by"])
    print("interval (outcomes):", interval["every_outcome_unchanged"]["reading"], "|", interval["every_outcome_unchanged"]["lower_set_by"], "|", interval["every_outcome_unchanged"]["upper_set_by"])
    print("anchors:", json.dumps({"largest_named_shift": largest_os, "delta_over_largest": DELTA / largest_os,
                                  "se_C3_C1": pair_a2["se_per_1000"], "delta_over_se": DELTA / pair_a2["se_per_1000"],
                                  "C3_better_in": pair_a2["metros_richer_better"],
                                  "smallest_served": smallest, "over_delta": smallest["margin_per_1000"] / DELTA}, indent=1))
    print("under two SE:", json.dumps(under2, indent=1))
    print("expected:", json.dumps(expected, indent=1))
    if not expected["all_as_expected"]:
        print("STOP: an expected verdict differs", file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
