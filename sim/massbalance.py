"""Front A: gram-by-gram accounting pellet -> post-furnace -> post-acid.

Wraps sim.kinetics with the weighing steps the lab actually performs, and
reconciles against (a) the measured masses in the ground-truth spreadsheet and
(b) the engine's spreadsheet-ported chemistry (yield_calc), which this model
must reproduce as a limiting case (instant calcination, no CO2 escape, complete
trapping, no thermal S loss) — that parity is pinned by tests/test_sim.py.
"""
from __future__ import annotations

import sim  # noqa: F401
from sim import feedstock
from sim.kinetics import Params, Recipe, phase_fractions, simulate
from sim.state import IDX, carbon_mass, conservation_error, solid_mass


def run_mass_balance(recipe: Recipe, p: Params | None = None,
                     c_wt: float | None = None, s_wt: float | None = None) -> dict:
    """Simulate one run and produce the full mass ledger."""
    p = p or Params()
    gc, gs = feedstock.composition(recipe.grade)
    c_wt = gc if c_wt is None else c_wt
    s_wt = gs if s_wt is None else s_wt

    res = simulate(recipe, p, c_wt, s_wt)
    y, y0 = res["y_final"], res["y0"]

    post_furnace = solid_mass(y)
    fe, cao, cas, caco3 = (y[IDX[k]] for k in ("Fe", "CaO", "CaS", "CaCO3"))
    carbon = carbon_mass(y)
    # acid wash: Fe and Ca species dissolve with finite efficiency; what stays
    # is the "trapped metal" impurity of handoff section 4, step 5
    removed = p.eta_wash_fe * fe + p.eta_wash_ca * (cao + cas + caco3)
    trapped = (1 - p.eta_wash_fe) * fe + (1 - p.eta_wash_ca) * (cao + cas + caco3)
    post_acid = post_furnace - removed

    gas = {k: float(y[IDX[k]]) for k in ("CO2_out", "CO_out", "S_out", "VOL_out", "O_out")}
    fracs = phase_fractions(y)
    feed_c = y0[IDX["C_am"]]

    return {
        "recipe": recipe, "c_wt": c_wt, "s_wt": s_wt, "sim": res,
        "pellet": recipe.pellet_mass,
        "post_furnace": float(post_furnace),
        "post_acid": float(post_acid),
        "trapped_metal": float(trapped),
        "conservation_error": conservation_error(y, y0),
        "solids": {"C_amorphous": float(y[IDX["C_am"]]),
                   "C_turbostratic": float(y[IDX["C_turb"]]),
                   "C_graphitic": float(y[IDX["C_gr"]]),
                   "S": float(y[IDX["S"]]), "VOL": float(y[IDX["VOL"]]),
                   "CaCO3": float(caco3), "CaO": float(cao), "CaS": float(cas),
                   "Fe": float(fe)},
        "gas": gas,
        "carbon": {
            "feed_C": float(feed_c),
            "surviving_C": float(carbon),
            "etched_C": float(feed_c - carbon),
            "phase_fractions": fracs,
            "ordering_q": float(y[IDX["Q"]]),
        },
        # the number the project chases: crystalline carbon per gram of feed C.
        # graphitic+turbostratic both diffract; the *crystalline-graphite* yield
        # counts only the graphitic phase.
        "yield": {
            "carbon_yield": float(carbon / feed_c) if feed_c else 0.0,
            "graphite_mass": float(y[IDX["C_gr"]]),
            "crystalline_graphite_yield": float(y[IDX["C_gr"]] / feed_c) if feed_c else 0.0,
        },
    }


def compare_to_measured(mb: dict, measured: dict) -> dict:
    """Residuals vs one spreadsheet row {pellet, post_furnace, post_acid}."""
    out = {"sample": measured.get("sample"),
           "post_furnace_pred": mb["post_furnace"],
           "post_furnace_meas": measured["post_furnace"],
           "post_furnace_resid": mb["post_furnace"] - measured["post_furnace"]}
    if measured.get("post_acid") is not None:
        out.update(post_acid_pred=mb["post_acid"], post_acid_meas=measured["post_acid"],
                   post_acid_resid=mb["post_acid"] - measured["post_acid"])
    return out
